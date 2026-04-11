from flask import Flask, request, jsonify
from reply import generate_reply, send_reply, IG_USER_ID
from history import add_message, format_history_for_prompt
from settings import load_settings
app = Flask(__name__)

VERIFY_TOKEN = "ghostmode123"
GHOST_MODE = True


@app.route("/", methods=["GET"])
def home():
    return "Server is running", 200


@app.route("/webhook", methods=["GET"])
def verify_webhook():
    if (
        request.args.get("hub.mode") == "subscribe"
        and request.args.get("hub.verify_token") == VERIFY_TOKEN
    ):
        return request.args.get("hub.challenge"), 200
    return "Verification failed", 403


@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(silent=True) or {}

    for entry in data.get("entry", []):
        for event in entry.get("messaging", []):
            sender_id = event.get("sender", {}).get("id")
            message_text = event.get("message", {}).get("text")

            if not message_text:
                continue

            if str(sender_id) == str(IG_USER_ID):
                continue

            print(f"\nNew message from {sender_id}: {message_text}", flush=True)

            # Save user's new message first
            add_message(sender_id, "user", message_text)

            settings = load_settings()
            reply_mode = settings["reply_mode"]
            ghost_mode = settings["ghost_mode"]

            if ghost_mode:
                history_text = format_history_for_prompt(sender_id)
                print(reply_mode, flush=True)
                reply = generate_reply(message_text, history_text, reply_mode)
                send_reply(sender_id, reply)
                add_message(sender_id, "assistant", reply)

    return jsonify({"status": "received"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)