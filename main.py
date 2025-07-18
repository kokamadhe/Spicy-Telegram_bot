import os
from flask import Flask, request, jsonify, render_template_string
from dotenv import load_dotenv
import stripe
import requests
from pydub import AudioSegment
from pydub.playback import play
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters
from io import BytesIO

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL_LAB_API_KEY = os.getenv("MODEL_LAB_API_KEY")
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
STRIPE_PRICE_ID = os.getenv("STRIPE_PRICE_ID")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
RENDER_URL = "https://spicy-telegram-bot-5.onrender.com"

stripe.api_key = STRIPE_SECRET_KEY

app = Flask(__name__)
bot = Bot(token=TELEGRAM_TOKEN)
dispatcher = Dispatcher(bot, None, use_context=True)

# In-memory premium user storage (use DB in production)
premium_users = set()

# HTML template for pay page
PAY_TEMPLATE = """
<html><body style='text-align: center; font-family: sans-serif'>
<h2>Buy Premium Access</h2>
<form action='/create-checkout-session' method='POST'>
  <input type='hidden' name='user_id' value='{{ user_id }}'>
  <button type='submit' style='font-size: 18px;'>💳 Buy Premium</button>
</form>
</body></html>
"""

@app.route("/")
def home():
    return "TheSpicyBot is live! 🔥"

@app.route("/pay")
def pay():
    user_id = request.args.get("user_id")
    return render_template_string(PAY_TEMPLATE, user_id=user_id)

@app.route("/create-checkout-session", methods=["POST"])
def create_checkout_session():
    user_id = request.form["user_id"]
    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{"price": STRIPE_PRICE_ID, "quantity": 1}],
        mode="payment",
        success_url=f"{RENDER_URL}/success?user_id={user_id}",
        cancel_url=f"{RENDER_URL}/cancel",
        metadata={"user_id": user_id}
    )
    return jsonify({"url": session.url})

@app.route("/success")
def success():
    user_id = request.args.get("user_id")
    premium_users.add(int(user_id))
    bot.send_message(chat_id=user_id, text="✅ Premium unlocked! You can now chat with me 😘")
    return "Payment successful!"

@app.route("/cancel")
def cancel():
    return "Payment canceled."

@app.route("/stripe_webhook", methods=["POST"])
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
        premium_users.add(int(user_id))
        bot.send_message(chat_id=user_id, text="✅ Payment confirmed! Premium access activated.")
    return "", 200

def start(update, context):
    user_id = update.effective_user.id
    if user_id in premium_users:
        update.message.reply_text("You're already a premium user 😎")
    else:
        pay_url = f"{RENDER_URL}/pay?user_id={user_id}"
        keyboard = [[InlineKeyboardButton("💳 Buy Premium", url=pay_url)]]
        update.message.reply_text("🔥 Welcome to TheSpicyChatBot!\n\nTo chat with me, please unlock premium 😉",
                                  reply_markup=InlineKeyboardMarkup(keyboard))

def handle_message(update, context):
    user_id = update.effective_user.id
    text = update.message.text

    if user_id not in premium_users:
        update.message.reply_text("🔒 This feature is for premium users only. Use /start to upgrade.")
        return

    if text.startswith("/image"):
        prompt = text.replace("/image", "").strip()
        image_url = generate_image(prompt)
        update.message.reply_photo(photo=image_url)
    else:
        reply = generate_text_reply(text)
        update.message.reply_text(reply)
        send_voice_reply(user_id, reply)

def generate_text_reply(prompt):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "HTTP-Referer": "https://chat.openai.com",
    }
    data = {
        "model": "nous-hermes2",
        "messages": [
            {"role": "system", "content": "You're a spicy, flirty chatbot."},
            {"role": "user", "content": prompt}
        ]
    }
    response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data)
    return response.json()["choices"][0]["message"]["content"]

def generate_image(prompt):
    headers = {"Authorization": f"Bearer {MODEL_LAB_API_KEY}"}
    payload = {"prompt": prompt, "model": "realistic-vision-v5"}
    response = requests.post("https://api.modellab.ai/v1/image/generate", json=payload, headers=headers)
    return response.json()["data"][0]["url"]

def send_voice_reply(user_id, text):
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json"
    }
    json = {
        "text": text,
        "voice_settings": {"stability": 0.4, "similarity_boost": 0.6},
        "model_id": "eleven_monolingual_v1"
    }
    response = requests.post("https://api.elevenlabs.io/v1/text-to-speech/Rachel/stream", headers=headers, json=json)

    audio = BytesIO(response.content)
    bot.send_voice(chat_id=user_id, voice=audio)

dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def telegram_webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "ok"

if __name__ == "__main__":
    app.run(debug=True)



















