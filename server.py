import os, json, time
from flask import Flask, jsonify

# Optional: add your OpenAI key in Render later to enable AI guides
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "").strip()

# (Future) PlusPortals creds — add in Render later when we wire scraping
PP_EMAIL = os.environ.get("PP_EMAIL", "")
PP_PASS  = os.environ.get("PP_PASS", "")
PP_URL   = os.environ.get("PP_URL", "")

CLASS_ORDER = [
    "Witness", "Apologetics", "Algebra 2",
    "Chemistry", "American Literature", "American History"
]

def fallback_tasks():
    today = time.strftime("%Y-%m-%d")
    return [
        {
            "id": "cloud-demo-1",
            "className": "Witness",
            "day": "Tuesday",
            "title": "Cloud test item",
            "due": today,
            "files": [{"name": "Outline.pdf", "type": "original"}],
            "instructions": "This came from the cloud helper (Render)."
        }
    ]

def fetch_from_plusportals():
    # We’ll replace this with real scraping later.
    # For now, return a safe list so your app works anywhere.
    return fallback_tasks()

def maybe_add_ai_guides(tasks):
    if not OPENAI_API_KEY:
        return tasks
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        for t in tasks:
            prompt = (
                "Create a short 4–6 bullet checklist for a high schooler to complete: "
                f"“{t['title']}”. Keep it direct and practical."
            )
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role":"user","content":prompt}],
                temperature=0.3,
            )
            guide = (resp.choices[0].message.content or "").strip()
            if guide:
                t.setdefault("files", []).append({
                    "name": f"{t['title']}_Guide.txt",
                    "type": "ai_guide"
                })
                t["instructions"] = (t.get("instructions") or "") + "\n\nAI Guide:\n" + guide
    except Exception as e:
        print("AI guide skipped:", e)
    return tasks

app = Flask(__name__)

@app.get("/tasks")
def tasks():
    try:
        data = fetch_from_plusportals()
    except Exception as e:
        print("Fetch error, sending fallback:", e)
        data = fallback_tasks()

    data = maybe_add_ai_guides(data)

    # Normalize shapes so your app never crashes
    for t in data:
        t.setdefault("files", [])
        t.setdefault("instructions", "")
        t.setdefault("due", None)
        t.setdefault("day", "")
        t.setd
