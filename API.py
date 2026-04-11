import os
from dotenv import load_dotenv
import google.genai as genai

load_dotenv()

API_KEY = os.getenv("GOOGLE_API_KEY")

if not API_KEY:
    key_file = os.path.join(os.path.dirname(__file__), "key.txt")
    if os.path.exists(key_file):
        with open(key_file, "r", encoding="utf-8") as f:
            API_KEY = f.read().strip()

if not API_KEY:
    raise ValueError("GOOGLE_API_KEY not found in .env or key.txt")

client = genai.Client(api_key=API_KEY)

DEFAULT_MODEL = "models/gemini-2.5-flash"


def generate_text(prompt: str, model_name: str = DEFAULT_MODEL) -> str:
    """
    Generate text using Google's Gemini API.
    """
    try:
        response = client.models.generate_content(
            model=model_name,
            contents=prompt
        )
        return (response.text or "").strip()
    except Exception as e:
        return f"Error: {str(e)}"


def generate_instagram_reply(message: str) -> str:
    """
    Generate a short Instagram DM auto-reply.
    """
    prompt = f"""
You are writing a short Instagram DM auto-reply.

Rules:
- Reply in 1 short sentence only
- Sound casual and human
- Do not use hashtags
- Do not mention being an AI
- Do not over-explain
- Keep it under 20 words

Incoming message: "{message}"
"""
    return generate_text(prompt)


if __name__ == "__main__":
    test_message = "Hey are you free later?"
    print("Generated Reply:")
    print(generate_instagram_reply(test_message))