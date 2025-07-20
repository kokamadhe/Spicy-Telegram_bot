import os
import json
from flask import Flask, request, jsonify, redirect
import stripe
import requests
from dotenv import load_dotenv

load_dotenv()

# Load environment variables
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
STRIPE_PRICE_ID = os.getenv("STRIPE_PRICE_ID")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
YOUR_RENDER_URL = "https://spicy-telegram-bot-5.onrender.com"

BOT_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
PREMIUM_USERS_FILE = "premium_users.json"

app = Flask(__name__)
stripe.api_key = STRIPE_SECRET_KEY


### --- UTILITIES --- ###

def load_premium_users():
    if os.path.exists(PREMIUM_USERS_FILE):
        try:
            with open(PREMIUM_USERS_FILE, "r") as f:
                return set(map(int, json.load(f)))
        except Exception as e:
            print(f"Error loading premium users file: {e}")
    return set()

def save_premium_user(user_id):
    users = load_premium_users()
    if user_id not in users:
        users.add(user_id)
        try:
            with open(PREMIUM_USERS_FILE, "w") as f:
                json.dump(list(users), f)
        except Exception as e:
            print(f"Error saving premium users file: {e}")

def is_premium(user_id):
    return user_id in load_premium_users()

def send_message(chat_id, text):
    resp = requests.post(f"{BOT_API_URL}/sendMessage", json={
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    })
    if not resp.ok:
        print(f"Failed to send message: {resp.status_code} - {resp.text}")

def send_voice_message(chat_id, text):
    if not ELEVENLABS_API_KEY:
        send_message(chat_id, "⚠️ Voice reply unavailable: missing ElevenLabs API key.")
        return

    tts_url = "https://api.elevenlabs.io/v1/text-to-speech/EXAVITQu4vr4xnSDxMaL/stream"
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json"
    }
    data = {
        "text": text,
        "voice_settings": {
            "stability": 0.75,
            "similarity_boost": 0.75
        }
    }
    response = requests.post(tts_url, headers=headers, json=data, stream=True)
    if response.status_code == 200:
        files = {
            "audio": ("voice.mp3", response.raw, "audio/mpeg")
        }
        resp = requests.post(f"{BOT_API_URL}/sendAudio", data={"chat_id": chat_id}, files=files)
        if not resp.ok:
            print(f"Failed to send voice message: {resp.status_code} - {resp.text}")
    else:
        print(f"ElevenLabs TTS error: {response.status_code} - {response.text}")
        send_message(chat_id, "Sorry, I couldn't generate the voice message.")

def query_openrouter(prompt: str) -> str:
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    json_data = {
        "model": "nous-hermes-2",
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }
    response = requests.post(url, headers=headers, json=json_data)
    if response.ok:
        data = response.json()
        return data["choices"][0]["message"]["content"]
    else:
        print("OpenRouter API error:", response.text)
        return "Sorry, I couldn't process that."


### --- FLASK ROUTES --- ###

@app.route('/')
def home():
    return "🔥 Spicy Bot is live!"

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "")

        if not is_premium(chat_id) and text not in ["/start", "/pay"]:
            send_message(chat_id, "🚫 This is a premium-only bot.\nUse /pay to unlock access.")
            return jsonify(ok=True)

        if text == "/start":
            send_message(chat_id, "🔥 Welcome to TheSpicyChatBot!\n\nTo chat with me, please unlock premium 😉")
        elif text == "/pay":
            payment_link = f"{YOUR_RENDER_URL}/pay?user_id={chat_id}"
            send_message(chat_id, f"💳 Click below to purchase premium:\n{payment_link}")
        elif is_premium(chat_id):
            ai_response = query_openrouter(text)
            send_message(chat_id, ai_response)
            send_voice_message(chat_id, ai_response)

    return jsonify(ok=True)

@app.route('/pay')
def pay():
    user_id = request.args.get("user_id")
    if not user_id:
        return "Missing user_id", 400

    checkout = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{
            "price": STRIPE_PRICE_ID,
            "quantity": 1
        }],
        mode="subscription",
        success_url=f"{YOUR_RENDER_URL}/success?user_id={user_id}",
        cancel_url=f"{YOUR_RENDER_URL}/cancel",
        metadata={"user_id": user_id}
    )
    return redirect(checkout.url, code=303)

@app.route('/success')
def success():
    user_id = request.args.get("user_id")
    if user_id:
        save_premium_user(int(user_id))
        send_message(int(user_id), "✅ Thank you for your payment!\nYou now have premium access.")
    return "Payment successful!"

@app.route('/cancel')
def cancel():
    return "Payment cancelled."

@app.route('/stripe-webhook', methods=['POST'])
def stripe_webhook():
    payload = request.data
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except stripe.error.SignatureVerificationError:
        return "Invalid signature", 400

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        metadata = session.get("metadata", {})
        user_id = metadata.get("user_id")
        if user_id:
            save_premium_user(int(user_id))
            send_message(int(user_id), "✅ Payment confirmed! You now have full access.")

    return "Webhook received", 200


### --- START APP --- ###

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)





















