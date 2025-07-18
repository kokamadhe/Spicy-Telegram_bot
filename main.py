from flask import Flask, request, jsonify
import requests
import os
import stripe
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Load environment variables
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL_LAB_API_KEY = os.getenv("MODEL_LAB_API_KEY")
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_PRICE_ID = os.getenv("STRIPE_PRICE_ID")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

stripe.api_key = STRIPE_SECRET_KEY
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

# TEMPORARY in-memory premium user list
PAID_USERS = set()

def send_telegram_message(chat_id, text):
    url = f"{TELEGRAM_API_URL}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }
    requests.post(url, json=data)

def generate_text(prompt):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "nous-hermes2",
        "messages": [
            {"role": "system", "content": "You are a flirty girlfriend. Be playful and spicy."},
            {"role": "user", "content": prompt}
        ]
    }
    res = requests.post("https://openrouter.ai/api/v1/chat/completions", json=data, headers=headers)
    return res.json()["choices"][0]["message"]["content"]

def generate_image(prompt):
    headers = {
        "Authorization": f"Bearer {MODEL_LAB_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "realistic-vision-v5",
        "prompt": prompt,
        "num_images": 1
    }
    res = requests.post("https://api.modellab.ai/v1/image/generate", json=data, headers=headers)
    return res.json()["data"][0]["url"]

@app.route("/webhook", methods=["POST"])
def telegram_webhook():
    data = request.json
    if "message" not in data:
        return "ok"
    
    chat_id = data["message"]["chat"]["id"]
    user_id = str(chat_id)
    text = data["message"].get("text", "")

    if text.startswith("/start"):
        send_telegram_message(chat_id, "Hey! I'm Aria 🔥 Your spicy AI girl. Type anything or /image to play. Use /pay to unlock premium 💖")
    elif text.startswith("/pay"):
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="payment",
            line_items=[{
                "price": STRIPE_PRICE_ID,
                "quantity": 1
            }],
            success_url="https://t.me/YourBotUsername?start=success",
            cancel_url="https://t.me/YourBotUsername?start=cancel",
            metadata={"user_id": user_id}
        )
        pay_url = session.url
        send_telegram_message(chat_id, f"💳 [Click here to unlock premium]({pay_url})")
    elif text.startswith("/image"):
        if user_id not in PAID_USERS:
            send_telegram_message(chat_id, "🚫 This feature is premium. Use /pay to unlock.")
        else:
            prompt = text.replace("/image", "").strip()
            if not prompt:
                send_telegram_message(chat_id, "Please enter a prompt like:\n`/image a sexy girl in leather`")
            else:
                image_url = generate_image(prompt)
                requests.post(f"{TELEGRAM_API_URL}/sendPhoto", json={"chat_id": chat_id, "photo": image_url})
    else:
        if user_id not in PAID_USERS:
            send_telegram_message(chat_id, "💬 I'm free to chat! Use /pay to unlock image generation 🔥")
        else:
            reply = generate_text(text)
            send_telegram_message(chat_id, reply)
    
    return "ok"

@app.route("/stripe-webhook", methods=["POST"])
def stripe_webhook():
    payload = request.data
    sig_header = request.headers.get("Stripe-Signature")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except stripe.error.SignatureVerificationError:
        return "Invalid signature", 400

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        user_id = session["metadata"]["user_id"]
        PAID_USERS.add(user_id)
        print(f"✅ Premium activated for user: {user_id}")

    return "ok", 200

@app.route("/")
def index():
    return "Bot is live!"










