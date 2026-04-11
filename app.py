import json
import importlib
import os
import urllib.error
import urllib.parse
import urllib.request
import random
import sys
import threading
import time
import uuid
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, request, send_from_directory

InstagramClient = None
_instagram_import_error = ""

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_FILE = DATA_DIR / "store.json"
INSTAGRAM_SESSION_DIR = DATA_DIR / "instagram_sessions"
PUBLIC_DIR = BASE_DIR / "public"

app = Flask(__name__, static_folder=str(PUBLIC_DIR), static_url_path="")

_timers = {}
_timers_lock = threading.Lock()
_store_lock = threading.Lock()
_instagram_runtime_lock = threading.Lock()
_instagram_client = None
_instagram_worker_thread = None
_instagram_worker_stop = None
GRAPH_API_BASE = "https://graph.facebook.com/v20.0"
OLLAMA_API_URL = os.environ.get("OLLAMA_API_URL", "http://127.0.0.1:11434/api/generate")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3")
OLLAMA_TIMEOUT_SEC = int(os.environ.get("OLLAMA_TIMEOUT_SEC", "45"))


def load_instagram_client_class() -> tuple[Any | None, str]:
    global InstagramClient, _instagram_import_error

    if InstagramClient is not None:
        return InstagramClient, ""

    try:
        module = importlib.import_module("instagrapi")
        InstagramClient = getattr(module, "Client")
        _instagram_import_error = ""
        return InstagramClient, ""
    except Exception as exc:
        _instagram_import_error = f"{exc.__class__.__name__}: {exc}"
        return None, _instagram_import_error


def _instagram_session_path(username: str) -> Path:
    safe = "".join(ch if ch.isalnum() or ch in ["_", "-"] else "_" for ch in username.lower()).strip("_")
    safe = safe or "instagram_user"
    return INSTAGRAM_SESSION_DIR / f"{safe}.json"


def _load_instagram_session(client: Any, username: str) -> bool:
    path = _instagram_session_path(username)
    if not path.exists():
        return False
    try:
        client.load_settings(str(path))
        return True
    except Exception:
        return False


def _save_instagram_session(client: Any, username: str) -> None:
    INSTAGRAM_SESSION_DIR.mkdir(parents=True, exist_ok=True)
    path = _instagram_session_path(username)
    client.dump_settings(str(path))


def _friendly_instagram_login_error(exc: Exception) -> str:
    raw = str(exc)
    lower = raw.lower()

    if "blacklist" in lower or "ip address" in lower or "ip" in lower and "black" in lower:
        return (
            "Instagram blocked this login from your current network/IP. "
            "Password may still be correct. Disable VPN/proxy, sign in once via browser from this same network, "
            "wait a bit, then retry."
        )

    if "challenge" in lower or "checkpoint" in lower or "email" in lower:
        return (
            "Instagram triggered a security challenge. Approve the challenge in the Instagram app/web first, "
            "then reconnect here."
        )

    if "two_factor" in lower or "2fa" in lower:
        return "This account requires 2FA challenge handling, which is not implemented in this prototype yet."

    return f"Instagram login failed: {raw}"


def _sanitize_token(raw: str) -> str:
    """Strip common copy/paste artefacts from a Meta access token."""
    t = raw.strip()
    # Remove surrounding quotes
    if (t.startswith('"') and t.endswith('"')) or (t.startswith("'") and t.endswith("'")):
        t = t[1:-1]
    # Remove accidental "Bearer " prefix
    for prefix in ("Bearer ", "bearer "):
        if t.startswith(prefix):
            t = t[len(prefix):]
    # Collapse any embedded newlines / carriage returns / tabs
    t = t.replace("\n", "").replace("\r", "").replace("\t", "").strip()
    return t


def _graph_get(path: str, access_token: str, params: dict[str, Any] | None = None) -> dict:
    merged = dict(params or {})
    merged["access_token"] = access_token
    query = urllib.parse.urlencode(merged)
    url = f"{GRAPH_API_BASE}/{path}?{query}"
    req = urllib.request.Request(url=url, method="GET")
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = resp.read().decode("utf-8")
    return json.loads(payload)


def _graph_post(path: str, access_token: str, body: dict[str, Any]) -> dict:
    token = urllib.parse.quote(access_token, safe="")
    url = f"{GRAPH_API_BASE}/{path}?access_token={token}"
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url=url,
        method="POST",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = resp.read().decode("utf-8")
    return json.loads(payload)


def _error_text(exc: Exception) -> str:
    if isinstance(exc, urllib.error.HTTPError):
        try:
            body = exc.read().decode("utf-8")
            if body:
                return body
        except Exception:
            pass
    return str(exc)


def validate_official_instagram_setup(access_token: str, ig_business_id: str) -> dict:
    required_permissions = [
        "instagram_manage_messages",
    ]
    optional_permissions = [
        "pages_manage_metadata",
        "pages_read_engagement",
    ]
    checks = []
    granted_permissions = []
    missing_permissions = []

    me_ok = False
    ig_ok = False

    try:
        me_data = _graph_get("me", access_token, {"fields": "id,name"})
        me_ok = bool(me_data.get("id"))
        checks.append(
            {
                "name": "Token is valid",
                "ok": me_ok,
                "details": f"Connected as {me_data.get('name', 'unknown')} ({me_data.get('id', 'n/a')})",
            }
        )
    except Exception as exc:
        checks.append({"name": "Token is valid", "ok": False, "details": _error_text(exc)})

    try:
        ig_data = _graph_get(str(ig_business_id), access_token, {"fields": "id,username,name"})
        ig_ok = bool(str(ig_data.get("id", "")) == str(ig_business_id))
        checks.append(
            {
                "name": "Business account is reachable",
                "ok": ig_ok,
                "details": f"Resolved {ig_data.get('username') or ig_data.get('name') or 'account'} ({ig_data.get('id', 'n/a')})",
            }
        )
    except Exception as exc:
        checks.append({"name": "Business account is reachable", "ok": False, "details": _error_text(exc)})

    try:
        perms_data = _graph_get("me/permissions", access_token)
        granted_permissions = [
            item.get("permission")
            for item in (perms_data.get("data") or [])
            if item.get("status") == "granted" and item.get("permission")
        ]
        granted_set = set(granted_permissions)
        missing_permissions = [perm for perm in required_permissions if perm not in granted_set]
        missing_optional = [perm for perm in optional_permissions if perm not in granted_set]
        details_parts = []
        if not missing_permissions:
            details_parts.append("All required permissions granted")
        else:
            details_parts.append(f"Missing required: {', '.join(missing_permissions)}")
        if missing_optional:
            details_parts.append(f"Optional (not required): {', '.join(missing_optional)}")
        checks.append(
            {
                "name": "Required permissions",
                "ok": len(missing_permissions) == 0,
                "details": ". ".join(details_parts),
            }
        )
    except Exception as exc:
        checks.append(
            {
                "name": "Required permissions",
                "ok": False,
                "details": f"Could not verify permissions: {_error_text(exc)}",
            }
        )

    ok = me_ok and ig_ok and len(missing_permissions) == 0
    recommendations = []
    if not ok:
        recommendations.append("Ensure your token is a valid long-lived page access token for the connected Facebook page.")
        recommendations.append("Confirm the Instagram account is professional and linked to that page in Meta Business settings.")
        if missing_permissions:
            recommendations.append("Request and grant missing permissions in your Meta app, then generate a fresh token.")

    return {
        "ok": ok,
        "checks": checks,
        "missingPermissions": missing_permissions,
        "grantedPermissions": granted_permissions,
        "requiredPermissions": required_permissions,
        "recommendations": recommendations,
    }


def discover_official_instagram_accounts(access_token: str) -> dict:
    pages_payload = _graph_get(
        "me/accounts",
        access_token,
        {"fields": "id,name,access_token,instagram_business_account{id,username,name}"},
    )
    pages = pages_payload.get("data", []) or []

    accounts = []
    for page in pages:
        ig = page.get("instagram_business_account") or {}
        ig_id = str(ig.get("id") or "")
        if not ig_id:
            continue
        accounts.append(
            {
                "pageId": str(page.get("id") or ""),
                "pageName": str(page.get("name") or ""),
                "pageAccessToken": str(page.get("access_token") or ""),
                "instagramBusinessAccountId": ig_id,
                "instagramUsername": str(ig.get("username") or ig.get("name") or ""),
            }
        )

    return {
        "count": len(accounts),
        "accounts": accounts,
        "single": accounts[0] if len(accounts) == 1 else None,
    }


def random_id() -> str:
    return f"{uuid.uuid4().hex[:8]}{int(time.time() * 1000) % 10000}"


def seed_store() -> dict:
    now = int(time.time() * 1000)
    return {
        "settings": {
            "autoReplyEnabled": True,
            "defaultMinDelaySec": 15,
            "defaultMaxDelaySec": 90,
        },
        "instagram": {
            "enabled": False,
            "connected": False,
            "username": "",
            "authMode": "private",
            "pageAccessToken": "",
            "instagramBusinessAccountId": "",
            "pageId": "",
            "pollIntervalSec": 20,
            "lastError": "",
            "seenMessageIds": [],
        },
        "contacts": [
            {
                "id": "alex",
                "name": "Alex",
                "platform": "local",
                "instagramUsername": None,
                "instagramThreadId": None,
                "mode": "normal",
                "autoReplyEnabled": True,
                "styleOverride": "",
                "minDelaySec": 20,
                "maxDelaySec": 75,
                "history": [
                    {"role": "you", "text": "yo im running 10 late, on my way"},
                    {"role": "you", "text": "sounds good, lets do thurs 7?"},
                    {"role": "you", "text": "cant this week, maybe next one"},
                ],
                "messages": [
                    {
                        "id": random_id(),
                        "role": "contact",
                        "text": "Can you make dinner tonight?",
                        "ts": now - 200000,
                    }
                ],
            },
            {
                "id": "sam",
                "name": "Sam (Work)",
                "platform": "local",
                "instagramUsername": None,
                "instagramThreadId": None,
                "mode": "no_mode",
                "autoReplyEnabled": True,
                "styleOverride": "keep concise, polite, and non-committal",
                "minDelaySec": 45,
                "maxDelaySec": 140,
                "history": [
                    {"role": "you", "text": "thanks for flagging this, i will review by tomorrow morning."},
                    {"role": "you", "text": "I cannot take this on right now, but I can share notes."},
                ],
                "messages": [],
            },
        ],
    }


def normalize_store(store: dict) -> bool:
    changed = False
    if "instagram" not in store:
        store["instagram"] = {
            "enabled": False,
            "connected": False,
            "username": "",
            "authMode": "private",
            "pageAccessToken": "",
            "instagramBusinessAccountId": "",
            "pollIntervalSec": 20,
            "lastError": "",
            "seenMessageIds": [],
        }
        changed = True
    else:
        instagram = store["instagram"]
        defaults = {
            "enabled": False,
            "connected": False,
            "username": "",
            "authMode": "private",
            "pageAccessToken": "",
            "instagramBusinessAccountId": "",
            "pollIntervalSec": 20,
            "lastError": "",
            "seenMessageIds": [],
        }
        for key, value in defaults.items():
            if key not in instagram:
                instagram[key] = value
                changed = True

    for contact in store.get("contacts", []):
        if "platform" not in contact:
            contact["platform"] = "local"
            changed = True
        if "instagramUsername" not in contact:
            contact["instagramUsername"] = None
            changed = True
        if "instagramThreadId" not in contact:
            contact["instagramThreadId"] = None
            changed = True
        if "instagramRecipientId" not in contact:
            contact["instagramRecipientId"] = None
            changed = True
        if "autoReplyEnabled" not in contact:
            contact["autoReplyEnabled"] = True
            changed = True

    return changed


def ensure_store() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    INSTAGRAM_SESSION_DIR.mkdir(parents=True, exist_ok=True)
    if not DATA_FILE.exists():
        with DATA_FILE.open("w", encoding="utf-8") as f:
            json.dump(seed_store(), f, indent=2)


def read_store() -> dict:
    ensure_store()
    with _store_lock:
        with DATA_FILE.open("r", encoding="utf-8") as f:
            store = json.load(f)

        if normalize_store(store):
            with DATA_FILE.open("w", encoding="utf-8") as fw:
                json.dump(store, fw, indent=2)

        return store


def write_store(store: dict) -> None:
    normalize_store(store)
    with _store_lock:
        with DATA_FILE.open("w", encoding="utf-8") as f:
            json.dump(store, f, indent=2)


def clamp_delay(min_sec: int, max_sec: int) -> tuple[int, int]:
    safe_min = max(3, min(int(min_sec), int(max_sec)))
    safe_max = max(safe_min, int(max_sec))
    return safe_min, safe_max


def extract_common_openers(messages: list[dict]) -> list[str]:
    counts = {}
    for msg in messages:
        words = str(msg.get("text", "")).strip().split()
        opener = " ".join(words[:2]).lower()
        if opener:
            counts[opener] = counts.get(opener, 0) + 1
    ordered = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    return [v for v, _ in ordered[:4]]


def analyze_style(history: list[dict]) -> dict:
    your_msgs = [m for m in history if m.get("role") == "you" and str(m.get("text", "")).strip()]
    if not your_msgs:
        return {
            "avgWords": 12,
            "lowerCaseBias": 0.6,
            "emojiBias": 0.05,
            "punctuation": ".",
            "commonOpeners": [],
        }

    word_counts = [len(str(m["text"]).strip().split()) for m in your_msgs]
    avg_words = max(4, round(sum(word_counts) / len(word_counts)))

    lower_chars = 0
    alpha_chars = 0
    emoji_hits = 0
    punct_count = {".": 0, "!": 0, "?": 0, "none": 0}

    for msg in your_msgs:
        text = str(msg["text"])
        for ch in text:
            if ch.isalpha():
                alpha_chars += 1
                if ch.islower():
                    lower_chars += 1
            if ord(ch) > 127:
                emoji_hits += 1

        trimmed = text.strip()
        if trimmed.endswith("!"):
            punct_count["!"] += 1
        elif trimmed.endswith("?"):
            punct_count["?"] += 1
        elif trimmed.endswith("."):
            punct_count["."] += 1
        else:
            punct_count["none"] += 1

    punctuation = sorted(punct_count.items(), key=lambda x: x[1], reverse=True)[0][0]
    common_openers = extract_common_openers(your_msgs)

    return {
        "avgWords": avg_words,
        "lowerCaseBias": (lower_chars / alpha_chars) if alpha_chars else 0.6,
        "emojiBias": emoji_hits / max(1, len(your_msgs) * 20),
        "punctuation": punctuation,
        "commonOpeners": common_openers,
    }


def truncate_by_words(text: str, limit: int) -> str:
    words = text.strip().split()
    if len(words) <= limit:
        return " ".join(words)
    return " ".join(words[:limit])


def no_mode_reply(incoming_text: str) -> str:
    lower = incoming_text.lower()
    if any(k in lower for k in ["can you", "could you", "would you", "please", "need you", "join", "cover", "help"]):
        return "I cannot commit to that right now, sorry."
    if any(k in lower for k in ["party", "trip", "meet", "hang", "tonight", "weekend"]):
        return "I am going to pass for now, maybe another time."
    return "I cannot take this on right now, but thanks for checking."


def synth_reply(incoming_text: str, profile: dict, mode: str, style_override: str) -> str:
    if mode == "no_mode":
        return no_mode_reply(incoming_text)

    lowered = incoming_text.lower()
    if "?" in lowered:
        base = "yeah that works for me, i can do that"
    elif "thanks" in lowered or "thank you" in lowered:
        base = "of course, no problem at all"
    elif any(k in lowered for k in ["urgent", "asap", "quick"]):
        base = "got it, i will handle this shortly"
    else:
        base = "sounds good, noted on my side"

    style = (style_override or "").lower()
    if "concise" in style or "short" in style:
        base = truncate_by_words(base, 7)
    if "warm" in style or "friendly" in style:
        base += " appreciate you"
    if "formal" in style or "professional" in style:
        base = base.replace("yeah", "Yes").replace("got it", "Understood")

    openers = profile.get("commonOpeners", [])
    opener = random.choice(openers) if openers else ""
    composed = f"{opener} {base}".strip() if opener else base
    composed = truncate_by_words(composed, int(profile.get("avgWords", 12)) + 2)

    if float(profile.get("lowerCaseBias", 0.6)) > 0.75:
        composed = composed.lower()

    punctuation = profile.get("punctuation", "none")
    if punctuation in ["!", "?", "."]:
        composed += punctuation

    if float(profile.get("emojiBias", 0.05)) > 0.08:
        composed += " :)"

    return composed


def _recent_chat_context(contact: dict, limit: int = 8) -> str:
    lines = []
    for msg in (contact.get("messages") or [])[-limit:]:
        role = "You" if msg.get("role") == "you" else "Contact"
        text = str(msg.get("text", "")).strip()
        if text:
            lines.append(f"{role}: {text}")
    return "\n".join(lines)


def _ollama_generate(prompt: str) -> tuple[str, str]:
    body = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.65},
    }
    try:
        req = urllib.request.Request(
            url=OLLAMA_API_URL,
            method="POST",
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=OLLAMA_TIMEOUT_SEC) as resp:
            payload = resp.read().decode("utf-8")
        data = json.loads(payload)
        return str(data.get("response", "")).strip(), ""
    except Exception as exc:
        return "", str(exc)


def generate_reply(contact: dict, incoming_text: str, profile: dict, mode: str, style_override: str) -> tuple[str, dict]:
    if mode == "no_mode":
        return no_mode_reply(incoming_text), {"provider": "rule", "reason": "no_mode"}

    style_notes = [
        f"Average words: {int(profile.get('avgWords', 12))}",
        f"Lowercase bias: {float(profile.get('lowerCaseBias', 0.6)):.2f}",
        f"Typical punctuation: {profile.get('punctuation', 'none')}",
    ]
    if style_override:
        style_notes.append(f"Custom style override: {style_override}")

    prompt = (
        "You write one short text message reply as the user. "
        "Keep it natural and realistic. Do not mention AI. Do not add explanation. "
        "Output only the final reply text.\n\n"
        f"Style profile:\n- " + "\n- ".join(style_notes) + "\n\n"
        f"Recent conversation:\n{_recent_chat_context(contact)}\n\n"
        f"Incoming message to reply to:\n{incoming_text}\n"
    )

    generated, err = _ollama_generate(prompt)
    if generated:
        cleaned = " ".join(generated.split())
        if cleaned.lower().startswith("reply:"):
            cleaned = cleaned[6:].strip()
        cleaned = truncate_by_words(cleaned, int(profile.get("avgWords", 12)) + 4)

        if float(profile.get("lowerCaseBias", 0.6)) > 0.75:
            cleaned = cleaned.lower()

        punctuation = profile.get("punctuation", "none")
        if punctuation in ["!", "?", "."] and not cleaned.endswith(("!", "?", ".")):
            cleaned += punctuation

        if float(profile.get("emojiBias", 0.05)) > 0.08 and ":)" not in cleaned:
            cleaned += " :)"

        return cleaned, {"provider": "ollama", "model": OLLAMA_MODEL}

    fallback = synth_reply(incoming_text, profile, mode, style_override)
    return fallback, {"provider": "rule", "fallback": True, "ollamaError": err}


def sanitize_contact_id(value: str) -> str:
    sanitized = "".join(ch if ch.isalnum() else "_" for ch in value.lower()).strip("_")
    return sanitized or "instagram_contact"


def create_instagram_contact(store: dict, username: str, thread_id: str) -> dict:
    base_id = f"ig_{sanitize_contact_id(username)}"
    candidate = base_id
    idx = 2
    existing_ids = {c.get("id") for c in store.get("contacts", [])}
    while candidate in existing_ids:
        candidate = f"{base_id}_{idx}"
        idx += 1

    contact = {
        "id": candidate,
        "name": f"@{username}",
        "platform": "instagram",
        "instagramUsername": username,
        "instagramThreadId": str(thread_id),
        "instagramRecipientId": None,
        "mode": "normal",
        "autoReplyEnabled": True,
        "styleOverride": "",
        "minDelaySec": 20,
        "maxDelaySec": 75,
        "history": [],
        "messages": [],
    }
    store["contacts"].append(contact)
    return contact


def get_or_create_instagram_contact(store: dict, username: str, thread_id: str) -> dict:
    for contact in store.get("contacts", []):
        if (
            contact.get("platform") == "instagram"
            and str(contact.get("instagramThreadId") or "") == str(thread_id)
        ):
            if not contact.get("instagramUsername"):
                contact["instagramUsername"] = username
            return contact

    for contact in store.get("contacts", []):
        if contact.get("platform") == "instagram" and contact.get("instagramUsername") == username:
            contact["instagramThreadId"] = str(thread_id)
            return contact

    return create_instagram_contact(store, username, thread_id)


def _extract_instagram_message_text(message: Any) -> str:
    text = str(getattr(message, "text", "") or "").strip()
    if text:
        return text
    item_type = str(getattr(message, "item_type", "") or "")
    if item_type and item_type != "text":
        return f"[{item_type}]"
    return ""


def _resolve_instagram_username(thread: Any, sender_id: Any) -> str:
    users = getattr(thread, "users", []) or []
    for user in users:
        user_pk = str(getattr(user, "pk", "") or "")
        if user_pk and sender_id is not None and user_pk == str(sender_id):
            return str(getattr(user, "username", "") or f"user_{sender_id}")
    if sender_id is not None:
        return f"user_{sender_id}"
    return "instagram_user"


def send_instagram_reply(thread_id: str, text: str) -> tuple[bool, str]:
    store = read_store()
    instagram = store.get("instagram", {})
    auth_mode = str(instagram.get("authMode", "private") or "private")

    if auth_mode == "official":
        contact = next(
            (c for c in store.get("contacts", []) if str(c.get("instagramThreadId") or "") == str(thread_id)),
            None,
        )
        if not contact:
            return False, "Instagram contact not found for official send"

        recipient_id = str(contact.get("instagramRecipientId") or "")
        ig_business_id = str(instagram.get("instagramBusinessAccountId") or "")
        page_id = str(instagram.get("pageId") or "")
        access_token = str(instagram.get("pageAccessToken") or "")
        if not recipient_id or not ig_business_id or not access_token:
            return False, "Official Instagram API is missing recipient/business/token configuration"

        # Send via Page ID (messages endpoint is on the Page, not IG business account)
        send_id = page_id or ig_business_id

        try:
            _graph_post(
                f"{send_id}/messages",
                access_token,
                {
                    "recipient": {"id": recipient_id},
                    "message": {"text": text},
                    "messaging_type": "RESPONSE",
                },
            )
            return True, ""
        except Exception as exc:
            return False, f"Instagram official send failed: {exc}"

    with _instagram_runtime_lock:
        client = _instagram_client

    if not client:
        return False, "Instagram account is not connected"

    try:
        send_thread_id: Any = int(thread_id) if str(thread_id).isdigit() else str(thread_id)
        client.direct_send(text, thread_ids=[send_thread_id])
        return True, ""
    except Exception as exc:
        return False, f"Instagram send failed: {exc}"


def poll_instagram_official_once() -> dict:
    store = read_store()
    instagram = store.get("instagram", {})
    access_token = str(instagram.get("pageAccessToken") or "")
    ig_business_id = str(instagram.get("instagramBusinessAccountId") or "")
    page_id = str(instagram.get("pageId") or "")
    if not access_token or not ig_business_id:
        return {"processed": 0, "queued": 0, "connected": False, "error": "Official API credentials are missing"}

    # Conversations API must be called on the Page ID, not the IG business account ID
    conversations_id = page_id or ig_business_id

    seen_list = [str(v) for v in instagram.get("seenMessageIds", [])]
    seen_set = set(seen_list)
    queued_contact_ids = set()
    processed = 0

    try:
        convs = _graph_get(
            f"{conversations_id}/conversations",
            access_token,
            {"platform": "instagram", "fields": "id,participants"},
        )
        conversations = convs.get("data", []) or []
    except Exception as exc:
        error_detail = _error_text(exc)
        instagram["lastError"] = f"Instagram official poll failed: {error_detail}"
        instagram["connected"] = False
        write_store(store)
        return {"processed": 0, "queued": 0, "connected": False, "error": instagram["lastError"]}

    for conv in conversations:
        conversation_id = str(conv.get("id") or "")
        participants = ((conv.get("participants") or {}).get("data") or [])
        other_participant = None
        for participant in participants:
            pid = str(participant.get("id") or "")
            if pid and pid != ig_business_id:
                other_participant = participant
                break

        recipient_id = str((other_participant or {}).get("id") or "")
        username = str(
            (other_participant or {}).get("username")
            or (other_participant or {}).get("name")
            or f"user_{recipient_id or 'ig'}"
        )

        try:
            msg_payload = _graph_get(
                f"{conversation_id}/messages",
                access_token,
                {"fields": "id,from,to,message,created_time", "limit": 20},
            )
            messages = msg_payload.get("data", []) or []
        except Exception:
            continue

        for msg in reversed(messages):
            message_id = str(msg.get("id") or "")
            if not message_id or message_id in seen_set:
                continue

            seen_set.add(message_id)
            seen_list.append(message_id)

            from_id = str((msg.get("from") or {}).get("id") or "")
            if from_id == ig_business_id:
                continue

            text = str(msg.get("message") or "").strip()
            if not text:
                continue

            contact = get_or_create_instagram_contact(store, username, conversation_id)
            contact["instagramRecipientId"] = recipient_id or from_id
            incoming = {
                "id": random_id(),
                "role": "contact",
                "text": text,
                "ts": int(time.time() * 1000),
                "meta": {
                    "source": "instagram_official",
                    "instagramThreadId": conversation_id,
                    "instagramMessageId": message_id,
                },
            }
            contact["messages"].append(incoming)
            queued_contact_ids.add(contact["id"])
            processed += 1

    if len(seen_list) > 5000:
        seen_list = seen_list[-5000:]

    instagram["seenMessageIds"] = seen_list
    instagram["connected"] = True
    instagram["lastError"] = ""
    write_store(store)

    for contact_id in queued_contact_ids:
        queue_auto_reply(contact_id)

    return {"processed": processed, "queued": len(queued_contact_ids), "connected": True}


def poll_instagram_once() -> dict:
    store = read_store()
    instagram = store.get("instagram", {})
    auth_mode = str(instagram.get("authMode", "private") or "private")
    if auth_mode == "official":
        return poll_instagram_official_once()

    with _instagram_runtime_lock:
        client = _instagram_client

    if not client:
        return {"processed": 0, "queued": 0, "connected": False}

    seen_list = [str(v) for v in instagram.get("seenMessageIds", [])]
    seen_set = set(seen_list)
    queued_contact_ids = set()
    processed = 0

    try:
        own_user_id = str(getattr(client, "user_id", "") or "")
        threads = client.direct_threads(amount=20)
    except Exception as exc:
        instagram["lastError"] = f"Instagram poll failed: {exc}"
        instagram["connected"] = False
        write_store(store)
        return {"processed": 0, "queued": 0, "connected": False, "error": instagram["lastError"]}

    for thread in threads or []:
        thread_id = str(getattr(thread, "id", "") or "")
        messages = list(getattr(thread, "messages", []) or [])

        for message in reversed(messages):
            message_id = str(getattr(message, "id", "") or "")
            if not message_id or message_id in seen_set:
                continue

            seen_set.add(message_id)
            seen_list.append(message_id)

            sender_id = str(getattr(message, "user_id", "") or "")
            if sender_id and own_user_id and sender_id == own_user_id:
                continue

            text = _extract_instagram_message_text(message)
            if not text:
                continue

            username = _resolve_instagram_username(thread, sender_id)
            contact = get_or_create_instagram_contact(store, username, thread_id)
            incoming = {
                "id": random_id(),
                "role": "contact",
                "text": text,
                "ts": int(time.time() * 1000),
                "meta": {
                    "source": "instagram",
                    "instagramThreadId": str(thread_id),
                    "instagramMessageId": message_id,
                },
            }
            contact["messages"].append(incoming)
            queued_contact_ids.add(contact["id"])
            processed += 1

    if len(seen_list) > 5000:
        seen_list = seen_list[-5000:]

    instagram["seenMessageIds"] = seen_list
    instagram["connected"] = True
    instagram["lastError"] = ""
    write_store(store)

    for contact_id in queued_contact_ids:
        queue_auto_reply(contact_id)

    return {"processed": processed, "queued": len(queued_contact_ids), "connected": True}


def _instagram_worker_loop() -> None:
    while True:
        with _instagram_runtime_lock:
            stopper = _instagram_worker_stop
        if stopper is None or stopper.is_set():
            return

        store = read_store()
        poll_interval = int(store.get("instagram", {}).get("pollIntervalSec", 20) or 20)
        poll_interval = max(10, min(poll_interval, 300))

        poll_instagram_once()

        with _instagram_runtime_lock:
            stopper = _instagram_worker_stop
        if stopper is None:
            return
        if stopper.wait(poll_interval):
            return


def start_instagram_worker() -> None:
    global _instagram_worker_thread, _instagram_worker_stop
    with _instagram_runtime_lock:
        if _instagram_worker_thread and _instagram_worker_thread.is_alive():
            return

        _instagram_worker_stop = threading.Event()
        _instagram_worker_thread = threading.Thread(target=_instagram_worker_loop, daemon=True)
        _instagram_worker_thread.start()


def stop_instagram_worker() -> None:
    global _instagram_worker_thread, _instagram_worker_stop
    with _instagram_runtime_lock:
        stopper = _instagram_worker_stop
        worker = _instagram_worker_thread
        _instagram_worker_stop = None
        _instagram_worker_thread = None

    if stopper:
        stopper.set()
    if worker and worker.is_alive():
        worker.join(timeout=2)


def disconnect_instagram_runtime() -> None:
    global _instagram_client
    stop_instagram_worker()
    with _instagram_runtime_lock:
        client = _instagram_client
        _instagram_client = None
    if client:
        try:
            client.logout()
        except Exception:
            pass


def _generate_reply(contact_id: str, wait_sec: int) -> None:
    fresh = read_store()
    contact = next((c for c in fresh["contacts"] if c["id"] == contact_id), None)
    if not contact:
        return

    latest_incoming = next((m for m in reversed(contact["messages"]) if m.get("role") == "contact"), None)
    if not latest_incoming:
        return

    profile = analyze_style(contact.get("history", []))
    reply_text, generation_meta = generate_reply(
        contact,
        str(latest_incoming.get("text", "")),
        profile,
        str(contact.get("mode", "normal")),
        str(contact.get("styleOverride", "")),
    )

    outgoing = {
        "id": random_id(),
        "role": "you",
        "text": reply_text,
        "ts": int(time.time() * 1000),
        "meta": {"generated": True, "delaySec": wait_sec, **generation_meta},
    }

    contact["messages"].append(outgoing)
    contact["history"].append({"role": "you", "text": reply_text})

    if contact.get("platform") == "instagram" and contact.get("instagramThreadId"):
        sent, error = send_instagram_reply(str(contact.get("instagramThreadId")), reply_text)
        if not sent:
            outgoing.setdefault("meta", {})["instagramSendFailed"] = True
            outgoing["meta"]["instagramError"] = error

            instagram = fresh.get("instagram", {})
            instagram["lastError"] = error
            instagram["connected"] = False

    write_store(fresh)

    with _timers_lock:
        _timers.pop(contact_id, None)


def queue_auto_reply(contact_id: str) -> None:
    store = read_store()

    contact = next((c for c in store["contacts"] if c["id"] == contact_id), None)
    if not contact:
        return

    if not contact.get("autoReplyEnabled", True):
        return

    min_delay, max_delay = clamp_delay(contact.get("minDelaySec", 15), contact.get("maxDelaySec", 90))
    wait_sec = random.randint(min_delay, max_delay)

    with _timers_lock:
        old_timer = _timers.get(contact_id)
        if old_timer:
            old_timer.cancel()

        timer = threading.Timer(wait_sec, _generate_reply, args=(contact_id, wait_sec))
        timer.daemon = True
        _timers[contact_id] = timer
        timer.start()


@app.get("/")
def root():
    return send_from_directory(PUBLIC_DIR, "index.html")


@app.get("/api/state")
def api_state():
    return jsonify(read_store())


@app.post("/api/settings")
def api_settings():
    store = read_store()
    incoming = request.get_json(silent=True) or {}
    settings = store["settings"]

    settings["autoReplyEnabled"] = bool(incoming.get("autoReplyEnabled", settings["autoReplyEnabled"]))

    if incoming.get("defaultMinDelaySec") is not None:
        settings["defaultMinDelaySec"] = int(incoming["defaultMinDelaySec"])
    if incoming.get("defaultMaxDelaySec") is not None:
        settings["defaultMaxDelaySec"] = int(incoming["defaultMaxDelaySec"])

    write_store(store)
    return jsonify({"ok": True, "settings": settings})


@app.post("/api/contact/<contact_id>")
def api_contact(contact_id: str):
    store = read_store()
    body = request.get_json(silent=True) or {}

    contact = next((c for c in store["contacts"] if c["id"] == contact_id), None)
    if not contact:
        return jsonify({"error": "Contact not found"}), 404

    if body.get("mode") is not None:
        contact["mode"] = str(body["mode"])
    if body.get("autoReplyEnabled") is not None:
        contact["autoReplyEnabled"] = bool(body["autoReplyEnabled"])
    if body.get("styleOverride") is not None:
        contact["styleOverride"] = str(body["styleOverride"])
    if body.get("minDelaySec") is not None:
        contact["minDelaySec"] = int(body["minDelaySec"])
    if body.get("maxDelaySec") is not None:
        contact["maxDelaySec"] = int(body["maxDelaySec"])

    write_store(store)
    return jsonify({"ok": True, "contact": contact})


@app.post("/api/contact/<contact_id>/history")
def api_contact_history(contact_id: str):
    store = read_store()
    body = request.get_json(silent=True) or {}
    text = str(body.get("text", "")).strip()

    contact = next((c for c in store["contacts"] if c["id"] == contact_id), None)
    if not contact:
        return jsonify({"error": "Contact not found"}), 404

    if not text:
        return jsonify({"error": "history text is required"}), 400

    contact["history"].append({"role": "you", "text": text})
    write_store(store)
    return jsonify({"ok": True, "historyCount": len(contact["history"])})


@app.post("/api/incoming/<contact_id>")
def api_incoming(contact_id: str):
    store = read_store()
    body = request.get_json(silent=True) or {}
    text = str(body.get("text", "")).strip()

    contact = next((c for c in store["contacts"] if c["id"] == contact_id), None)
    if not contact:
        return jsonify({"error": "Contact not found"}), 404

    if not text:
        return jsonify({"error": "incoming text is required"}), 400

    incoming = {
        "id": random_id(),
        "role": "contact",
        "text": text,
        "ts": int(time.time() * 1000),
    }
    contact["messages"].append(incoming)
    write_store(store)

    queue_auto_reply(contact_id)
    return jsonify({"ok": True, "queued": True, "message": incoming})


@app.get("/api/instagram/status")
def api_instagram_status():
    store = read_store()
    instagram = store.get("instagram", {})
    _, import_error = load_instagram_client_class()
    return jsonify(
        {
            "enabled": bool(instagram.get("enabled", False)),
            "connected": bool(instagram.get("connected", False)),
            "username": str(instagram.get("username", "") or ""),
            "authMode": str(instagram.get("authMode", "private") or "private"),
            "instagramBusinessAccountId": str(instagram.get("instagramBusinessAccountId", "") or ""),
            "pollIntervalSec": int(instagram.get("pollIntervalSec", 20) or 20),
            "lastError": str(instagram.get("lastError", "") or ""),
            "instagramClientAvailable": import_error == "",
            "importError": import_error,
            "pythonExecutable": sys.executable,
        }
    )


@app.post("/api/instagram/connect")
def api_instagram_connect():
    payload = request.get_json(silent=True) or {}
    auth_mode = str(payload.get("authMode", "private") or "private").lower().strip()
    username = str(payload.get("username", "")).strip()
    password = str(payload.get("password", "")).strip()
    page_access_token = _sanitize_token(str(payload.get("pageAccessToken", "")))
    ig_business_id = str(payload.get("instagramBusinessAccountId", "")).strip()
    page_id = str(payload.get("pageId", "")).strip()
    poll_interval = int(payload.get("pollIntervalSec", 20) or 20)
    poll_interval = max(10, min(poll_interval, 300))

    if auth_mode == "official":
        if not page_access_token or not ig_business_id:
            return jsonify({"error": "pageAccessToken and instagramBusinessAccountId are required for official mode"}), 400

        # Auto-discover pageId and page-specific access token if not provided
        if not page_id:
            try:
                disc = discover_official_instagram_accounts(page_access_token)
                for acct in (disc.get("accounts") or []):
                    if str(acct.get("instagramBusinessAccountId") or "") == ig_business_id:
                        page_id = str(acct.get("pageId") or "")
                        # Swap user token for page-specific token if available
                        acct_token = str(acct.get("pageAccessToken") or "")
                        if acct_token:
                            page_access_token = acct_token
                        break
            except Exception:
                pass

        disconnect_instagram_runtime()

        store = read_store()
        instagram = store.get("instagram", {})
        instagram["enabled"] = True
        instagram["connected"] = True
        instagram["username"] = username
        instagram["authMode"] = "official"
        instagram["pageAccessToken"] = page_access_token
        instagram["instagramBusinessAccountId"] = ig_business_id
        instagram["pageId"] = page_id
        instagram["pollIntervalSec"] = poll_interval
        instagram["lastError"] = ""
        write_store(store)

        start_instagram_worker()
        sync_result = poll_instagram_once()
        return jsonify({"ok": True, "instagram": instagram, "sync": sync_result})

    client_class, import_error = load_instagram_client_class()
    if client_class is None:
        install_cmd = f'"{sys.executable}" -m pip install -r requirements.txt'
        return (
            jsonify(
                {
                    "error": "Instagram integration package missing in the Python environment running this app.",
                    "details": import_error,
                    "pythonExecutable": sys.executable,
                    "installCommand": install_cmd,
                }
            ),
            400,
        )

    if not username or not password:
        return jsonify({"error": "username and password are required"}), 400

    client = client_class()
    try:
        _load_instagram_session(client, username)
        client.login(username=username, password=password)
        _save_instagram_session(client, username)
    except Exception as exc:
        store = read_store()
        instagram = store.get("instagram", {})
        instagram["enabled"] = False
        instagram["connected"] = False
        instagram["username"] = username
        instagram["pollIntervalSec"] = poll_interval
        friendly = _friendly_instagram_login_error(exc)
        instagram["lastError"] = friendly
        write_store(store)
        return (
            jsonify(
                {
                    "error": instagram["lastError"],
                    "details": str(exc),
                    "pythonExecutable": sys.executable,
                }
            ),
            400,
        )

    with _instagram_runtime_lock:
        global _instagram_client
        _instagram_client = client

    store = read_store()
    instagram = store.get("instagram", {})
    instagram["enabled"] = True
    instagram["connected"] = True
    instagram["username"] = username
    instagram["authMode"] = "private"
    instagram["pageAccessToken"] = ""
    instagram["instagramBusinessAccountId"] = ""
    instagram["pollIntervalSec"] = poll_interval
    instagram["lastError"] = ""
    write_store(store)

    start_instagram_worker()
    sync_result = poll_instagram_once()
    return jsonify({"ok": True, "instagram": instagram, "sync": sync_result})


@app.post("/api/instagram/validate-official")
def api_instagram_validate_official():
    payload = request.get_json(silent=True) or {}
    page_access_token = _sanitize_token(str(payload.get("pageAccessToken", "")))
    ig_business_id = str(payload.get("instagramBusinessAccountId", "")).strip()

    if not page_access_token or not ig_business_id:
        return jsonify({"error": "pageAccessToken and instagramBusinessAccountId are required"}), 400

    if len(page_access_token) < 20:
        return jsonify({"error": "Token looks too short. Paste the full Page Access Token from Meta Graph API Explorer."}), 400
    if " " in page_access_token:
        return jsonify({"error": "Token contains spaces. Copy the token carefully with no extra whitespace."}), 400

    result = validate_official_instagram_setup(page_access_token, ig_business_id)
    return jsonify({"ok": True, "result": result})


@app.post("/api/instagram/discover-official")
def api_instagram_discover_official():
    payload = request.get_json(silent=True) or {}
    page_access_token = _sanitize_token(str(payload.get("pageAccessToken", "")))
    if not page_access_token:
        return jsonify({"error": "pageAccessToken is required"}), 400

    try:
        result = discover_official_instagram_accounts(page_access_token)
        return jsonify({"ok": True, "result": result})
    except Exception as exc:
        return jsonify({"error": f"Could not discover Instagram accounts: {_error_text(exc)}"}), 400


@app.post("/api/instagram/disconnect")
def api_instagram_disconnect():
    disconnect_instagram_runtime()

    store = read_store()
    instagram = store.get("instagram", {})
    instagram["enabled"] = False
    instagram["connected"] = False
    instagram["pageAccessToken"] = ""
    instagram["instagramBusinessAccountId"] = ""
    write_store(store)

    return jsonify({"ok": True})


@app.post("/api/instagram/sync")
def api_instagram_sync():
    result = poll_instagram_once()
    return jsonify({"ok": True, "result": result})


if __name__ == "__main__":
    ensure_store()
    store = read_store()
    store["instagram"]["connected"] = False
    write_store(store)
    app.run(host="0.0.0.0", port=3000, debug=False)
