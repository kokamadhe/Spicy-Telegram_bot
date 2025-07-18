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

# --- TEXT GENERATION HANDLER ---
def generate_text(prompt):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "gryphe/mythomist-7b",
        "messages": [{"role": "user", "content": prompt}]
    }

    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"❌ Text generation failed: {e}"

# --- IMAGE GENERATION HANDLER ---
def generate_image(prompt):
    url = "https://api.stablediffusionapi.com/v4/dreambooth"
    headers = {"Content-Type": "application/json"}
    payload = {
        "key": MODEL_LAB_API_KEY,
        "model_id": "realistic-vision-v51",
        "prompt": prompt,
        "negative_prompt": "blurry, bad anatomy, distorted",
        "width": "512",
        "height": "768",
        "samples": "1",
        "guidance_scale": 7.5
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        return data["output"][0] if "output" in data else None
    except Exception as e:
        return None

# --- TELEGRAM WEBHOOK HANDLER ---
@app.route("/", methods=["POST"])
def webhook():
    data = request.get_json()

    if "message" in data and "text" in data["message"]:
        chat_id = data["message"]["chat"]["id"]
        message_text = data["message"]["text"]

        if message_text.startswith("/image"):
            prompt = message_text.replace("/image", "").strip()
            image_url = generate_image(prompt)
            if image_url:
                send_photo(chat_id, image_url)
            else:
                send_message(chat_id, "❌ Failed to generate image.")
        else:
            reply = generate_text(message_text)
            send_message(chat_id, reply)

    return {"ok": True}

# --- UTILITIES ---
def send_message(chat_id, text):
    url = f"{TELEGRAM_API_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    requests.post(url, json=payload)

def send_photo(chat_id, photo_url):
    url = f"{TELEGRAM_API_URL}/sendPhoto"
    payload = {"chat_id": chat_id, "photo": photo_url}
    requests.post(url, json=payload)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)



