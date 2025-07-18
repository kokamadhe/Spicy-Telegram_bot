from flask import Flask, request, jsonify, redirect
import requests
import os
import stripe
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# ENV VARS
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
STRIPE_API_KEY = os.environ.get("STRIPE_API_KEY")
DOMAIN = os.environ.get("DOMAIN", "https://your-app-name.onrender.com")  # Update this to your actual domain
PREMIUM_PRICE_ID = os.environ.get("PREMIUM_PRICE_ID")  # Your Stripe price ID

stripe.api_key = STRIPE_API_KEY

# Store premium users (in-memory, replace with DB for persistence)
premium_users = set()

@app.route('/')
def home():
    return '✅ Spicy ChatBot is live!'

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "")

        if text == "/start":
            send_message(chat_id, "🔥 Welcome to TheSpicyChatBot!\n\nTo chat with me, please [unlock premium](https://your-app-name.onrender.com/pay?user_id={}) 😉".format(chat_id))
        elif text == "/pay":
            send_message(chat_id, "💳 Click here to unlock premium access:\n" + f"{DOMAIN}/pay?user_id={chat_id}")
        elif chat_id in premium_users:
            ai_reply = generate_ai_reply(text)
            send_message(chat_id, ai_reply)
        else:
            send_message(chat_id, "🔒 This is a premium-only bot.\nUse /pay to unlock access.")

    return jsonify({"ok": True})

@app.route('/pay')
def create_checkout():
    user_id = request.args.get("user_id")
    if not user_id:
        return "Missing user_id", 400

    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                'price': PREMIUM_PRICE_ID,
                'quantity': 1,
            }],
            mode='payment',  # change to 'subscription' for recurring
            success_url=f"{DOMAIN}/success?user_id={user_id}",
            cancel_url=f"{DOMAIN}/cancel",
            metadata={'user_id': user_id}
        )
        return redirect(checkout_session.url, code=303)
    except Exception as e:
        return f"Stripe error: {str(e)}", 400

@app.route('/success')
def payment_success():
    user_id = request.args.get("user_id")
    if user_id:
        premium_users.add(int(user_id))
        send_message(user_id, "🎉 Thank you for subscribing! You now have premium access.")
        return "✅ Premium access granted!"
    return "Missing user_id", 400

@app.route('/cancel')
def payment_cancel():
    return "❌ Payment canceled. You can try again via /pay"

def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    requests.post(url, json=payload)

def generate_ai_reply(user_message):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "nousresearch/nous-hermes-2-mixtral-8x7b-dpo",
        "messages": [
            {"role": "system", "content": "You are a spicy, seductive NSFW chatbot."},
            {"role": "user", "content": user_message}
        ]
    }
    response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data)
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        return "❌ Error from AI model."

if __name__ == '__main__':
    app.run(debug=True)











