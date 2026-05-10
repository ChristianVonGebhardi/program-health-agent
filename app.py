from flask import Flask, render_template, jsonify
from data_fetcher import fetch_all
from analyzer import run_analysis
from github_reporter import post_report
import threading
import schedule
import time
import os
import json
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

CACHE_FILE = "data/latest.json"

cache = {
    "result": None,
    "status": "idle",
    "last_updated": None,
    "report_url": None
}

def save_cache(result):
    os.makedirs("data", exist_ok=True)
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

def load_cache():
    if not os.path.exists(CACHE_FILE):
        return None
    with open(CACHE_FILE, encoding="utf-8") as f:
        return json.load(f)

def run_pipeline():
    cache["status"] = "running"
    try:
        data = fetch_all()
        result = run_analysis(data)
        # Ensure analysis is a dict
        if isinstance(result.get('analysis'), str):
            try:
                result['analysis'] = json.loads(result['analysis'])
            except:
                pass
        url = post_report(result)
        result["report_url"] = url
        save_cache(result)
        cache["result"] = result
        cache["report_url"] = url
        cache["last_updated"] = time.strftime("%Y-%m-%d %H:%M")
        cache["status"] = "done"
        print(f">>> Pipeline complete")
    except Exception as e:
        cache["status"] = "error"
        cache["last_updated"] = time.strftime("%Y-%m-%d %H:%M")
        print(f">>> Pipeline failed: {e}")

def start_scheduler():
    schedule.every().friday.at("09:00").do(run_pipeline)
    print(">>> Scheduler started — runs every Friday at 09:00 UTC (10:00 CET)")
    while True:
        schedule.run_pending()
        time.sleep(60)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/status")
def status():
    return jsonify({
        "status": cache["status"],
        "last_updated": cache["last_updated"],
        "report_url": cache["report_url"]
    })

@app.route("/api/results")
def results():
    if cache["result"]:
        return jsonify(cache["result"])
    return jsonify({})

@app.route("/api/refresh", methods=["POST"])
def refresh():
    if cache["status"] != "running":
        thread = threading.Thread(target=run_pipeline)
        thread.daemon = True
        thread.start()
    return jsonify({"status": "started"})

if __name__ == "__main__":
    # Load cached results on startup
    previous = load_cache()
    if previous:
        cache["result"] = previous
        cache["status"] = "done"
        cache["last_updated"] = previous.get("analyzed_at", "previous run")[:10]
        cache["report_url"] = previous.get("report_url")
        print(">>> Loaded previous results from cache")

    scheduler_thread = threading.Thread(target=start_scheduler)
    scheduler_thread.daemon = True
    scheduler_thread.start()

    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)