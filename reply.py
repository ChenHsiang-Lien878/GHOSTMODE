import os
import requests
from dotenv import load_dotenv
from API import generate_instagram_reply

load_dotenv()

IG_USER_ID = "17841434171692913"
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")


def generate_reply(message: str, conversation_history: str) -> str:
    reply = generate_instagram_reply(message, conversation_history)

    if not reply or reply.startswith("Error:"):
        return "Hey, I’m a bit busy right now, I’ll get back to you soon."

    return reply


def send_reply(user_id: str, text: str) -> None:
    url = f"https://graph.instagram.com/v25.0/{IG_USER_ID}/messages"

    payload = {
        "recipient": {"id": user_id},
        "message": {"text": text}
    }

    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    response = requests.post(url, headers=headers, json=payload, timeout=30)
    print("Reply sent:", response.text, flush=True)