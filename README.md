# GhostMode

GhostMode is a local web app prototype for AI-assisted auto-replies that imitate your texting style.

## What this build includes

- Auto-reply engine for incoming messages
- Style mimicry from your historical messages per contact
- Per-contact behavior modes
- `No mode` to automatically avoid commitments
- Human-like delayed response intervals (randomized between min/max seconds)
- Contact-level style override prompt (e.g. concise, friendly, professional)
- Instagram account bridge for incoming DMs (connect, poll, and auto-reply)
- Demo chat UI to simulate messages and inspect generated responses

## Tech stack

- Python + Flask backend
- Vanilla HTML/CSS/JS frontend
- JSON file persistence in `data/store.json`

## Run locally

1. Install Python 3.10+ from https://www.python.org/
2. In project root, use the project virtualenv and run:
   - `./run.ps1`
3. Or run manually with virtualenv Python:
   - `.venv/Scripts/python.exe -m pip install -r requirements.txt`
   - `.venv/Scripts/python.exe app.py`
4. Open:
   - `http://localhost:3000`

## Local AI model (Llama 3)

GhostMode now uses a local Ollama model for reply generation by default.

1. Install Ollama: https://ollama.com/
2. Pull the model:
   - `ollama pull llama3`
3. Ensure Ollama is running locally (default endpoint `http://127.0.0.1:11434`).

Optional environment variables:

- `OLLAMA_MODEL` (default: `llama3`)
- `OLLAMA_API_URL` (default: `http://127.0.0.1:11434/api/generate`)
- `OLLAMA_TIMEOUT_SEC` (default: `45`)

## How to demo the pitch

1. Select a contact from the left panel.
2. Add past messages in "Add style-training line" to tune style mimicry.
3. Configure mode and delay interval for that contact.
4. Send a simulated incoming message in the chat panel.
5. Wait for the configured random delay.
6. A generated AI response appears as if sent by you.

## API endpoints

- `GET /api/state` - full app state
- `POST /api/settings` - global settings (auto-reply toggle)
- `POST /api/contact/:contactId` - update mode/style/delay per contact
- `POST /api/contact/:contactId/history` - add style-training sample
- `POST /api/incoming/:contactId` - simulate incoming message and queue auto-reply
- `GET /api/instagram/status` - instagram bridge status
- `POST /api/instagram/connect` - login/connect instagram account
- `POST /api/instagram/disconnect` - disconnect instagram bridge
- `POST /api/instagram/sync` - pull inbox once immediately

## Notes

- This is a prototype using local Llama 3 via Ollama with rule-based fallback when Ollama is unavailable.
- In production, add stronger moderation/safety controls and robust model hosting/monitoring.
- Instagram integration uses polling and requires valid account login.
- If Instagram says password is correct but login is blocked/blacklisted, it is a network security block (IP reputation), not necessarily bad credentials.
- Use Official API mode in the UI (Meta page access token + Instagram business account ID) to avoid private password login blocks.
- Recovery steps for blocked/challenge logins:
   - Disable VPN/proxy and retry from a normal residential network.
   - Log in successfully in Instagram web/app once from the same network.
   - Complete any email/challenge prompts, then reconnect in GhostMode.
   - Wait 15-60 minutes after repeated failed attempts before trying again.
