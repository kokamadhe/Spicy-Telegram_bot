import os
import requests
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import stripe

load_dotenv()

app = Flask(__name__)

# 🔐 Load secrets
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL_LAB_API_KEY = os.getenv("MODEL_LAB_API_KEY")
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
STRIPE_PRICE_ID = os.getenv("STRIPE_PRICE_ID")

# 🌍 Stripe + Telegram setup
stripe.api_key = STRIPE_SECRET_KEY
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
PAID_USERS = set()  # Add premium Telegram IDs here manually or via Stripe webhook
PAID_USERS.add(1985536979)  # You can remove this after testing

# 🔁 Telegram utils
def send_telegram_message(chat_id, text):
    url = f"{TELEGRAM_API_URL}/sendMessage"
    data = {"chat_id": chat_id, "text": text}
    requests.post(url, json=data)

def send_telegram_photo(chat_id, photo_url, caption=None):
    url = f"{TELEGRAM_API_URL}/sendPhoto"
    data = {"chat_id": chat_id, "photo": photo_url}
    if caption:
        data["caption"] = caption
    requests.post(url, data=data)

# 🧠 AI text generation
def generate_reply(message):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    body = {
        "model": "nousresearch/nous-hermes-2-mixtral-8x7b-dpo",
        "messages": [
            {"role": "system", "content": "You are an uncensored, flirty, NSFW AI girlfriend."},
            {"role": "user", "content": message}
        ],
        "max_tokens": 1000
    }

    response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=body)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]

# 🎨 AI image generation
def generate_image(prompt):
    url = "https://api.modellab.com/v1/stable-diffusion"
    headers = {
        "Authorization": f"Bearer {MODEL_LAB_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "prompt": prompt,
        "model": "realisticVision",
        "output_format": "url"
    }

    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    return response.json()["output"][0]

# 💳 Stripe Checkout Link
def create_stripe_checkout_link(user_id):
    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{"price": STRIPE_PRICE_ID, "quantity": 1}],
        mode="payment",
        success_url="https://t.me/YourBotUsername?start=success",
        cancel_url="https://t.me/YourBotUsername?start=cancel",
        metadata={"telegram_id": str(user_id)}
    )
    return session.url

# 🤖 Telegram update handler
def handle_telegram_update(update):
    if "message" not in update:
        return

    message = update["message"]
    chat_id = message["chat"]["id"]
    user_id = message["from"]["id"]
    text = message.get("text", "")

    try:
        if text.startswith("/pay"):
            url = create_stripe_checkout_link(user_id)
            send_telegram_message(chat_id, f"💳 Pay to unlock premium: {url}")
            return

        if user_id not in PAID_USERS:
            send_telegram_message(chat_id, "🔒 You need to pay first. Use /pay to unlock premium access.")
            return

        if text.startswith("/image"):
            prompt = text.replace("/image", "").strip()
            if not prompt:
                send_telegram_message(chat_id, "❗ Please provide a prompt after /image.")
                return
            send_telegram_message(chat_id, "🎨 Generating image, please wait...")
            image_url = generate_image(prompt)
            send_telegram_photo(chat_id, image_url, caption=f"🖼️ Prompt: {prompt}")
        else:
            send_telegram_message(chat_id, "💬 Thinking...")
            reply = generate_reply(text)
            send_telegram_message(chat_id, reply)

    except Exception as e:
        send_telegram_message(chat_id, f"❌ Error: {str(e)}")

# 🌐 Home and Webhook Routes
@app.route("/", methods=["GET"])
def home():
    return "Bot is running", 200

@app.route("/", methods=["POST"])
def telegram_webhook():
    update = request.get_json()
    handle_telegram_update(update)
    return "", 200

@app.route("/stripe-webhook", methods=["POST"])
def stripe_webhook():
    payload = request.data
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)

        if event["type"] == "checkout.session.completed":
            session = event["data"]["object"]
            telegram_id = int(session["metadata"]["telegram_id"])
            PAID_USERS.add(telegram_id)

    except Exception as e:
        return f"⚠️ Webhook Error: {str(e)}", 400

    return "", 200

# ▶️ Run app
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))








