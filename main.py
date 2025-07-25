import os
import requests
import sqlite3
import uuid
from flask import Flask, request, jsonify
from firebase_admin import credentials, firestore, initialize_app
from dotenv import load_dotenv
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters

# --- Load ENV ---
load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")
NOWPAYMENTS_API = os.getenv("NOWPAYMENTS_API_KEY")

# --- Firebase ---
cred = credentials.Certificate("firebase-adminsdk.json")
initialize_app(cred)
db = firestore.client()
users_ref = db.collection("users")

# --- SQLite (for fallback) ---
conn = sqlite3.connect('users.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    verified INTEGER DEFAULT 0,
    premium INTEGER DEFAULT 0
)''')
conn.commit()

# --- Flask Setup ---
app = Flask(__name__)
bot = Bot(token=BOT_TOKEN)
dispatcher = Dispatcher(bot, None, workers=0, use_context=True)

# --- Helper Functions ---
def is_verified(user_id):
    user = users_ref.document(str(user_id)).get()
    if user.exists:
        return user.to_dict().get("verified", False)
    cursor.execute("SELECT verified FROM users WHERE user_id = ?", (str(user_id),))
    result = cursor.fetchone()
    return result and result[0] == 1

def is_premium(user_id):
    user = users_ref.document(str(user_id)).get()
    if user.exists:
        return user.to_dict().get("premium", False)
    cursor.execute("SELECT premium FROM users WHERE user_id = ?", (str(user_id),))
    result = cursor.fetchone()
    return result and result[0] == 1

def set_verified(user_id):
    users_ref.document(str(user_id)).set({"verified": True}, merge=True)
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (str(user_id),))
    cursor.execute("UPDATE users SET verified = 1 WHERE user_id = ?", (str(user_id),))
    conn.commit()

def set_premium(user_id):
    users_ref.document(str(user_id)).set({"premium": True}, merge=True)
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (str(user_id),))
    cursor.execute("UPDATE users SET premium = 1 WHERE user_id = ?", (str(user_id),))
    conn.commit()

# --- Handlers ---
def start(update, context):
    update.message.reply_text("Welcome to Aria Blaze 💋 Use /verify, /pay, /status, or /image <prompt>")

def verify(update, context):
    user_id = update.effective_user.id
    token = str(uuid.uuid4())
    context.user_data["verify_token"] = token
    link = f"https://yourdomain.com/verify/{user_id}?token={token}"
    update.message.reply_text(f"🔐 Click to verify: {link}")

def status(update, context):
    user_id = update.effective_user.id
    v = is_verified(user_id)
    p = is_premium(user_id)
    update.message.reply_text(f"👤 Verified: {v}\n💎 Premium: {p}")

def pay(update, context):
    user_id = update.effective_user.id
    payload = {
        "price_amount": 5,
        "price_currency": "usd",
        "pay_currency": "trx",
        "order_id": str(user_id),
        "ipn_callback_url": "https://yourdomain.com/ipn",
        "success_url": "https://t.me/your_bot_username",
        "cancel_url": "https://t.me/your_bot_username"
    }
    headers = {"x-api-key": NOWPAYMENTS_API, "Content-Type": "application/json"}
    r = requests.post("https://api.nowpayments.io/v1/invoice", json=payload, headers=headers)
    if r.status_code == 200:
        link = r.json()["invoice_url"]
        update.message.reply_text(f"💰 Click to pay and unlock premium: {link}")
    else:
        update.message.reply_text("❌ Payment error. Try again later.")

def image(update, context):
    user_id = update.effective_user.id
    if not (is_verified(user_id) and is_premium(user_id)):
        update.message.reply_text("🔒 Only verified & premium users can generate images.")
        return
    prompt = " ".join(context.args)
    if not prompt:
        update.message.reply_text("Please provide a prompt. Example: /image a sexy anime girl in bed")
        return
    headers = {
        "Authorization": f"Bearer {OPENROUTER_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "stability-ai/sdxl",
        "prompt": prompt
    }
    r = requests.post("https://openrouter.ai/api/v1/generate-image", json=data, headers=headers)
    if r.status_code == 200:
        img_url = r.json().get("image_url")
        if img_url:
            update.message.reply_photo(img_url)
        else:
            update.message.reply_text("⚠️ No image returned.")
    else:
        update.message.reply_text("⚠️ Error generating image.")

def ai_reply(update, context):
    user_id = update.effective_user.id
    if not (is_verified(user_id) and is_premium(user_id)):
        return
    prompt = update.message.text
    headers = {
        "Authorization": f"Bearer {OPENROUTER_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "nousresearch/nous-hermes2",
        "messages": [{"role": "user", "content": prompt}]
    }
    r = requests.post("https://openrouter.ai/api/v1/chat/completions", json=data, headers=headers)
    if r.status_code == 200:
        reply = r.json()['choices'][0]['message']['content']
        update.message.reply_text(reply)
    else:
        update.message.reply_text("⚠️ Error generating reply.")

# --- Dispatcher ---
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("verify", verify))
dispatcher.add_handler(CommandHandler("status", status))
dispatcher.add_handler(CommandHandler("pay", pay))
dispatcher.add_handler(CommandHandler("image", image))
dispatcher.add_handler(MessageHandler(Filters.text & (~Filters.command), ai_reply))

# --- Flask Routes ---
@app.route('/webhook', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "ok"

@app.route('/verify/<user_id>', methods=["GET"])
def web_verify(user_id):
    set_verified(user_id)
    return f"<h2>✅ User {user_id} verified! Return to Telegram.</h2>"

@app.route("/ipn", methods=["POST"])
def ipn():
    data = request.json
    if data.get("payment_status") == "finished":
        user_id = data.get("order_id")
        set_premium(user_id)
        return "OK", 200
    return "Ignored", 200

# --- Run ---
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))























