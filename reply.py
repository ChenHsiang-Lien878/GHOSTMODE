import requests
from dotenv import load_dotenv
import os

load_dotenv()
IG_USER_ID = "17841434171692913"
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")

def generate_reply(message):
    return "Hey! I'm in ghost mode right now 👻"

def send_reply(user_id, text):
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