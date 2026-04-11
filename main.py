from flask import Flask, request, jsonify
from reply import generate_reply, send_reply

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
            message_text = event.get("message", {}).get("text")

            print(f"\nMessage from {sender_id}: {message_text}", flush=True)

            reply = generate_reply(message_text)
            send_reply(sender_id, reply)

    return jsonify({"status": "received"}), 200


if __name__ == "__main__":  
    app.run(host="0.0.0.0", port=5000, debug=False)