import os
import requests
from flask import Flask, request
from dotenv import load_dotenv
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler

load_dotenv()

app = Flask(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
NOWPAYMENTS_API_KEY = os.getenv("NOWPAYMENTS_API_KEY")

bot = Bot(token=TOKEN)

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dp.process_update(update)
    return "ok"

def start(update, context):
    update.message.reply_text("Welcome! Type /pay to unlock premium features via crypto.")

def pay(update, context):
    chat_id = update.message.chat_id
    payment = create_nowpayments_invoice(chat_id)
    if payment:
        update.message.reply_text(f"💰 Click to Pay:\n{payment}")
    else:
        update.message.reply_text("❌ Failed to create payment. Try again later.")

def create_nowpayments_invoice(user_id):
    url = "https://api.nowpayments.io/v1/invoice"
    headers = {
        "x-api-key": NOWPAYMENTS_API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "price_amount": 5.00,
        "price_currency": "USD",
        "order_id": str(user_id),
        "order_description": "Premium access for Aria Blaze",
        "success_url": "https://t.me/YourBotUsername",  # <- update this
        "cancel_url": "https://t.me/YourBotUsername",
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        data = response.json()
        return data.get("invoice_url")
    except Exception as e:
        print("NOWPayments error:", e)
        return None

# Dispatcher
dp = Dispatcher(bot, None, workers=0)
dp.add_handler(CommandHandler("start", start))
dp.add_handler(CommandHandler("pay", pay))

@app.route("/")
def index():
    return "Bot running"
























