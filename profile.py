import os
import requests
from dotenv import load_dotenv
import hashlib

load_dotenv()

ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
_profile_cache = {}

import hashlib

def generate_avatar(name: str) -> str:
    initials = "".join([w[0] for w in name.split()[:2]]).upper() or "U"

    # Generate consistent color per user
    hash_color = hashlib.md5(name.encode()).hexdigest()[:6]

    return f"https://ui-avatars.com/api/?name={initials}&background={hash_color}&color=fff&size=128"
def shorten_id(user_id: str) -> str:
    return f"User {user_id[:6]}..."


def get_display_name(user_id: str) -> tuple[str, str | None]:
    if user_id in _profile_cache:
        return _profile_cache[user_id]

    fallback = (shorten_id(user_id), None)

    if not ACCESS_TOKEN:
        print("No ACCESS_TOKEN found for profile lookup", flush=True)
        _profile_cache[user_id] = fallback
        return fallback

    url = f"https://graph.instagram.com/v25.0/{user_id}"
    params = {
        "fields": "username,name",
        "access_token": ACCESS_TOKEN,
    }

    try:
        response = requests.get(url, params=params, timeout=20)
        data = response.json()

        print(f"Profile lookup for {user_id}: {data}", flush=True)

        if "error" in data:
            _profile_cache[user_id] = fallback
            return fallback

        display_name = data.get("name") or data.get("username") or shorten_id(user_id)

        result = (display_name, None)
        _profile_cache[user_id] = result
        return result

    except Exception as e:
        print(f"Profile lookup exception for {user_id}: {e}", flush=True)
        _profile_cache[user_id] = fallback
        return fallback