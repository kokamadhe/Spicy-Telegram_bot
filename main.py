import os
from flask import Flask, request, jsonify, redirect
import stripe
import requests
from dotenv import load_dotenv

load_dotenv()

# Load environment variables
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
STRIPE_PRICE_ID = os.getenv("STRIPE_PRICE_ID")

# Updated Render service URL
YOUR_RENDER_URL = "https://spicy-telegram-bot-5.onrender.com"
BOT_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

# In-memory storage for user access (for production, use a database!)
premium_users = set()

# Setup Stripe API key
stripe.api_key = STRIPE_SECRET_KEY

app = Flask(__name__)

def query_openrouter(prompt: str) -> str:
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    json_data = {
        "model": "nous-hermes-2",  # or another model you prefer
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }
    response = requests.post(url, headers=headers, json=json_data)
    if response.ok:
        data = response.json()
        # Extract the AI message
        return data["choices"][0]["message"]["content"]
    else:
        print("OpenRouter API error:", response.text)
        return "Sorry, I couldn't process that."

@app.route('/')
def home():
    return "🔥 Spicy Bot is live!"

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "")

        if chat_id not in premium_users and text not in ["/start", "/pay"]:
            send_message(chat_id, "🚫 This is a premium-only bot.\nUse /pay to unlock access.")
            return jsonify(ok=True)

        if text == "/start":
            send_message(chat_id, "🔥 Welcome to TheSpicyChatBot!\n\nTo chat with me, please unlock premium 😉")
        elif text == "/pay":
            payment_link = f"{YOUR_RENDER_URL}/pay?user_id={chat_id}"
            send_message(chat_id, f"💳 Click below to purchase premium:\n{payment_link}")
        elif chat_id in premium_users:
            ai_response = query_openrouter(text)
            send_message(chat_id, ai_response)

    return jsonify(ok=True)

@app.route('/pay')
def pay():
    user_id = request.args.get("user_id")
    if not user_id:
        return "Missing user_id", 400

    checkout = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{
            "price": STRIPE_PRICE_ID,
            "quantity": 1
        }],
        mode="subscription",
        success_url=f"{YOUR_RENDER_URL}/success?user_id={user_id}",
        cancel_url=f"{YOUR_RENDER_URL}/cancel",
        metadata={"user_id": user_id}  # Important for webhook tracking
    )
    return redirect(checkout.url, code=303)

@app.route('/success')
def success():
    user_id = request.args.get("user_id")
    if user_id:
        premium_users.add(int(user_id))
        send_message(user_id, "✅ Thank you for your payment!\nYou now have premium access.")
    return "Payment successful!"

@app.route('/cancel')
def cancel():
    return "Payment cancelled."

@app.route('/stripe-webhook', methods=['POST'])
def stripe_webhook():
    payload = request.data
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except stripe.error.SignatureVerificationError:
        return "Invalid signature", 400

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        metadata = session.get("metadata", {})
        user_id = metadata.get("user_id")
        if user_id:
            premium_users.add(int(user_id))
            send_message(user_id, "✅ Payment confirmed! You now have full access.")
    return "Webhook received", 200

def send_message(chat_id, text):
    resp = requests.post(f"{BOT_API_URL}/sendMessage", json={
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    })
    if not resp.ok:
        print(f"Failed to send message: {resp.status_code} - {resp.text}")

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

















