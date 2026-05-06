import json
import os
from datetime import datetime

PENDING_FILE = "pending_replies.json"


def load_pending():
    if not os.path.exists(PENDING_FILE):
        return []

    try:
        with open(PENDING_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_pending(items):
    with open(PENDING_FILE, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2)


def add_pending_reply(user_id: str, text: str, send_at: str):
    items = load_pending()
    items.append({
        "user_id": user_id,
        "text": text,
        "send_at": send_at
    })
    save_pending(items)


def get_due_replies():
    items = load_pending()
    now = datetime.utcnow()

    due = []
    remaining = []

    for item in items:
        send_time = datetime.fromisoformat(item["send_at"])
        if send_time <= now:
            due.append(item)
        else:
            remaining.append(item)

    save_pending(remaining)
    return due