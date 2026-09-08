#!/usr/bin/env python
"""Memory Chatbot (#16 of the 30-in-15) — a bot that remembers you across sessions.

The lesson is memory architecture: a short-term conversation buffer (this session) vs long-term memory
(a store that outlives the session). After each exchange the bot extracts durable facts and saves them;
on every turn it injects what it remembers. Close the tab, come back tomorrow — it still knows you.

    pip install -r requirements.txt
    python app.py            # http://127.0.0.1:7860   (local Ollama by default; ANTHROPIC_API_KEY for Claude)
"""
import os
import uuid

from flask import Flask, request, render_template_string, jsonify, make_response

import llm
import store

app = Flask(__name__)
BASE_SYSTEM = ("You are a warm, helpful assistant with a long-term memory of the user across sessions. "
               "Use what you remember naturally — don't recite it back robotically. Be concise.")
MAX_BUFFER = 8   # short-term turns folded in per request

PAGE = r"""<!doctype html><html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>GritAI · Memory Chatbot</title>
<link rel="stylesheet" href="/static/gritai.css">
<style>
  .wrap{max-width:1080px;margin:0 auto;padding:22px 20px 30px}
  .cols{display:grid;grid-template-columns:1fr 300px;gap:20px;margin-top:16px}
  @media(max-width:820px){.cols{grid-template-columns:1fr}}
  #chat{display:flex;flex-direction:column;gap:12px;min-height:52vh;max-height:64vh;overflow-y:auto;padding-right:4px}
  .msg{max-width:88%;padding:11px 14px;border-radius:4px;font-size:15px;line-height:1.6;white-space:pre-wrap}
  .msg.user{align-self:flex-end;background:var(--panel2);border:1px solid var(--line2)}
  .msg.ai{align-self:flex-start;background:linear-gradient(180deg,var(--panel),var(--bg2));border:1px solid var(--line)}
  .composer{display:flex;gap:10px;margin-top:14px}
  .composer input{flex:1;background:var(--panel);border:1px solid var(--line2);border-radius:3px;color:var(--ink);
    font-family:var(--body);font-size:15.5px;padding:13px 16px;outline:none}
  .send{border:0;background:var(--grit);color:#140a06;font-family:var(--mono);font-weight:600;font-size:12px;
    letter-spacing:.12em;text-transform:uppercase;padding:0 20px;cursor:pointer;border-radius:3px}
  .send:hover{background:var(--grit2)}
  .mempanel{border:1px solid var(--line2);border-radius:3px;background:var(--panel);padding:14px}
  .mempanel h4{font-family:var(--disp);color:var(--grit);font-size:13px;letter-spacing:.06em;text-transform:uppercase;margin:0 0 4px}
  .mempanel .hint{color:var(--dim2);font-family:var(--mono);font-size:10px;letter-spacing:.1em;text-transform:uppercase;margin-bottom:10px}
  .fact{display:flex;justify-content:space-between;gap:8px;align-items:flex-start;font-size:13px;color:var(--ink);
    border-bottom:1px solid var(--line);padding:7px 0}
  .fact .x{cursor:pointer;color:var(--dim2);font-family:var(--mono);font-size:12px}
  .fact .x:hover{color:var(--bad)}
  .fresh{color:var(--ok)}
  .clr{margin-top:10px;border:1px solid var(--line2);background:transparent;color:var(--dim);font-family:var(--mono);
    font-size:10.5px;letter-spacing:.08em;text-transform:uppercase;padding:6px 10px;border-radius:3px;cursor:pointer}
  .clr:hover{color:var(--bad);border-color:var(--bad)}
  .muted{color:var(--dim2);font-family:var(--mono);font-size:10.5px;letter-spacing:.14em;text-transform:uppercase}
  .empty{color:var(--dim2);font-size:12.5px;font-style:italic}
</style></head><body>
<div class="wrap">
  <header style="display:flex;align-items:center;gap:13px">
    <svg width="34" height="34" viewBox="0 0 38 38" fill="none"><rect x="1" y="1" width="36" height="36" rx="2" stroke="#2b303c"/><path d="M27 12.5A9 9 0 1 0 28 22H19" stroke="#ff5a2a" stroke-width="2.4" stroke-linecap="square"/><rect x="10.5" y="10.5" width="3" height="3" fill="#ff5a2a"/></svg>
    <div class="brand"><div class="co">Grit<b>AI</b> · Memory Chatbot</div>
    <div class="sub">Remembers you across sessions · close the tab, come back — it still knows you</div></div>
    <div style="flex:1"></div><div class="tag hot">#16 · 30-in-15</div>
  </header>

  <div class="cols">
    <div>
      <div id="chat"><div class="msg ai">Hi! I'll remember what you tell me — your name, what you're working on, how you like things — and recall it next time you're here. Tell me a bit about yourself.</div></div>
      <div class="composer">
        <input id="q" placeholder="Say something — I'll remember the important bits…" autofocus>
        <button class="send" onclick="ask()">Send</button>
      </div>
      <p class="muted" style="margin-top:12px">Backend: {{ backend }} · GritAI Solutions</p>
    </div>
    <div>
      <div class="mempanel">
        <h4>🧠 Memory</h4>
        <div class="hint">what I remember about you — persists across sessions</div>
        <div id="facts"><span class="empty">nothing yet — tell me something durable</span></div>
        <button class="clr" onclick="clearMem()">forget everything</button>
      </div>
    </div>
  </div>
</div>
<script>
let history=[];
const chat=document.getElementById('chat');
function esc(s){return (s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}
function bubble(cls,text){const d=document.createElement('div');d.className='msg '+cls;d.textContent=text;chat.appendChild(d);chat.scrollTop=chat.scrollHeight;return d;}

async function loadMem(fresh){
  const r=await fetch('/api/memory'); const d=await r.json();
  const box=document.getElementById('facts');
  if(!d.facts||!d.facts.length){box.innerHTML='<span class="empty">nothing yet — tell me something durable</span>';return;}
  box.innerHTML=d.facts.map(f=>{
    const isNew=(fresh||[]).includes(f.fact);
    return `<div class="fact"><span class="${isNew?'fresh':''}">${esc(f.fact)}</span><span class="x" onclick="delMem(${f.id})">✕</span></div>`;
  }).join('');
}
async function delMem(id){await fetch('/api/memory/delete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id})});loadMem();}
async function clearMem(){await fetch('/api/memory/clear',{method:'POST'});loadMem();}

async function ask(){
  const inp=document.getElementById('q');const text=inp.value.trim();if(!text)return;
  inp.value='';bubble('user',text);history.push({role:'user',content:text});
  const thinking=bubble('ai','…');
  try{
    const r=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:text,history})});
    const d=await r.json();
    thinking.textContent=d.reply||'(no reply)';
    history.push({role:'assistant',content:d.reply||''});
    if(history.length>16)history=history.slice(-16);
    loadMem(d.remembered);
  }catch(e){thinking.textContent='(error — is the model backend running?)';}
}
document.getElementById('q').addEventListener('keydown',e=>{if(e.key==='Enter')ask();});
loadMem();
</script></body></html>"""


def _user():
    return request.cookies.get("memuser") or ""


@app.route("/")
def index():
    resp = make_response(render_template_string(PAGE, backend=llm.backend_label()))
    if not request.cookies.get("memuser"):
        resp.set_cookie("memuser", uuid.uuid4().hex, max_age=60 * 60 * 24 * 365, samesite="Lax")
    return resp


@app.route("/api/memory")
def api_memory():
    return jsonify({"facts": store.get_facts(_user())})


@app.route("/api/memory/delete", methods=["POST"])
def api_delete():
    d = request.get_json(force=True)
    store.delete_fact(_user(), int(d.get("id", 0)))
    return jsonify({"ok": True})


@app.route("/api/memory/clear", methods=["POST"])
def api_clear():
    store.clear(_user())
    return jsonify({"ok": True})


@app.route("/api/chat", methods=["POST"])
def api_chat():
    user_id = _user()
    d = request.get_json(force=True)
    message = (d.get("message") or "").strip()[:2000]
    if not message:
        return jsonify({"reply": "Say something!", "remembered": []})
    history = d.get("history") or []
    system = BASE_SYSTEM + store.memory_block(user_id)   # long-term memory injected here
    # short-term buffer: recent turns folded into the prompt
    recent = history[-MAX_BUFFER * 2:-1] if len(history) > 1 else []
    convo = "".join(f"{m['role']}: {m['content']}\n" for m in recent)
    user_prompt = (f"Recent conversation:\n{convo}\n" if convo else "") + f"User: {message}"
    try:
        reply = llm.chat(system, user_prompt, temperature=0.6, max_tokens=600)
    except Exception as e:
        print(f"chat error: {type(e).__name__}")
        return jsonify({"reply": "My brain backend hiccuped — is the model running?", "remembered": []})
    remembered = []
    try:
        remembered = store.remember_from_exchange(user_id, message, reply)
    except Exception as e:
        print(f"memory error: {type(e).__name__}")
    return jsonify({"reply": reply, "remembered": remembered})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "7860"))
    app.run(host="0.0.0.0", port=port, debug=False)
