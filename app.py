import os, json, time
from datetime import datetime, timezone
from flask import Flask, jsonify

app = Flask(__name__)

def now_utc():
    return datetime.now(timezone.utc).strftime("%H:%M UTC")

def read_scores():
    try:
        with open("data/scores.json") as f:
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
