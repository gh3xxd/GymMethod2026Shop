import os
import time
import json
import random
import telebot
import threading
import requests
from bs4 import BeautifulSoup
from flask import Flask

# --- INIZIALIZZAZIONE FLASK (Per tenere sveglio Render) ---
app = Flask('')

@app.route('/')
def home():
    return "Il bot Amazon Offerte è ONLINE e il sistema anti-ban è attivo!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# --- CONFIGURAZIONE CREDENZIALI ---
TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHANNEL_ID = os.environ.get('TELEGRAM_CHANNEL_ID')
AMAZON_TAG = os.environ.get('AMAZON_TAG')

bot = telebot.TeleBot(TOKEN)
CACHE_FILE = "prodotti_pubblicati.json"

# Parole chiave delle categorie che vuoi monitorare su Amazon.it
KEYWORDS_DA_CERCARE = ["creatina monoidrato", "attrezzatura palestra home gym"]

# Lista di User-Agent realistici per ingannare i sistemi anti-bot di Amazon
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
]

# --- GESTIONE MEMORIA ANTI-DOPPIONE ---
def carica_cronologia():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                return json.load(f)
        except:
            return []
    return []

def salva_cronologia(cronologia):
    try:
        with open(CACHE_FILE, 'w') as f:
            json.dump(cronologia, f)
    except Exception as e:
        print(f"Errore nel salvataggio della cronologia: {e}")

# --- MOTORE DI SCRAPING MIRATO SU AMAZON ---
def cerca_offerte_amazon(keyword):
    offerte_trovate = []
    # Costruiamo l'URL di ricerca su Amazon Italia
    url = f"https://www.amazon.it/s?k={keyword.replace(' ', '+')}"
    
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Referer": "https://www.google.com/",
        "Connection": "keep-alive"
    }
    
    try:
        # Ritardo casuale per simulare il comportamento umano
        time.sleep(random.uniform(2.0, 5.0))
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code != 200:
            print(f"Amazon ha risposto con errore {response.status_code} per la ricerca: {keyword}")
            return ofertas_trovate
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Selettore dei blocchi prodotto su Amazon
        prodotti = soup.find_all("div", {"data-component-type": "s-search-result"})
        
        for p in prodotti:
            asin = p.get("data-asin")
            if not asin:
                continue
                
            # Estrarre il titolo
            titolo_el = p.find("h2")
            titolo = titolo_el.text.strip() if titolo_el else "Prodotto Amazon"
            
            # --- VERIFICA SE È IN SCONTO ---
            # Cerchiamo la presenza di un prezzo barrato o badge di sconto tipici di Amazon
            prezzo_barrato = p.find("span", {"class": "a-text-price"})
            badge_sconto = p.find("span", {"class": "a-badge-text"})
            
            # Se c'è un prezzo barrato o un badge di offerta, consideriamo il prodotto in sconto
            if prezzo_barrato or badge_sconto:
                # Recuperiamo il prezzo attuale per metterlo nel messaggio
                prezzo_attuale_el = p.find("span", {"class": "a-price-whole"})
                prezzo_centesimi_el = p.find("span", {"class": "a-price-fraction"})
                
                prezzo_str = "Vedi su Amazon"
                if prezzo_attuale_el:
                    centesimi = prezzo_centesimi_el.text.strip() if prezzo_centesimi_el else "00"
                    prezzo_str = f"€ {prezzo_attuale_el.text.strip()},{centesimi}"
                
                offerte_trovate.append({
                    "asin": asin,
                    "titolo": titolo[:85] + "..." if len(titolo) > 85 else titolo, # Accorcia se troppo lungo
                    "prezzo": prezzo_str
                })
                
    except Exception as e:
        print(f"Errore durante lo scraping della keyword {keyword}: {e}")
        
    return offerte_trovate

# --- PROCESSO PRINCIPALE (Ogni 2 Ore) ---
def avvia_pubblicazione():
    print("Bot avviato. Monitoraggio Amazon ogni 2 ore attivo...")
    cronologia_pubblicati = carica_cronologia()

    while True:
        print("Inizio ciclo di scansione su Amazon...")
        
        for keyword in KEYWORDS_DA_CERCARE:
            print(f"Cerco sconti per: '{keyword}'")
            prodotti_in_offerta = cerca_offerte_amazon(keyword)
            
            for prodotto in prodotti_in_offerta:
                asin = prodotto['asin']
                
                # CONTROLLO ANTI-DOPPIONE
                if asin in cronologia_pubblicati:
                    continue 
                
                # Costruisci il link affiliato pulito
                link_affiliato = f"https://www.amazon.it/dp/{asin}/?tag={AMAZON_TAG}"
                
                messaggio = (
                    f"🏋️‍♂️ <b>OFFERTA IN EVIDENZA</b> 🏋️‍♂️\n\n"
                    f"🔥 <b>{prodotto['titolo']}</b>\n"
                    f"💰 Prezzo attuale: <b>{prodotto['prezzo']}</b>\n\n"
                    f"🔗 👉 <a href='{link_affiliato}'>Acquista in Sconto su Amazon</a>"
                )
                
                try:
                    bot.send_message(CHANNEL_ID, messaggio, parse_mode='HTML', disable_web_page_preview=False)
                    print(f"Pubblicato nuovo sconto: {prodotto['titolo']}")
                    
                    # Salva in memoria
                    cronologia_pubblicati.append(asin)
                    if len(cronologia_pubblicati) > 150:  # Evita file enormi
                        cronologia_pubblicati.pop(0)
                    salva_cronologia(cronologia_pubblicati)
                    
                    # Attendi 15 secondi tra un post e l'altro per spalmare i messaggi nel canale
                    time.sleep(15)
                    
                except Exception as e:
                    print(f"Errore nell'invio del messaggio su Telegram: {e}")
            
            # Aspetta un minuto tra una categoria di ricerca e l'altra per non stressare Amazon
            time.sleep(60)

        print("Ciclo di scansione completato. Prossimo controllo tra 2 ore...")
        time.sleep(7200) # Pausa di 2 ore esatte

if __name__ == "__main__":
    if not TOKEN or not CHANNEL_ID or not AMAZON_TAG:
        print("ERRORE CRITICO: Variabili d'ambiente mancanti su Render!")
    else:
        # Avvia Flask in un thread separato
        t = threading.Thread(target=run_flask)
        t.daemon = True
        t.start()
        
        # Avvia il monitoraggio
        avvia_pubblicazione()