import os
import requests
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import Dispatcher, MessageHandler, Filters, CallbackContext
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
bot = Bot(token=TELEGRAM_TOKEN)
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL = "nousresearch/nous-hermes-2-mixtral-8x7b-dpo"

# Initialize dispatcher
dispatcher = Dispatcher(bot, None, use_context=True)

def get_openrouter_reply(message):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "You are Aria Blaze, an intelligent, seductive AI girlfriend who chats with users in NSFW, flirty, or emotional style."},
            {"role": "user", "content": message}
        ]
    }
    response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        return "⚠️ OpenRouter API error."

def generate_image(prompt):
    url = "https://api.stability.ai/v2beta/stable-image/generate/core"
    stability_key = os.getenv("STABILITY_API_KEY")
    headers = {
        "Authorization": f"Bearer {stability_key}",
        "Content-Type": "application/json"
    }
    data = {
        "prompt": prompt,
        "output_format": "png",
    }
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        image_bytes = requests.get(response.json()["image"]).content
        return image_bytes
    else:
        return None

def handle_message(update: Update, context: CallbackContext):
    user_message = update.message.text

    if user_message.startswith("/image"):
        prompt = user_message.replace("/image", "").strip()
        if prompt:
            image = generate_image(prompt)
            if image:
                update.message.reply_photo(photo=image, caption="Here is your image ❤️")
            else:
                update.message.reply_text("❌ Failed to generate image.")
        else:
            update.message.reply_text("🖼️ Please include a prompt after /image.")
    else:
        reply = get_openrouter_reply(user_message)
        update.message.reply_text(reply)

# Add handler
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
dispatcher.add_handler(MessageHandler(Filters.command, handle_message))  # for /image

@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def telegram_webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "OK", 200

@app.route("/", methods=["GET"])
def home():
    return "Aria Blaze AI bot is running!", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
























