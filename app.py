import json
import os
from datetime import datetime, timezone
from pathlib import Path
from flask import Flask, jsonify

app = Flask(__name__)
SCORES_FILE = Path(__file__).parent / 'data' / 'scores.json'

def now_utc():
    return datetime.now(timezone.utc).strftime("%H:%M UTC")

def read_scores():
    try:
        with SCORES_FILE.open(encoding="utf-8") as f:
            return json.load(f)
    except Exception as ex:
        print(f"Read error: {ex}")
        return {"matches": [], "updated": now_utc(), "count": 0, "source": "read-error"}

@app.get("/")
def index():
    return jsonify({"name": "Garmin Live Sports", "source": "GitHub Actions scraper"})

@app.get("/health")
def health():
    d = read_scores()
    return jsonify({"status": "ok", "updated": d.get("updated"), "count": d.get("count", 0), "source": d.get("source")})

@app.get("/scores")
def scores():
    return jsonify(read_scores())

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "10000")))
