from API import generate_instagram_reply
import os
import requests
from dotenv import load_dotenv

load_dotenv()

IG_USER_ID = "17841434171692913"
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")


def generate_reply(message: str, conversation_history: str, mode: str = "normal") -> str:
    reply = generate_instagram_reply(message, conversation_history, mode)

    if not reply or str(reply).startswith("Error:"):
        if mode == "no":
            return "Nah, can't do that."
        return "Hey, I’m a bit busy right now, I’ll get back to you soon."

    return reply



def send_reply(user_id: str, text: str) -> tuple[bool, str]:
    url = f"https://graph.instagram.com/v25.0/{IG_USER_ID}/messages"

    payload = {
        "recipient": {"id": user_id},
        "message": {"text": text}
    }

    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        body = response.text
        ok = response.status_code == 200 and "error" not in body.lower()
        print("Reply sent:", body, flush=True)
        return ok, body
    except Exception as e:
        return False, str(e)