#!/usr/bin/env python
"""LLM backend for the Memory Chatbot (#16): local Ollama (default) or Claude.

chat() for replies, extract_json() for the memory extractor. Errors log the exception TYPE only.
"""
import json
import os
import re
import urllib.request

BACKEND      = os.environ.get("MEMBOT_LLM_BACKEND", "ollama").lower()
OLLAMA_URL   = os.environ.get("MEMBOT_OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
OLLAMA_MODEL = os.environ.get("MEMBOT_OLLAMA_MODEL", "qwen2.5:7b")
ANTHROPIC_KEY   = (os.environ.get("ANTHROPIC_API_KEY") or "").strip() or None
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-haiku-4-5")


def _ollama(system, user, temperature, max_tokens):
    body = json.dumps({"model": OLLAMA_MODEL, "stream": False,
                       "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                       "options": {"temperature": temperature, "num_predict": max_tokens}}).encode()
    req = urllib.request.Request(OLLAMA_URL + "/api/chat", data=body, headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=120).read())["message"]["content"].strip()


def _claude(system, user, temperature, max_tokens):
    body = json.dumps({"model": ANTHROPIC_MODEL, "max_tokens": max_tokens, "temperature": temperature,
                       "system": system, "messages": [{"role": "user", "content": user}]}).encode()
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=body, headers={
        "x-api-key": ANTHROPIC_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"})
    data = json.loads(urllib.request.urlopen(req, timeout=120).read())
    return "".join(b.get("text", "") for b in data.get("content", [])).strip()


def chat(system: str, user: str, temperature: float = 0.5, max_tokens: int = 700) -> str:
    fn = _claude if (BACKEND == "claude" and ANTHROPIC_KEY) else _ollama
    return fn(system, user, temperature, max_tokens)


def extract_json(system: str, user: str):
    raw = chat(system + "\nReply with ONLY valid JSON, no prose, no code fences.", user, temperature=0.0, max_tokens=400)
    s = raw.strip()
    if s.startswith("```"):
        s = s.split("```", 2)[1].lstrip("json").strip() if s.count("```") >= 2 else s.strip("`")
    try:
        return json.loads(s)
    except Exception:
        i, j = s.find("["), s.rfind("]")
        if 0 <= i < j:
            try:
                return json.loads(s[i:j + 1])
            except Exception:
                pass
    return None


def backend_label() -> str:
    return "Claude" if (BACKEND == "claude" and ANTHROPIC_KEY) else f"Ollama ({OLLAMA_MODEL} @ {OLLAMA_URL})"
