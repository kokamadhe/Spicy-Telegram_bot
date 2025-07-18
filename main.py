import os
import requests
from flask import Flask, request
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL_LAB_API_KEY = os.getenv("MODEL_LAB_API_KEY")

app = Flask(__name__)

# Telegram API URL
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

# OpenRouter Chat Endpoint
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

@app.route("/")
def home():
    return "Aria Blaze is live! 🔥"

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()

    if "message" not in data:
        return "No message", 200

    chat_id = data["message"]["chat"]["id"]
    user_message = data["message"].get("text", "")

    if user_message.startswith("/image"):
        prompt = user_message.replace("/image", "").strip()
        if not prompt:
            prompt = "a beautiful fantasy woman in futuristic city"
        image_url = generate_image(prompt)
        if image_url:
            send_photo(chat_id, image_url)
        else:
            send_message(chat_id, "❌ Failed to generate image.")
    else:
        reply = generate_reply(user_message)
        if reply:
            send_message(chat_id, reply)
        else:
            send_message(chat_id, "❌ Text generation failed.")
    
    return "OK", 200

def generate_reply(user_input):
    try:
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://ariablazebot.com",  # Can be any valid domain
            "X-Title": "AriaBlazeBot"
        }

        payload = {
            "model": "nous-hermes2",
            "messages": [
                {"role": "system", "content": "You are Aria Blaze, an uncensored and flirty NSFW AI girl."},
                {"role": "user", "content": user_input}
            ]
        }

        response = requests.post(OPENROUTER_URL, headers=headers, json=payload)
        response.raise_for_status()

        data = response.json()
        return data["choices"][0]["message"]["content"].strip()

    except Exception as e:
        print("❌ Text generation error:", e)
        return None

def generate_image(prompt):
    try:
        payload = {
            "key": MODEL_LAB_API_KEY,
            "prompt": prompt,
            "negative_prompt": "blurry, bad quality, censored",
            "width": "512",
            "height": "512",
            "samples": "1",
            "num_inference_steps": "30",
            "guidance_scale": 7.5,
            "model_id": "realistic-vision-v51",
            "safety_checker": "no",
            "webhook": None,
            "track_id": None
        }

        response = requests.post("https://stablediffusionapi.com/api/v3/text2img", json=payload)
        response.raise_for_status()

        data = response.json()
        return data["output"][0] if "output" in data else None

    except Exception as e:
        print("❌ Image generation error:", e)
        return None

def send_message(chat_id, text):
    payload = {
        "chat_id": chat_id,
        "text": text
    }
    requests.post(f"{TELEGRAM_API_URL}/sendMessage", json=payload)

def send_photo(chat_id, photo_url):
    payload = {
        "chat_id": chat_id,
        "photo": photo_url
    }
    requests.post(f"{TELEGRAM_API_URL}/sendPhoto", json=payload)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)




