import os
import sqlite3
from flask import Flask, request, jsonify, redirect
import stripe
import requests
from dotenv import load_dotenv

load_dotenv()

# Environment variables
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
STRIPE_PRICE_ID = os.getenv("STRIPE_PRICE_ID")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

YOUR_RENDER_URL = "https://spicy-telegram-bot-5.onrender.com"
BOT_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

app = Flask(__name__)
stripe.api_key = STRIPE_SECRET_KEY

# --- SQLite DB setup ---
DB_PATH = "users.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS premium_users (
            user_id INTEGER PRIMARY KEY
        )
    """)
    conn.commit()
    conn.close()

def add_premium_user(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO premium_users (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()

def is_premium_user(user_id: int) -> bool:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT 1 FROM premium_users WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result is not None

# Initialize DB on startup
init_db()

# --- Telegram & AI functions ---

def query_openrouter(prompt: str) -> str:
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    json_data = {
        "model": "nous-hermes-2",
        "messages": [{"role": "user", "content": prompt}]
    }
    response = requests.post(url, headers=headers, json=json_data)
    if response.ok:
        data = response.json()
        return data["choices"][0]["message"]["content"]
    else:
        print("OpenRouter API error:", response.text)
        return "⚠️ Sorry, something went wrong with AI."

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

# --- Flask routes ---

@app.route('/')
def home():
    return "🔥 Spicy Bot is live!"

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()

    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "")

        # Basic command responses
        if text == "/start":
            send_message(chat_id, "🔥 Welcome to SpicyChatBot!\nUse /pay to unlock premium features.")
            return jsonify(ok=True)

        if text == "/pay":
            payment_link = f"{YOUR_RENDER_URL}/pay?user_id={chat_id}"
            send_message(chat_id, f"💳 Click to purchase premium:\n{payment_link}")
            return jsonify(ok=True)

        # Check premium status
        if not is_premium_user(chat_id):
            send_message(chat_id, "🚫 This is a premium-only bot.\nUse /pay to unlock access.")
            return jsonify(ok=True)

        # Process AI response
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
        user_id_int = int(user_id)
        add_premium_user(user_id_int)
        send_message(user_id_int, "✅ Thank you for your payment!\nYou now have premium access.")
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
            user_id_int = int(user_id)
            add_premium_user(user_id_int)
            send_message(user_id_int, "✅ Payment confirmed! You now have full access.")

    return "Webhook received", 200

# Run server
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)























