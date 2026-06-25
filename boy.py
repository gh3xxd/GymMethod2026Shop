import os
import time
import json
import telebot
from threading import Thread
from flask import Flask

# Mini server web per fare in modo che Render rilevi una porta aperta ed eviti il timeout
app = Flask('')

@app.route('/')
def home():
    return "Il bot è attivo e in esecuzione!"

def run_flask():
    # Render assegna automaticamente una porta variabile nell'ambiente, altrimenti usa la 8080
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# Recupero delle credenziali sicure dalle variabili d'ambiente di Render
TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHANNEL_ID = os.environ.get('TELEGRAM_CHANNEL_ID')
AMAZON_TAG = os.environ.get('AMAZON_TAG')

bot = telebot.TeleBot(TOKEN)

def carica_offerte():
    """Carica la lista dei prodotti dal file offerte.json"""
    try:
        with open('offerte.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Errore nel caricamento del file JSON: {e}")
        return []

def genera_link_affiliato(asin):
    """Costruisce il link Amazon pulito con il tuo tag affiliato"""
    return f"https://www.amazon.it/dp/{asin}/?tag={AMAZON_TAG}"

def avvia_pubblicazione():
    """Ciclo infinito che pubblica periodicamente le offerte sul canale"""
    print("Bot avviato e in ascolto...")
    
    while True:
        offerte = carica_offerte()
        
        if not offerte:
            print("Nessuna offerta trovata nel file offerte.json. Ricontrollo tra 60 secondi...")
            time.sleep(60)
            continue

        for offerta in offerte:
            link = genera_link_affiliato(offerta['asin'])
            
            # Formattazione estetica del messaggio Telegram (supporta il Markdown)
            messaggio = (
                f"🏋️‍♂️ **OFFERTA INTEGRATORI** 🏋️‍♂️\n\n"
                f"🔥 **{offerta['titolo']}**\n\n"
                f"🔗 👉 [Acquista in Offerta su Amazon]({link})"
            )
            
            try:
                # Invia il messaggio al tuo canale Telegram
                bot.send_message(CHANNEL_ID, messaggio, parse_mode='Markdown', disable_web_page_preview=False)
                print(f"Inviata con successo l'offerta: {offerta['titolo']}")
            except Exception as e:
                print(f"Errore durante l'invio del messaggio su Telegram: {e}")
            
            # Intervallo di tempo tra un post e l'altro per evitare spam.
            # 14400 secondi corrispondono a esattamente 4 ore.
            # NOTA: Per fare un test rapido la prima volta e vedere subito i messaggi,
            # puoi cambiare 14400 con 15 (secondi). Poi rimettilo alto prima di lasciarlo andare!
            print("In attesa per il prossimo post...")
            time.sleep(14400) 

if __name__ == "__main__":
    # 1. Avvia il server Flask in un thread secondario in background
    flask_thread = Thread(target=run_flask)
    flask_thread.daemon = True  # Permette al programma principale di chiudersi correttamente
    flask_thread.start()
    
    # 2. Avvia il ciclo continuo di invio offerte sul thread principale
    avvia_pubblicazione()