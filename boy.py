import os
import time
import json
import telebot

# Recupera le credenziali che nasconderemo su Render
TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHANNEL_ID = os.environ.get('TELEGRAM_CHANNEL_ID')
AMAZON_TAG = os.environ.get('AMAZON_TAG') # Il tuo tag affiliato (es. pippo-21)

bot = telebot.TeleBot(TOKEN)

def carica_offerte():
    """Carica la lista dei prodotti dal file JSON"""
    try:
        with open('offerte.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Errore nel caricamento del file JSON: {e}")
        return []

def genera_link_affiliato(asin):
    """Costruisce il link Amazon pulito con il tuo tag"""
    return f"https://www.amazon.it/dp/{asin}/?tag={AMAZON_TAG}"

def avvia_pubblicazione():
    print("Bot avviato e in ascolto...")
    offerte = carica_offerte()
    
    if not offerte:
        print("Nessuna offerta trovata nel file.")
        return

    for offerta in offerte:
        link = genera_link_affiliato(offerta['asin'])
        
        # Testo del messaggio che apparirà su Telegram
        messaggio = (
            f"🏋️‍♂️ **OFFERTA INTEGRATORI** 🏋️‍♂️\n\n"
            f"🔥 **{offerta['titolo']}**\n\n"
            f"🔗 👉 [Acquista in Offerta su Amazon]({link})"
        )
        
        try:
            # Invia il messaggio al canale
            bot.send_message(CHANNEL_ID, messaggio, parse_mode='Markdown', disable_web_page_preview=False)
            print(f"Inviata offerta: {offerta['titolo']}")
        except Exception as e:
            print(f"Errore nell'invio: {e}")
        
        # Pausa tra un post e l'altro per non fare spam (es. 4 ore = 14400 secondi)
        # Per fare un test rapido puoi impostarlo a 10 secondi, poi lo alzi.
        time.sleep(14400) 

if __name__ == "__main__":
    avvia_pubblicazione()