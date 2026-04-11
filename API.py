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
    try:
        response = client.models.generate_content(
            model=model_name,
            contents=prompt
        )
        return (response.text or "").strip()
    except Exception as e:
        return f"Error: {str(e)}"


def generate_instagram_reply(message, conversation_history, mode="normal"):
    print("mode is" + mode)
    if mode == "no":
        prompt = f"""
You are writing a short Instagram DM reply.

Mode: No Mode

Rules:
- Always reject, decline, or say no but make it kind
- Never agree to the request
- Sound casual and human
- Keep it short, max 1 sentence
- Keep it under 15 words
- Do not mention being an AI
- Do not be overly rude
- Vary the wording so it does not sound repetitive

Conversation history:
{conversation_history}

Latest user message:
"{message}"

Write the next assistant reply only.
"""
    else:
        prompt = f"""
You are writing a short Instagram DM auto-reply.

Rules:
- Reply in 1 short sentence only
- Sound casual and human
- Match the tone of the conversation
- Do not mention being an AI
- Keep it under 18 words
- Do not over-explain

Conversation history:
{conversation_history}

Latest user message:
"{message}"

Write the next assistant reply only.
"""

    return generate_text(prompt)