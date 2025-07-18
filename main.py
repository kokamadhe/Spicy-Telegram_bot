from flask import Flask, request
import requests
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
MODEL_API_KEY = os.getenv("MODEL_API_KEY")  # OpenRouter for text
MODEL_LAB_API_KEY = os.getenv("MODEL_LAB_API_KEY")  # ModelLab for image

# Send text message
def send_message(chat_id, text):
    requests.post(f"{TELEGRAM_API_URL}/sendMessage", json={
        "chat_id": chat_id,
        "text": text
    })

# Send image
def send_image(chat_id, image_url):
    requests.post(f"{TELEGRAM_API_URL}/sendPhoto", json={
        "chat_id": chat_id,
        "photo": image_url
    })

# Generate image with ModelLab / Stable Diffusion API
def generate_image(prompt):
    headers = {
        "Authorization": f"Bearer {MODEL_LAB_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "prompt": prompt,
        "model": "realistic-vision",  # or try "dreamshaper", "deliberate", etc.
        "n": 1,
        "size": "512x768",
        "quality": "standard"
    }
    response = requests.post("https://api.modellab.space/v1/text2image", json=payload, headers=headers)
    if response.ok:
        data = response.json()
        return data["data"][0]["url"]
    else:
        print(response.text)
        return None

@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
    data = request.get_json()

    if "message" in data:
        message = data["message"]
        chat_id = message["chat"]["id"]
        text = message.get("text", "")

        if text.startswith("/image"):
            prompt = text.replace("/image", "").strip()
            if prompt:
                send_message(chat_id, "🖼️ Generating image...")
                image_url = generate_image(prompt)
                if image_url:
                    send_image(chat_id, image_url)
                else:
                    send_message(chat_id, "❌ Failed to generate image.")
            else:
                send_message(chat_id, "❗ Please provide a prompt after /image")
        else:
            # Text generation via OpenRouter (your existing text logic)
            headers = {
                "Authorization": f"Bearer {MODEL_API_KEY}",
                "Content-Type": "application/json"
            }
            body = {
                "model": "gryphe/mythomist-7b",
                "messages": [{"role": "user", "content": text}]
            }
            response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=body)
            if response.ok:
                reply = response.json()["choices"][0]["message"]["content"]
                send_message(chat_id, reply)
            else:
                send_message(chat_id, "❌ Error generating reply.")

    return {"ok": True}



