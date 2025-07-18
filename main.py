from flask import Flask, request, jsonify, render_template_string, redirect
import os
import stripe
import telegram

# Your credentials
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_PRICE_ID = os.getenv("STRIPE_PRICE_ID")  # Your actual Stripe price ID
BOT = telegram.Bot(token=TELEGRAM_BOT_TOKEN)

# Your app and Stripe config
app = Flask(__name__)
stripe.api_key = STRIPE_SECRET_KEY

# Store who paid
premium_users = set()

@app.route("/", methods=["GET"])
def home():
    return "Bot is alive!"

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()

    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "")

        if chat_id not in premium_users:
            if text == "/start":
                BOT.send_message(chat_id=chat_id, text="🔥 Welcome to TheSpicyChatBot!\n\nTo chat with me, please unlock premium 😉")
            elif text == "/pay":
                payment_link = f"https://spicy-telegram-bot-4.onrender.com/pay?user_id={chat_id}"
                BOT.send_message(chat_id=chat_id, text=f"Unlock premium access here 👇\n{payment_link}")
            else:
                BOT.send_message(chat_id=chat_id, text="❌ This is a premium-only bot.\nUse /pay to unlock access.")
        else:
            # Premium reply (replace this with actual chat logic)
            BOT.send_message(chat_id=chat_id, text=f"✅ You’re premium! Ask me anything 🔥")

    return jsonify(success=True)

@app.route("/pay", methods=["GET"])
def pay():
    user_id = request.args.get("user_id")
    if not user_id:
        return "User ID missing", 400

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{
            "price": STRIPE_PRICE_ID,
            "quantity": 1,
        }],
        mode="payment",
        success_url=f"https://spicy-telegram-bot-4.onrender.com/success?user_id={user_id}",
        cancel_url="https://t.me/your_bot_username",  # Replace with your bot link
        metadata={"user_id": user_id}
    )

    return redirect(session.url, code=303)

@app.route("/success", methods=["GET"])
def success():
    user_id = request.args.get("user_id")
    if user_id:
        premium_users.add(int(user_id))
        try:
            BOT.send_message(chat_id=int(user_id), text="🎉 Thanks for your payment! You now have premium access.")
        except Exception as e:
            print(f"Failed to message user: {e}")
    return "Payment successful. You can now return to Telegram."

# Stripe webhook endpoint (optional for auto-validation)
@app.route("/stripe-webhook", methods=["POST"])
def stripe_webhook():
    payload = request.data
    sig_header = request.headers.get("Stripe-Signature")
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
    except Exception as e:
        return f"Webhook error: {str(e)}", 400

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        user_id = session.get("metadata", {}).get("user_id")
        if user_id:
            premium_users.add(int(user_id))
            try:
                BOT.send_message(chat_id=int(user_id), text="🎉 Thanks for your payment! You now have premium access.")
            except Exception as e:
                print(f"Error sending message: {e}")

    return "", 200

if __name__ == "__main__":
    app.run(debug=True)












