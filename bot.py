import os
import time
import json
import telebot

# Recupera le credenziali da Render
TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHANNEL_ID = os.environ.get('TELEGRAM_CHANNEL_ID')
AMAZON_TAG = os.environ.get('AMAZON_TAG')

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
    
    # Se vuoi che il bot controlli continuamente il file, 
    # mettiamo il ciclo qui
    while True:
        offerte = carica_offerte()
        
        if not offerte:
            print("Nessuna offerta trovata nel file. Ricontrollo tra 60 secondi...")
            time.sleep(60)
            continue

        for offerta in offerte:
            link = genera_link_affiliato(offerta['asin'])
            
            # Formattazione in HTML: più sicura ed evita bug con caratteri speciali
            messaggio = (
                f"🏋️‍♂️ <b>OFFERTA INTEGRATORI</b> 🏋️‍♂️\n\n"
                f"🔥 <b>{offerta['titolo']}</b>\n\n"
                f"🔗 👉 <a href='{link}'>Acquista in Offerta su Amazon</a>"
            )
            
            try:
                # Invia il messaggio al canale usando HTML
                bot.send_message(CHANNEL_ID, messaggio, parse_mode='HTML', disable_web_page_preview=False)
                print(f"Inviata offerta: {offerta['titolo']}")
            except Exception as e:
                print(f"Errore nell'invio di {offerta['titolo']}: {e}")
            
            # Pausa tra un post e l'altro (es. 4 ore)
            # NOTA: Per i test cambialo a 10 secondi!
            time.sleep(14400) 

if __name__ == "__main__":
    # Controllo di sicurezza per evitare crash immediati se dimentichi le variabili su Render
    if not TOKEN or not CHANNEL_ID or not AMAZON_TAG:
        print("ERRORE: Variabili d'ambiente mancanti su Render!")
    else:
        avvia_pubblicazione()