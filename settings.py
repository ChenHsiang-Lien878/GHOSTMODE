import json
import os

SETTINGS_FILE = "settings.json"

DEFAULT_SETTINGS = {
    "ghost_mode": True,
    "reply_mode": "normal",
    "reply_delay_seconds": 5

}


def load_settings():
    if not os.path.exists(SETTINGS_FILE):
        save_settings(DEFAULT_SETTINGS)
        return DEFAULT_SETTINGS.copy()

    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return {
                "ghost_mode": data.get("ghost_mode", True),
                "reply_mode": data.get("reply_mode", "normal"),
                "reply_delay_seconds": data.get("reply_delay_seconds", 5)
            }
    except Exception:
        save_settings(DEFAULT_SETTINGS)
        return DEFAULT_SETTINGS.copy()


def save_settings(settings):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)