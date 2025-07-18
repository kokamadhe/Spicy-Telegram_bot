from flask import Flask, request
import requests
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL_LAB_API_KEY = os.getenv("MODEL_LAB_API_KEY")

TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

# --- Telegram Message Sender ---
def send_telegram_message(chat_id, text):
    url = f"{TELEGRAM_API_URL}/sendMessage"
    data = {"chat_id": chat_id, "text": text}
    requests.post(url, json=data)

def send_telegram_photo(chat_id, photo_url, caption=None):
    url = f"{TELEGRAM_API_URL}/sendPhoto"
    data = {"chat_id": chat_id, "photo": photo_url}
    if caption:
        data["caption"] = caption
    requests.post(url, data=data)

# --- Text Generation via OpenRouter ---
def generate_reply(message):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    body = {
        "model": "nous-hermes2",
        "messages": [
            {"role": "system", "content": "You are an uncensored, flirty, NSFW AI girlfriend."},
            {"role": "user", "content": message}
        ]
    }

    response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=body)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]

# --- NSFW Image Generation ---
def generate_image(prompt):
    url = "https://api.modellab.com/v1/stable-diffusion"  # or your chosen NSFW image API
    headers = {
        "Authorization": f"Bearer {MODEL_LAB_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "prompt": prompt,
        "model": "realisticVision",  # use a NSFW-capable model
        "output_format": "url"
    }

    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    return response.json()["output"][0]  # URL of generated image

# --- Telegram Webhook Handler ---
def handle_telegram_update(update):
    if "message" not in update:
        return

    message = update["message"]
    chat_id = message["chat"]["id"]
    text = message.get("text", "")

    try:
        if text.startswith("/image"):
            prompt = text.replace("/image", "").strip()
            if not prompt:
                send_telegram_message(chat_id, "❗ Please provide a prompt after /image.")
                return
            send_telegram_message(chat_id, "🎨 Generating image...")
            image_url = generate_image(prompt)
            send_telegram_photo(chat_id, image_url, caption=f"🖼️ Prompt: {prompt}")
        else:
            send_telegram_message(chat_id, "💬 Thinking...")
            reply = generate_reply(text)
            send_telegram_message(chat_id, reply)

    except Exception as e:
        send_telegram_message(chat_id, f"❌ Error: {str(e)}")

# --- Flask Routes ---
@app.route("/", methods=["GET"])
def home():
    return "Bot is running", 200

@app.route("/", methods=["POST"])
def webhook():
    update = request.get_json()
    handle_telegram_update(update)
    return "", 200

# --- Gunicorn entrypoint ---
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)






