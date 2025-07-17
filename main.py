import os
import requests
from flask import Flask, request, jsonify
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

BOT_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

app = Flask(__name__)

HEADERS = {
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "Content-Type": "application/json"
}

def send_message(chat_id, text):
    requests.post(f"{BOT_URL}/sendMessage", json={
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    })

def send_photo(chat_id, photo_url, caption=None):
    payload = {
        "chat_id": chat_id,
        "photo": photo_url,
    }
    if caption:
        payload["caption"] = caption
    requests.post(f"{BOT_URL}/sendPhoto", json=payload)

def generate_text_reply(prompt):
    url = "https://openrouter.ai/api/v1/chat/completions"
    body = {
        "model": "gryphe/mythomist-7b",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 500,
        "temperature": 0.8,
        "top_p": 0.9
    }
    response = requests.post(url, headers=HEADERS, json=body)
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"]

def generate_image(prompt):
    url = "https://openrouter.ai/api/v1/image/generations"
    body = {
        "model": "revAnimated",
        "prompt": prompt,
        "negative_prompt": "blurry, low quality, watermark, text, cropped",
        "width": 512,
        "height": 768,
        "samples": 1,
        "steps": 30,
        "cfg_scale": 7.5
    }
    response = requests.post(url, headers=HEADERS, json=body)
    response.raise_for_status()
    data = response.json()
    # The response may include a list of image URLs under "artifacts"
    return data["artifacts"][0]["url"]

@app.route("/", methods=["POST"])
def webhook():
    data = request.get_json()

    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "").strip()

        if text.startswith("/image"):
            prompt = text[len("/image"):].strip()
            if not prompt:
                send_message(chat_id, "Please provide a prompt after /image. Example:\n/image a sexy anime warrior")
                return jsonify({"status": "ok"})

            send_message(chat_id, "🎨 Generating your NSFW image... please wait 20–40 seconds.")

            try:
                image_url = generate_image(prompt)
                send_photo(chat_id, image_url, caption=f"Prompt: {prompt}")
            except Exception as e:
                send_message(chat_id, f"❌ Failed to generate image. Error: {str(e)}")

        else:
            try:
                reply = generate_text_reply(text)
                send_message(chat_id, reply)
            except Exception as e:
                send_message(chat_id, f"⚠️ Error generating reply: {str(e)}")

    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

