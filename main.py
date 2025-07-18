from flask import Flask, request, jsonify, redirect
import os
import stripe
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters
from dotenv import load_dotenv

load_dotenv()

# ENV VARIABLES
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
STRIPE_PRICE_ID = os.getenv("STRIPE_PRICE_ID")
RENDER_URL = "https://spicy-telegram-bot-4.onrender.com"

# Set up bot
bot = Bot(token=BOT_TOKEN)
app = Flask(__name__)
stripe.api_key = STRIPE_SECRET_KEY

# In-memory user access (use database for production)
premium_users = set()

@app.route('/')
def index():
    return "Bot is running!"

@app.route('/webhook', methods=['POST'])
def webhook():
    payload = request.data
    sig_header = request.headers.get('stripe-signature')
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except Exception as e:
        print(f"Webhook error: {e}")
        return '', 400

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        user_id = session['client_reference_id']
        premium_users.add(int(user_id))
        bot.send_message(chat_id=user_id, text="✅ Payment received! You now have premium access.")
    return '', 200

@app.route('/pay')
def pay():
    user_id = request.args.get("user_id")
    if not user_id:
        return "Missing user_id", 400
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price': STRIPE_PRICE_ID,
                'quantity': 1,
            }],
            mode='payment',
            success_url=f"{RENDER_URL}/success",
            cancel_url=f"{RENDER_URL}/cancel",
            client_reference_id=user_id,
        )
        return redirect(session.url, code=303)
    except Exception as e:
        print(f"Stripe error: {e}")
        return str(e), 500

@app.route('/webhook_telegram', methods=['POST'])
def telegram_webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "ok"

def start(update, context):
    user_id = update.effective_chat.id
    context.bot.send_message(chat_id=user_id, text="🔥 Welcome to TheSpicyChatBot!\n\nTo chat with me, please unlock premium 😉")

def pay(update, context):
    user_id = update.effective_chat.id
    payment_link = f"{RENDER_URL}/pay?user_id={user_id}"
    context.bot.send_message(chat_id=user_id, text=f"💳 Unlock premium: {payment_link}")

def handle_message(update, context):
    user_id = update.effective_chat.id
    if user_id not in premium_users:
        context.bot.send_message(chat_id=user_id, text="🚫 This is a premium-only bot.\nUse /pay to unlock access.")
        return
    user_message = update.message.text
    context.bot.send_message(chat_id=user_id, text=f"🤖 AI reply to: {user_message}")

# Setup dispatcher
dispatcher = Dispatcher(bot, None, workers=0)
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("pay", pay))
dispatcher.add_handler(MessageHandler(Filters.text & (~Filters.command), handle_message))

# Set webhook on bot startup
@app.before_first_request
def set_webhook():
    webhook_url = f"{RENDER_URL}/webhook_telegram"
    bot.set_webhook(webhook_url)
    print(f"✅ Webhook set to {webhook_url}")

if __name__ == "__main__":
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))














