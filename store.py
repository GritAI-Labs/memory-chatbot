#!/usr/bin/env python
"""Long-term memory for the Memory Chatbot (#16).

The architecture, in four moves:
  1. EXTRACT — after each exchange, an LLM pulls durable facts about the user (name, prefs, projects).
  2. STORE   — facts are written to SQLite, keyed by user, deduped. This is what survives across sessions.
  3. RETRIEVE— on each new turn, the user's stored facts are loaded.
  4. INJECT  — they're placed in the system prompt so the bot "remembers you."

This is the distinction the rung teaches: the short-term conversation buffer lives in the request;
long-term memory lives here, in a store that outlives the session.
"""
import os
import sqlite3
import threading

import llm

DB = os.environ.get("MEMBOT_DB", os.path.join(os.path.dirname(os.path.abspath(__file__)), "memory.db"))
_lock = threading.Lock()

EXTRACT_SYS = (
    "You maintain a chatbot's LONG-TERM memory of a user. From the latest exchange, extract only DURABLE "
    "facts worth remembering across future sessions — the user's name, stable preferences, ongoing projects, "
    "role, constraints, or personal context they'd expect you to recall later. Do NOT store the assistant's "
    "words, one-off questions, greetings, or transient chit-chat. Return a JSON array of short first-person-"
    "about-the-user fact strings (e.g. [\"Name is Alex\", \"Prefers Python\", \"Building a bakery website\"]). "
    "If nothing durable was shared, return []."
)


def _conn():
    c = sqlite3.connect(DB)
    c.execute("""CREATE TABLE IF NOT EXISTS facts (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL, fact TEXT NOT NULL,
        created_at TEXT DEFAULT (datetime('now')))""")
    return c


def get_facts(user_id: str) -> list:
    with _lock, _conn() as c:
        rows = c.execute("SELECT id, fact FROM facts WHERE user_id=? ORDER BY id", (user_id,)).fetchall()
    return [{"id": r[0], "fact": r[1]} for r in rows]


def add_fact(user_id: str, fact: str):
    fact = (fact or "").strip()
    if not fact:
        return
    with _lock, _conn() as c:
        exists = c.execute("SELECT 1 FROM facts WHERE user_id=? AND lower(fact)=lower(?)",
                           (user_id, fact)).fetchone()
        if not exists:
            c.execute("INSERT INTO facts (user_id, fact) VALUES (?, ?)", (user_id, fact))


def delete_fact(user_id: str, fact_id: int):
    with _lock, _conn() as c:
        c.execute("DELETE FROM facts WHERE user_id=? AND id=?", (user_id, fact_id))


def clear(user_id: str):
    with _lock, _conn() as c:
        c.execute("DELETE FROM facts WHERE user_id=?", (user_id,))


def remember_from_exchange(user_id: str, user_msg: str, assistant_msg: str) -> list:
    """EXTRACT + STORE. Returns the list of newly-added facts (for UI feedback)."""
    prompt = f"USER SAID: {user_msg}\nASSISTANT REPLIED: {assistant_msg}\n\nExtract durable facts about the user."
    facts = llm.extract_json(EXTRACT_SYS, prompt)
    if not isinstance(facts, list):
        return []
    before = {f["fact"].lower() for f in get_facts(user_id)}
    added = []
    for f in facts:
        if isinstance(f, str) and f.strip() and f.strip().lower() not in before:
            add_fact(user_id, f.strip())
            added.append(f.strip())
    return added


def memory_block(user_id: str) -> str:
    """RETRIEVE + format for INJECTion into the system prompt."""
    facts = get_facts(user_id)
    if not facts:
        return ""
    lines = "\n".join(f"- {f['fact']}" for f in facts)
    return f"\n\nWhat you remember about this user from past sessions:\n{lines}\n"
