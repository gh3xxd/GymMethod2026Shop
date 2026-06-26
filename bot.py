import os
import time
import json
import telebot
import threading  # <--- Serve per far girare Flask e il Bot insieme
from flask import Flask  # <--- Serve per ingannare Render

# Inizializziamo Flask
app = Flask('')

@app.route('/')
def home():
    return "Il bot è online!"

def run_flask():
    # Recupera la porta che Render assegna automaticamente
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# --- Il tuo codice originale modificato con il ciclo ---

TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHANNEL_ID = os.environ.get('TELEGRAM_CHANNEL_ID')
AMAZON_TAG = os.environ.get('AMAZON_TAG')

bot = telebot.TeleBot(TOKEN)

def carica_offerte():
    try:
        with open('offerte.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Errore nel caricamento del file JSON: {e}")
        return []

def genera_link_affiliato(asin):
    return f"https://www.amazon.it/dp/{asin}/?tag={AMAZON_TAG}"

def avvia_pubblicazione():
    print("Bot avviato e in ascolto...")
    while True:
        offerte = carica_offerte()
        if not offerte:
            print("Nessuna offerta trovata. Riconto tra 60 secondi...")
            time.sleep(60)
            continue

        for offerta in offerte:
            link = genera_link_affiliato(offerta['asin'])
            messaggio = (
                f"🏋️‍♂️ <b>OFFERTA INTEGRATORI</b> 🏋️‍♂️\n\n"
                f"🔥 <b>{offerta['titolo']}</b>\n\n"
                f"🔗 👉 <a href='{link}'>Acquista in Offerta su Amazon</a>"
            )
            try:
                bot.send_message(CHANNEL_ID, messaggio, parse_mode='HTML', disable_web_page_preview=False)
                print(f"Inviata offerta: {offerta['titolo']}")
            except Exception as e:
                print(f"Errore nell'invio: {e}")
            
            # Pausa di 4 ore (usa 10 per i test)
            time.sleep(14400)

if __name__ == "__main__":
    if not TOKEN or not CHANNEL_ID or not AMAZON_TAG:
        print("ERRORE: Variabili d'ambiente mancanti!")
    else:
        # 1. Avvia Flask in un thread separato così Render vede la porta aperta
        t = threading.Thread(target=run_flask)
        t.daemon = True
        t.start()
        
        # 2. Avvia normalmente il bot nel thread principale
        avvia_pubblicazione()