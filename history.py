import json
import os
from typing import Dict, List

HISTORY_FILE = "chat_history.json"
MAX_MESSAGES_PER_USER = 8  # recent messages only


def load_history() -> Dict[str, List[dict]]:
    if not os.path.exists(HISTORY_FILE):
        return {}

    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_history(history: Dict[str, List[dict]]) -> None:
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


def add_message(user_id: str, role: str, text: str) -> None:
    history = load_history()

    if user_id not in history:
        history[user_id] = []

    history[user_id].append({
        "role": role,
        "text": text
    })

    history[user_id] = history[user_id][-MAX_MESSAGES_PER_USER:]
    save_history(history)


def get_recent_history(user_id: str) -> List[dict]:
    history = load_history()
    return history.get(user_id, [])


def format_history_for_prompt(user_id: str) -> str:
    messages = get_recent_history(user_id)

    if not messages:
        return "No previous conversation history."

    lines = []
    for msg in messages:
        label = "User" if msg["role"] == "user" else "Assistant"
        lines.append(f"{label}: {msg['text']}")

    return "\n".join(lines)