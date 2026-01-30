"""
Flask webhook receiver for GitHub Push, Pull Request, and Merge events.
Stores events in MongoDB and serves a UI that polls every 15 seconds.
"""
import os
from datetime import datetime
from flask import Flask, request, jsonify, render_template
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# MongoDB connection
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
DB_NAME = os.getenv("MONGODB_DB", "github_webhooks")
COLLECTION_NAME = "events"

client = MongoClient(MONGODB_URI)
db = client[DB_NAME]
events_collection = db.list_collection_names()[0] if False else db["events"]
print("Using collection:", events_collection.name)


def ref_to_branch(ref):
    """Convert git ref (e.g. refs/heads/staging) to branch name."""
    if not ref:
        return "unknown"
    return ref.replace("refs/heads/", "") if ref.startswith("refs/heads/") else ref

@app.route("/debug-insert")
def debug_insert():
    doc = {
        "action": "debug",
        "author": "ankith",
        "repo": "manual-test",
        "created_at": datetime.utcnow()
    }
    events_collection.insert_one(doc)
    return "Inserted test document"



def parse_github_timestamp(ts_str):
    """Parse GitHub ISO timestamp to datetime and format for display."""
    if not ts_str:
        return datetime.utcnow()
    try:
        # GitHub sends: 2021-04-01T21:30:00Z
        dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        return dt
    except (ValueError, TypeError):
        return datetime.utcnow()


def format_timestamp(dt):
    """Format datetime as '1st April 2021 - 9:30 PM UTC' style."""
    if not isinstance(dt, datetime):
        dt = datetime.utcnow()
    day = dt.day
    suffix = "th"
    if 4 <= day <= 20 or 24 <= day <= 30:
        suffix = "th"
    else:
        suffix = ["st", "nd", "rd"][day % 10 - 1] if day % 10 <= 3 else "th"
    date_str = dt.strftime(f"%d{suffix} %B %Y")
    hour = dt.hour % 12 or 12
    minute = dt.minute
    ampm = "AM" if dt.hour < 12 else "PM"
    time_str = f"{hour}:{minute:02d} {ampm}"
    return f"{date_str} - {time_str} UTC"


# --- Webhook handlers ---

def handle_push(payload):
    repo = payload.get("repository", {}).get("name", "unknown-repo")
    pusher = payload.get("pusher", {}).get("name", "unknown-user")
    ref = payload.get("ref", "")
    branch = ref.replace("refs/heads/", "")

    return {
        "action": "push",
        "author": pusher,
        "repo": repo,
        "from_branch": None,
        "to_branch": branch,
        "timestamp": datetime.utcnow(),
        "created_at": datetime.utcnow(),
    }


def handle_pull_request(payload):
    """Handle pull_request: opened = PR, closed+merged = merge."""
    pr = payload.get("pull_request") or {}
    action = payload.get("action")
    merged = pr.get("merged", False)
    if action == "closed" and merged:
        # Merge event
        base = pr.get("base", {})
        head = pr.get("head", {})
        to_branch = ref_to_branch(base.get("ref", ""))
        from_branch = ref_to_branch(head.get("ref", ""))
        merger = (pr.get("merged_by") or {}).get("login") or (payload.get("sender") or {}).get("login") or "Unknown"
        merged_at = pr.get("merged_at")
        ts = parse_github_timestamp(merged_at) if merged_at else datetime.utcnow()
        return {
            "action": "merge",
            "author": merger,
            "to_branch": to_branch,
            "from_branch": from_branch,
            "timestamp": ts,
            "repo": (payload.get("repository") or {}).get("full_name", ""),
            "created_at": datetime.utcnow(),
        }
    if action == "opened" or action == "synchronize":
        # Pull request submitted
        base = pr.get("base", {})
        head = pr.get("head", {})
        to_branch = ref_to_branch(base.get("ref", ""))
        from_branch = ref_to_branch(head.get("ref", ""))
        author = (pr.get("user") or {}).get("login") or (payload.get("sender") or {}).get("login") or "Unknown"
        ts_str = pr.get("created_at")
        ts = parse_github_timestamp(ts_str)
        return {
            "action": "pull_request",
            "author": author,
            "to_branch": to_branch,
            "from_branch": from_branch,
            "timestamp": ts,
            "repo": (payload.get("repository") or {}).get("full_name", ""),
            "created_at": datetime.utcnow(),
        }
    return None


@app.route("/")
def index():
    """Serve the UI that polls MongoDB every 15 seconds."""
    return render_template("index.html")


@app.route("/api/events", methods=["GET"])
def get_events():
    """Return latest events from MongoDB for UI polling."""
    cursor = events_collection.find().sort("created_at", -1).limit(100)
    events = []
    for doc in cursor:
        out = {
            "_id": str(doc["_id"]),
            "action": doc.get("action"),
            "author": doc.get("author"),
            "to_branch": doc.get("to_branch"),
            "from_branch": doc.get("from_branch"),
            "repo": doc.get("repo"),
        }
        ts = doc.get("timestamp")
        if isinstance(ts, datetime):
            out["timestamp_formatted"] = format_timestamp(ts)
            out["timestamp"] = ts.isoformat() + "Z" if ts.tzinfo is None else ts.isoformat()
        else:
            out["timestamp_formatted"] = str(ts) if ts else ""
            out["timestamp"] = ts
        created = doc.get("created_at")
        out["created_at"] = created.isoformat() + "Z" if isinstance(created, datetime) else created
        events.append(out)
    return jsonify(events)

@app.route("/webhook", methods=["POST"])
def webhook():
    event = request.headers.get("X-GitHub-Event", "")
    payload = request.get_json(force=True, silent=True) or {}

    print("Webhook received:", event)

    doc = None
    if event == "push":
        doc = handle_push(payload)
    elif event == "pull_request":
        doc = handle_pull_request(payload)
    elif event == "ping":
        return jsonify({"message": "pong"}), 200

    if doc is not None:
        events_collection.insert_one(doc)
        print("Inserted document:", doc)
        return jsonify({"status": "stored"}), 200

    print("No document created for event:", event)
    return jsonify({"status": "ignored"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5001)), debug=os.getenv("FLASK_DEBUG", "false").lower() == "true")
