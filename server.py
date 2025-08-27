import os, time
from flask import Flask, jsonify

app = Flask(__name__)

# Keep your class order if you want it later
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

@app.get("/tasks")
def tasks():
    # Just return the fallback for now (rock-solid)
    return jsonify(fallback_tasks())

if __name__ == "__main__":
    # Local run: python server.py
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

