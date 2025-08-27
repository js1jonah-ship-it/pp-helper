import os, time, re
from flask import Flask, jsonify, request, Response, redirect

app = Flask(__name__)

# Secret token to allow only your scraper to push data
INGEST_TOKEN = os.environ.get("INGEST_TOKEN", "").strip()

# In-memory cache of tasks
TASKS_CACHE = []

CLASS_ORDER = [
    "Witness", "Apologetics", "Algebra 2",
    "Chemistry", "American Literature", "American History"
]
DAY_ORDER = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]

def today():
    return time.strftime("%Y-%m-%d")

def normalize_task(t):
    t = dict(t)
    t.setdefault("id", f"id-{int(time.time()*1000)}")
    t.setdefault("className", "Unknown")
    t.setdefault("day", "")
    t.setdefault("title", "Untitled")
    t.setdefault("due", None)
    t.setdefault("files", [])
    t.setdefault("instructions", "")
    return t

def fallback_tasks():
    return [{
        "id": "cloud-demo-1",
        "className": "Witness",
        "day": "Tuesday",
        "title": "Cloud test item",
        "due": today(),
        "files": [{"name": "Outline.pdf", "type": "original"}],
        "instructions": "This came from the cloud helper."
    }]

# ---------- Simple text parser (backup admin page) ----------
def parse_weekly_text(raw_text):
    lines = [l.strip() for l in raw_text.splitlines()]
    tasks = []
    current_class = None
    current_day = None
    curr = None

    day_re = re.compile(r'^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b[:\-]?\s*(.*)$', re.I)
    due_inline_re = re.compile(r'\bdue[:\s]*([0-9]{4}-[0-9]{2}-[0-9]{2})\b', re.I)
    file_inline_re = re.compile(r'\b(file|attachment)[:\s]*([^\s].+)$', re.I)

    def push():
        nonlocal curr
        if curr and curr.get("title"):
            tasks.append(normalize_task(curr))
        curr = None

    i = 0
    while i < len(lines):
        line = lines[i]

        if line in CLASS_ORDER:
            push()
            current_class = line
            current_day = None
            i += 1
            continue

        mday = day_re.match(line)
        if mday and current_class:
            push()
            current_day = mday.group(1).capitalize()
            rest = mday.group(2).strip()
            curr = {
                "id": f"{current_class[:2].lower()}-{int(time.time()*1000)}-{len(tasks)}",
                "className": current_class,
                "day": current_day,
                "title": "",
                "due": None,
                "files": [],
                "instructions": ""
            }
            if rest:
                mdue = due_inline_re.search(rest)
                if mdue:
                    curr["due"] = mdue.group(1)
                    rest = due_inline_re.sub("", rest).strip()
                mfile = file_inline_re.search(rest)
                if mfile:
                    curr["files"].append({"name": mfile.group(2).strip(), "type": "original"})
                    rest = file_inline_re.sub("", rest).strip()
                curr["title"] = rest or f"{current_day} task"
            i += 1
            continue

        if curr:
            mdue2 = due_inline_re.search(line)
            if mdue2:
                curr["due"] = mdue2.group(1)
                i += 1
                continue
            mfile2 = file_inline_re.search(line)
            if mfile2:
                curr["files"].append({"name": mfile2.group(2).strip(), "type": "original"})
                i += 1
                continue
            if line:
                if not curr["title"] and line not in CLASS_ORDER and not day_re.match(line):
                    curr["title"] = line
                else:
                    curr["instructions"] = (curr["instructions"] + "\n" if curr["instructions"] else "") + re.sub(r'^instructions:\s*', '', line, flags=re.I)
            i += 1
            continue

        i += 1

    push()
    return tasks

# ---------------- Routes ----------------
@app.get("/")
def root():
    return Response(
        '<html><body style="font-family:system-ui;margin:20px">'
        '<h2>pp-helper live</h2>'
        '<p><a href="/tasks">/tasks</a> → JSON for your phone app.</p>'
        '<p><a href="/admin">/admin</a> → (backup) paste weekly text manually.</p>'
        '</body></html>', mimetype="text/html"
    )

@app.get("/tasks")
def tasks():
    data = TASKS_CACHE if TASKS_CACHE else fallback_tasks()
    out = [normalize_task(t) for t in data]
    return jsonify(out)

# Secure endpoint Apify calls with JSON: { tasks: [...] }
@app.post("/ingest")
def ingest():
    token = request.args.get("token", "")
    if not INGEST_TOKEN or token != INGEST_TOKEN:
        return jsonify({"ok": False, "error": "unauthorized"}), 401
    js = request.get_json(silent=True) or {}
    items = js.get("tasks", [])
    if not isinstance(items, list) or not items:
        return jsonify({"ok": False, "error": "no tasks"}), 400
    global TASKS_CACHE
    TASKS_CACHE = [normalize_task(t) for t in items]
    return jsonify({"ok": True, "count": len(TASKS_CACHE)})

# Backup admin page
@app.get("/admin")
def admin_page():
    return Response(
        '<html><head><meta name="viewport" content="width=device-width, initial-scale=1">'
        '<style>body{font-family:system-ui;margin:16px;max-width:720px}'
        'textarea{width:100%;height:320px;font-family:ui-monospace,Menlo,Consolas,monospace}'
        'button{padding:10px 16px;border-radius:999px;border:0;background:#111;color:#fff;font-weight:700}'
        '.box{background:#f4f4f5;border-radius:12px;padding:12px;margin-top:12px}</style>'
        '</head><body>'
        '<h2>Paste Weekly Plan (backup)</h2>'
        '<form method="POST" action="/admin"><textarea name="plan"></textarea>'
        '<div style="margin-top:12px"><button type="submit">Save</button></div></form>'
        '</body></html>', mimetype="text/html"
    )

@app.post("/admin")
def admin_save():
    raw = request.form.get("plan", "")
    parsed = parse_weekly_text(raw) if raw.strip() else []
    if parsed:
        global TASKS_CACHE
        TASKS_CACHE = parsed
        return redirect("/tasks")
    return redirect("/admin")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
