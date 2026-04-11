from flask import Flask, request, jsonify
from reply import generate_reply, send_reply, IG_USER_ID

app = Flask(__name__)

VERIFY_TOKEN = "ghostmode123"

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
            recipient_id = event.get("recipient", {}).get("id")
            message_text = event.get("message", {}).get("text")

            print("\n--- EVENT ---", flush=True)
            print("sender_id   =", sender_id, flush=True)
            print("recipient_id=", recipient_id, flush=True)
            print("message_text=", message_text, flush=True)
            print("IG_USER_ID  =", IG_USER_ID, flush=True)

            if not message_text:
                print("Skipped: no text", flush=True)
                continue

            if str(sender_id) == str(IG_USER_ID):
                print("Skipped: self message", flush=True)
                continue

            print("Sending reply...", flush=True)
            reply = generate_reply(message_text)
            send_reply(sender_id, reply)

    return jsonify({"status": "received"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)