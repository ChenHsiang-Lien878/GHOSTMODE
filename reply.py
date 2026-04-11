import requests

def generate_reply(message):
    return "Hey! I'm in ghost mode right now 👻"

IG_USER_ID = "17841434171692913"

ACCESS_TOKEN = "IGAAbbsS6aptNBZAFl1TVlnVHViQlZAocFpmS0tFZA1dueHhzTy0zem1Wcm5WU21kWGk0LV9IaTlKWU8ybkE3OUZACdk1TTFlxMG1JNVByeUNCdTYzRFkzb1h3bVdaR0xYT2ZAucERoZAnJQUjZAVTDl4Qkc1X0ItbzBaMjN1VWw0YktJSQZDZD"


def send_reply(user_id, text):
    url = f"https://graph.instagram.com/v25.0/{IG_USER_ID}/messages"

    payload = {
        "recipient": {"id": user_id},
        "message": {"text": text}
    }

    params = {
        "access_token": ACCESS_TOKEN
    }

    response = requests.post(url, params=params, json=payload)

    print("Reply sent:", response.text, flush=True)