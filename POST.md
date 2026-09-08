# 30-in-15 · #16 — Memory Chatbot (build-in-public post)

**Attach:** a screen-record — tell it your name/project, RELOAD the page, ask "what do you know about me?" → it recalls.
**Demo:** https://memory.gritai.solutions · **Repo:** https://github.com/GritAI-Labs/memory-chatbot

---

🧠 Project #16 of my "30 AI Projects in 15 days": a chatbot that actually remembers you across sessions.

Most chatbots only have a conversation buffer — the current session's messages. Reload and you're a stranger again. This one adds long-term memory: after each exchange it extracts the durable facts about you (name, preferences, what you're building), stores them, and injects them into every future conversation. Close the tab, come back tomorrow, and it still knows you.

The part I like is that the memory is visible and yours: a side panel shows exactly what it remembers, and you can delete any single fact or wipe it entirely. No black-box profile — memory you can see and control.

Under the hood it's the classic architecture: extract → store → retrieve → inject, with the long-term store deliberately separate from the short-term buffer. Runs on a local model by default (free, private) or a hosted one.

Tell it about yourself, reload, and ask what it knows.

⭐ https://github.com/GritAI-Labs/memory-chatbot

---

## X / Twitter version (≤280)

🧠 #16 of my 30 AI projects in 15 days: a chatbot that remembers you across sessions.

It extracts durable facts about you → stores them → recalls them next time. Reload the tab and it still knows your name & project. Memory you can see and delete.

→ https://github.com/GritAI-Labs/memory-chatbot

---

**Permalinks:** X: _____ · LinkedIn: _____
