import os
import logging
import requests
import uuid
from telegram import Update, InputMediaPhoto
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore

# Load env
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
NOWPAYMENTS_API_KEY = os.getenv("NOWPAYMENTS_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Firebase
if not firebase_admin._apps:
    cred = credentials.Certificate("firebase.json")  # Make sure this exists
    firebase_admin.initialize_app(cred)
db = firestore.client()

# Logging
logging.basicConfig(level=logging.INFO)

# Verify system
def is_verified(user_id):
    doc = db.collection("users").document(str(user_id)).get()
    return doc.exists and doc.to_dict().get("verified", False)

def is_premium(user_id):
    doc = db.collection("users").document(str(user_id)).get()
    return doc.exists and doc.to_dict().get("premium", False)

def save_message(user_id, message):
    doc_ref = db.collection("memory").document(str(user_id))
    old = doc_ref.get().to_dict() if doc_ref.get().exists else {}
    history = old.get("messages", [])
    history.append(message)
    if len(history) > 10:
        history = history[-10:]
    doc_ref.set({"messages": history})

def get_history(user_id):
    doc = db.collection("memory").document(str(user_id)).get()
    return doc.to_dict().get("messages", []) if doc.exists else []

# Commands
def start(update: Update, context: CallbackContext):
    update.message.reply_text("Benvenuto! Usa /verify per iniziare o /pay per diventare premium.")

def help_cmd(update: Update, context: CallbackContext):
    update.message.reply_text("/verify - Verifica il tuo account\n/status - Controlla il tuo stato\n/pay - Acquista premium\n/image - Genera immagine NSFW (premium)")

def verify(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    verify_link = f"https://t.me/yourbot?start=verify-{user_id}"
    db.collection("users").document(str(user_id)).set({"verified": True}, merge=True)
    update.message.reply_text(f"✅ Verificato! Usa /pay per accedere alle funzioni premium.\nProof: {verify_link}")

def status(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    ver = is_verified(user_id)
    prem = is_premium(user_id)
    update.message.reply_text(f"🧾 Verificato: {'✅' if ver else '❌'}\n💎 Premium: {'✅' if prem else '❌'}")

def pay(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    order_id = str(uuid.uuid4())
    amount = 5.00  # USD
    payload = {
        "price_amount": amount,
        "price_currency": "usd",
        "pay_currency": "usdttrc20",
        "order_id": order_id,
        "ipn_callback_url": "https://your-callback-url.com/payment",
    }
    headers = {"x-api-key": NOWPAYMENTS_API_KEY, "Content-Type": "application/json"}
    r = requests.post("https://api.nowpayments.io/v1/invoice", headers=headers, json=payload)
    if r.status_code == 200:
        payment_url = r.json()["invoice_url"]
        db.collection("users").document(str(user_id)).update({"pending_order": order_id})
        update.message.reply_text(f"💳 Paga qui per diventare premium:\n{payment_url}")
    else:
        update.message.reply_text("Errore durante la creazione del link di pagamento.")

def image_cmd(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    if not is_premium(user_id):
        return update.message.reply_text("🔒 Solo per utenti premium. Usa /pay.")
    prompt = " ".join(context.args) or "NSFW anime girl, detailed"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "prompt": prompt,
        "model": "stable-diffusion",
        "nsfw": True
    }
    response = requests.post("https://openrouter.ai/api/v1/generate/image", json=payload, headers=headers)
    if response.status_code == 200:
        image_url = response.json().get("url")
        update.message.reply_photo(photo=image_url)
    else:
        update.message.reply_text("Errore generazione immagine.")

# Text handler
def chat(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    text = update.message.text

    if not is_premium(user_id):
        return update.message.reply_text("🔒 Solo utenti premium possono ricevere risposte NSFW. Usa /pay.")

    save_message(user_id, f"user: {text}")
    history = get_history(user_id)
    prompt = "\n".join(history) + f"\nAI:"

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "nous-hermes2",
        "prompt": prompt,
        "max_tokens": 150
    }

    response = requests.post("https://openrouter.ai/api/v1/chat/completions", json=payload, headers=headers)
    if response.status_code == 200:
        reply = response.json()["choices"][0]["message"]["content"]
        update.message.reply_text(reply)
        save_message(user_id, f"AI: {reply}")
    else:
        update.message.reply_text("Errore risposta AI.")

# Main
def main():
    updater = Updater(token=TELEGRAM_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help_cmd))
    dp.add_handler(CommandHandler("verify", verify))
    dp.add_handler(CommandHandler("status", status))
    dp.add_handler(CommandHandler("pay", pay))
    dp.add_handler(CommandHandler("image", image_cmd))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, chat))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()

























