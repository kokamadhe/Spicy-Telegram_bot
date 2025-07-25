import os
import sqlite3
import requests
from flask import Flask, request
from dotenv import load_dotenv
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters
import logging
import json

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL_LAB_API_KEY = os.getenv("MODEL_LAB_API_KEY")
NOWPAYMENTS_API_KEY = os.getenv("NOWPAYMENTS_API_KEY")
YOUR_CRYPTO_WALLET = os.getenv("YOUR_CRYPTO_WALLET")

app = Flask(__name__)
bot = Bot(token=TOKEN)

# Enable logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# SQLite setup
conn = sqlite3.connect('users.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, is_premium INTEGER DEFAULT 0, memory TEXT)''')
conn.commit()

# --- Utility functions ---
def is_premium(user_id):
    cursor.execute("SELECT is_premium FROM users WHERE user_id=?", (user_id,))
    result = cursor.fetchone()
    return result and result[0] == 1

def set_premium(user_id):
    cursor.execute("INSERT OR REPLACE INTO users (user_id, is_premium) VALUES (?, 1)", (user_id,))
    conn.commit()

def set_memory(user_id, text):
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    cursor.execute("UPDATE users SET memory=? WHERE user_id=?", (text, user_id))
    conn.commit()

def get_memory(user_id):
    cursor.execute("SELECT memory FROM users WHERE user_id=?", (user_id,))
    result = cursor.fetchone()
    return result[0] if result else ""

# --- Telegram handlers ---
def start(update, context):
    update.message.reply_text("Benvenuto! Usa /verify per diventare premium oppure /pay per pagare.")

def verify(update, context):
    user_id = update.message.from_user.id
    if is_premium(user_id):
        update.message.reply_text("✅ Sei già verificato come utente premium.")
    else:
        update.message.reply_text("🔐 Per diventare premium usa il comando /pay e segui le istruzioni.")

def status(update, context):
    user_id = update.message.from_user.id
    if is_premium(user_id):
        update.message.reply_text("✅ Status: Utente PREMIUM")
    else:
        update.message.reply_text("❌ Status: Non premium")

def pay(update, context):
    url = "https://api.nowpayments.io/v1/invoice"
    headers = {
        "x-api-key": NOWPAYMENTS_API_KEY,
        "Content-Type": "application/json"
    }
    data = {
        "price_amount": 5,
        "price_currency": "usd",
        "pay_currency": "trx",
        "order_description": "Accesso Premium Bot",
        "ipn_callback_url": "https://yourdomain.com/ipn",  # Opzionale
        "success_url": "https://t.me/your_bot",
        "cancel_url": "https://t.me/your_bot",
        "payout_address": YOUR_CRYPTO_WALLET
    }

    response = requests.post(url, headers=headers, json=data)
    result = response.json()

    if "invoice_url" in result:
        update.message.reply_text(f"💳 Paga qui per diventare premium:\n{result['invoice_url']}")
    else:
        update.message.reply_text("❌ Errore nella creazione del pagamento.")

def image(update, context):
    user_id = update.message.from_user.id
    prompt = ' '.join(context.args)
    if not is_premium(user_id):
        return update.message.reply_text("🔒 Solo utenti premium possono generare immagini.")
    if not prompt:
        return update.message.reply_text("❗ Scrivi il prompt dopo /image")

    headers = {
        "Authorization": f"Bearer {MODEL_LAB_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "realistic-vision",
        "prompt": prompt,
        "n": 1
    }

    response = requests.post("https://api.modellab.ai/v1/images/generate", headers=headers, json=data)
    result = response.json()
    if 'data' in result and result['data']:
        img_url = result['data'][0]['url']
        update.message.reply_photo(img_url)
    else:
        update.message.reply_text("❌ Errore nella generazione dell'immagine.")

def chat(update, context):
    user_id = update.message.from_user.id
    user_message = update.message.text

    if not is_premium(user_id):
        return update.message.reply_text("🔒 Solo utenti premium possono usare questa funzione.")

    memory = get_memory(user_id)
    payload = {
        "model": "nous-hermes2",
        "messages": [
            {"role": "system", "content": "Sei una ragazza sexy e senza limiti."},
            {"role": "user", "content": memory + "\n" + user_message}
        ]
    }

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
    data = response.json()
    reply = data['choices'][0]['message']['content']
    update.message.reply_text(reply)
    set_memory(user_id, user_message)

# --- Flask Webhook ---
@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "ok"

@app.route('/')
def home():
    return "Bot is running!"

# Setup dispatcher
dispatcher = Dispatcher(bot, None, use_context=True)
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("verify", verify))
dispatcher.add_handler(CommandHandler("status", status))
dispatcher.add_handler(CommandHandler("pay", pay))
dispatcher.add_handler(CommandHandler("image", image))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, chat))

# --- Start (if using polling, for local debug) ---
if __name__ == "__main__":
    app.run()


























