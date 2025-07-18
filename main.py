from flask import Flask, request
import requests
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
STABILITY_API_KEY = os.getenv("STABILITY_API_KEY")

TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

# === ROUTE ===
@app.route("/", methods=["POST"])
def webhook():
    data = request.json
    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        if "text" in data["message"]:
            message_text = data["message"]["text"]

            if message_text.startswith("/start"):
                send_message(chat_id, "👋 Hello! I'm your spicy AI. Send me any message or try /image followed by a prompt.")
            elif message_text.startswith("/image"):
                prompt = message_text.replace("/image", "").strip()
                if not prompt:
                    send_message(chat_id, "🖼️ Please provide a prompt. Example: `/image a sexy elf warrior`")
                else:
                    image_url = generate_image(prompt)
                    if image_url:
                        send_photo(chat_id, image_url)
                    else:
                        send_message(chat_id, "⚠️ Failed to generate image.")
            else:
                reply = generate_reply(message_text)
                send_message(chat_id, reply)
    return {"ok": True}


# === TEXT GENERATION ===
def generate_reply(message):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "nous-hermes2",
        "messages": [
            {"role": "system", "content": "You are a spicy, uncensored, flirty girlfriend chatbot."},
            {"role": "user", "content": message}
        ]
    }

    response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)

    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        return "❌ Error: Couldn't fetch reply from AI."


# === IMAGE GENERATION ===
def generate_image(prompt):
    stability_endpoint = "https://api.stability.ai/v1/generation/stable-diffusion-v1-5/text-to-image"
    headers = {
        "Authorization": f"Bearer {STABILITY_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    payload = {
        "cfg_scale": 10,
        "height": 512,
        "width": 512,
        "samples": 1,
        "steps": 30,
        "text_prompts": [{"text": prompt}]
    }

    response = requests.post(stability_endpoint, headers=headers, json=payload)

    if response.status_code == 200:
        return response.json()["artifacts"][0]["url"]
    else:
        return None


# === TELEGRAM HELPERS ===
def send_message(chat_id, text):
    url = f"{TELEGRAM_API_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    requests.post(url, json=payload)


def send_photo(chat_id, photo_url):
    url = f"{TELEGRAM_API_URL}/sendPhoto"
    payload = {"chat_id": chat_id, "photo": photo_url}
    requests.post(url, json=payload)


# === RUN ===
if __name__ == "__main__":
    app.run(debug=True)


