import os
from flask import Flask, request, jsonify, redirect
import telegram
from telegram import Update
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters
import stripe
from dotenv import load_dotenv
from threading import Thread

load_dotenv()

# Load environment variables
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL_LAB_API_KEY = os.getenv("MODEL_LAB_API_KEY")
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
STRIPE_PRICE_ID = os.getenv("STRIPE_PRICE_ID")

# Define premium user storage
premium_users = set()

# Setup Flask
app = Flask(__name__)

# Setup Telegram bot
bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)

# Setup Stripe
stripe.api_key = STRIPE_SECRET_KEY


@app.route('/')
def home():
    return '🔥 Spicy Telegram Bot is live!'


@app.route('/pay')
def pay():
    user_id = request.args.get('user_id')
    if not user_id:
        return "Missing user_id", 400

    # Create Stripe checkout session
    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{
            'price': STRIPE_PRICE_ID,
            'quantity': 1,
        }],
        mode='payment',
        success_url=f"https://t.me/{bot.get_me().username}",
        cancel_url=f"https://t.me/{bot.get_me().username}",
        metadata={'user_id': user_id}
    )
    return redirect(session.url, code=303)


@app.route('/webhook', methods=['POST'])
def stripe_webhook():
    payload = request.data
    sig_header = request.headers.get('stripe-signature')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except stripe.error.SignatureVerificationError:
        return jsonify({'error': 'Invalid signature'}), 400

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        user_id = session['metadata']['user_id']
        premium_users.add(int(user_id))
        bot.send_message(chat_id=int(user_id), text="✅ Payment received! You now have premium access.")
    return jsonify({'status': 'success'})


def start(update: Update, context):
    user_id = update.effective_user.id
    if user_id in premium_users:
        context.bot.send_message(chat_id=user_id, text="Welcome back, premium user! 🔥")
    else:
        context.bot.send_message(chat_id=user_id, text="🔥 Welcome to TheSpicyChatBot!\n\nTo chat with me, please unlock premium 😉")


def pay_command(update: Update, context):
    user_id = update.effective_user.id
    pay_url = f"https://spicy-telegram-bot-4.onrender.com/pay?user_id={user_id}"
    context.bot.send_message(chat_id=user_id, text=f"💳 Click to unlock premium: {pay_url}")


def message_handler(update: Update, context):
    user_id = update.effective_user.id
    if user_id in premium_users:
        context.bot.send_message(chat_id=user_id, text="🔥 You're premium! I'm ready to chat.")
    else:
        context.bot.send_message(chat_id=user_id, text="🚫 This is a premium-only bot.\nUse /pay to unlock access.")


def run_bot():
    from telegram.ext import Updater
    updater = Updater(token=TELEGRAM_BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("pay", pay_command))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, message_handler))

    updater.start_polling()
    updater.idle()


# Run Flask and Telegram bot in parallel
if __name__ == '__main__':
    Thread(target=run_bot).start()
    app.run(host="0.0.0.0", port=10000)













