from flask import Flask, request, jsonify, redirect
import os, json, stripe, requests
from dotenv import load_dotenv
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters
from io import BytesIO

load_dotenv()

app = Flask(__name__)

# ENV variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_PRICE_ID = os.getenv("STRIPE_PRICE_ID")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
BASE_URL = os.getenv("BASE_URL", "https://spicy-telegram-bot-5.onrender.com")

# Stripe setup
stripe.api_key = STRIPE_SECRET_KEY

# Telegram bot setup
bot = Bot(token=BOT_TOKEN)
dispatcher = Dispatcher(bot, None, use_context=True)

# Load/save premium users
PREMIUM_USERS_FILE = "premium_users.json"

def load_premium_users():
    if os.path.exists(PREMIUM_USERS_FILE):
        with open(PREMIUM_USERS_FILE, "r") as f:
            return set(json.load(f))
    return set()

def save_premium_users(users):
    with open(PREMIUM_USERS_FILE, "w") as f:
        json.dump(list(users), f)

premium_users = load_premium_users()

# ElevenLabs TTS
def generate_voice(text):
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json"
    }
    data = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75
        }
    }
    response = requests.post(
        "https://api.elevenlabs.io/v1/text-to-speech/21m00Tcm4TlvDq8ikWAM",
        headers=headers,
        json=data
    )
    return BytesIO(response.content)

# OpenRouter AI response
def generate_ai_reply(prompt):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "nous-hermes2",
        "messages": [
            {"role": "system", "content": "You're a flirty spicy chatbot."},
            {"role": "user", "content": prompt}
        ]
    }
    response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data)
    return response.json()["choices"][0]["message"]["content"]

# Handlers
def start(update, context):
    user_id = update.effective_user.id
    if user_id in premium_users:
        update.message.reply_text("🔥 Welcome back, premium user!")
    else:
        pay_link = f"{BASE_URL}/pay?user_id={user_id}"
        update.message.reply_text(
            f"🔥 Welcome to TheSpicyChatBot!\n\nTo chat with me, please unlock premium 😉\n"
            f"💳 Click below to purchase premium:\n{pay_link}"
        )

def handle_message(update, context):
    user_id = update.effective_user.id
    if user_id not in premium_users:
        update.message.reply_text("Please purchase premium first using /pay.")
        return
    text = update.message.text
    reply = generate_ai_reply(text)
    update.message.reply_text(reply)

    # Voice reply
    voice_data = generate_voice(reply)
    voice_data.name = "voice.ogg"
    bot.send_voice(chat_id=update.effective_chat.id, voice=voice_data)

def pay(update, context):
    user_id = update.effective_user.id
    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{"price": STRIPE_PRICE_ID, "quantity": 1}],
        mode="payment",
        success_url=f"{BASE_URL}/success?user_id={user_id}",
        cancel_url=f"{BASE_URL}/cancel"
    )
    update.message.reply_text(f"💳 Click here to pay: {session.url}")

# Telegram webhook route
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def telegram_webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "OK"

# Stripe webhook
@app.route("/stripe_webhook", methods=["POST"])
def stripe_webhook():
    payload = request.data
    sig_header = request.headers.get("Stripe-Signature")
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
        if event["type"] == "checkout.session.completed":
            user_id = int(request.args.get("user_id", 0))
            premium_users.add(user_id)
            save_premium_users(premium_users)
            bot.send_message(chat_id=user_id, text="🎉 You are now a premium user! Start chatting.")
    except Exception as e:
        return str(e), 400
    return "", 200

# Payment routes
@app.route("/pay")
def pay_route():
    user_id = request.args.get("user_id")
    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{"price": STRIPE_PRICE_ID, "quantity": 1}],
        mode="payment",
        success_url=f"{BASE_URL}/success?user_id={user_id}",
        cancel_url=f"{BASE_URL}/cancel"
    )
    return redirect(session.url, code=303)

@app.route("/success")
def success():
    user_id = int(request.args.get("user_id", 0))
    premium_users.add(user_id)
    save_premium_users(premium_users)
    bot.send_message(chat_id=user_id, text="✅ Payment successful! You're now a premium user.")
    return "Payment successful! You may now return to Telegram."

@app.route("/cancel")
def cancel():
    return "Payment canceled."

# Start
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("pay", pay))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

@app.route("/")
def home():
    return "Bot is live 🎉"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)


















