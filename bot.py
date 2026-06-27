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
    return "Il bot Amazon Offerte (Grafica Sconti) è ONLINE!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# --- CONFIGURAZIONE CREDENZIALI ---
TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHANNEL_ID = os.environ.get('TELEGRAM_CHANNEL_ID')
AMAZON_TAG = os.environ.get('AMAZON_TAG')

bot = telebot.TeleBot(TOKEN)
CACHE_FILE = "prodotti_pubblicati.json"

KEYWORDS_DA_CERCARE = ["creatina monoidrato", "attrezzatura palestra home gym"]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0"
]

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

# --- MOTORE DI SCRAPING CON CALCOLO SCONTO ---
def cerca_offerte_amazon(keyword):
    offerte_trovate = []
    url = f"https://www.amazon.it/s?k={keyword.replace(' ', '+')}"
    
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "it-IT,it;q=0.9",
        "Referer": "https://www.google.com/",
        "Connection": "keep-alive"
    }
    
    try:
        time.sleep(random.uniform(2.0, 5.0))
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code != 200:
            return offerte_trovate
        
        soup = BeautifulSoup(response.text, "html.parser")
        prodotti = soup.find_all("div", {"data-component-type": "s-search-result"})
        
        for p in prodotti:
            asin = p.get("data-asin")
            if not asin:
                continue
                
            titolo_el = p.find("h2")
            titolo = titolo_el.text.strip() if titolo_el else "Prodotto Amazon"
            
            # 1. Trova il prezzo attuale (Prezzo DOPO)
            prezzo_attuale_el = p.find("span", {"class": "a-price-whole"})
            prezzo_centesimi_el = p.find("span", {"class": "a-price-fraction"})
            
            # 2. Trova il prezzo barrato (Prezzo PRIMA)
            prezzo_barrato_el = p.find("span", {"class": "a-text-price"})
            
            # Procediamo solo se abbiamo sia il prezzo attuale che quello barrato (quindi c'è uno sconto reale)
            if prezzo_attuale_el and prezzo_barrato_el:
                # Pulizia prezzo attuale
                centesimi = prezzo_centesimi_el.text.strip() if prezzo_centesimi_el else "00"
                testo_prezzo_attuale = f"{prezzo_attuale_el.text.strip()},{centesimi}".replace("€", "").strip()
                
                # Pulizia prezzo barrato (Amazon spesso lo scrive come "€50,00" o "50,00€")
                testo_prezzo_barrato = prezzo_barrato_el.find("span", {"class": "a-offscreen"})
                if testo_prezzo_barrato:
                    testo_prezzo_barrato = testo_prezzo_barrato.text.strip().replace("€", "").replace(".", "").replace(",", ".").strip()
                else:
                    continue
                
                try:
                    # Convertiamo in numeri per calcolare lo sconto percentuale reale
                    prezzo_dopo = float(testo_prezzo_attuale.replace(".", "").replace(",", "."))
                    prezzo_prima = float(testo_prezzo_barrato)
                    
                    # Calcolo matematico della percentuale: ((Prima - Dopo) / Prima) * 100
                    percentuale_sconto = int(round(((prezzo_prima - prezzo_dopo) / prezzo_prima) * 100))
                    
                    # Evitiamo errori strani o sconti dello 0%
                    if percentuale_sconto <= 0:
                        continue
                        
                    offerte_trovate.append({
                        "asin": asin,
                        "titolo": titolo[:80] + "..." if len(titolo) > 80 else titolo,
                        "prezzo_prima": f"€ {prezzo_prima:.2f}".replace(".", ","),
                        "prezzo_dopo": f"€ {prezzo_dopo:.2f}".replace(".", ","),
                        "sconto": f"{percentuale_sconto}%"
                    })
                except ValueError:
                    # Se la conversione fallisce a causa di caratteri strani, salta il prodotto in modo sicuro
                    continue
                
    except Exception as e:
        print(f"Errore durante lo scraping: {e}")
        
    return offerte_trovate

# --- PROCESSO PRINCIPALE ---
def avvia_pubblicazione():
    print("Bot avviato con nuova grafica sconti...")
    cronologia_pubblicati = carica_cronologia()

    while True:
        for keyword in KEYWORDS_DA_CERCARE:
            prodotti_in_offerta = cerca_offerte_amazon(keyword)
            
            for prodotto in prodotti_in_offerta:
                asin = prodotto['asin']
                
                if asin in cronologia_pubblicati:
                    continue 
                
                link_affiliato = f"https://www.amazon.it/dp/{asin}/?tag={AMAZON_TAG}"
                
                # --- NUOVA GRAFICA MESSAGGIO TELEGRAM ---
                messaggio = (
                    f"💥 <b>SCONTO DEL {prodotto['sconto']}</b> 💥\n\n"
                    f"📦 <b>{prodotto['titolo']}</b>\n\n"
                    f"❌ Prezzo Vecchio: <s>{prodotto['prezzo_prima']}</s>\n"
                    f"✅ <b>Prezzo Offerta: {prodotto['prezzo_dopo']}</b>\n\n"
                    f"🔗 👉 <a href='{link_affiliato}'>Apri l'Offerta su Amazon</a>"
                )
                
                try:
                    bot.send_message(CHANNEL_ID, messaggio, parse_mode='HTML', disable_web_page_preview=False)
                    print(f"Pubblicato: {prodotto['titolo']} con sconto {prodotto['sconto']}")
                    
                    cronologia_pubblicati.append(asin)
                    if len(cronologia_pubblicati) > 150:
                        cronologia_pubblicati.pop(0)
                    salva_cronologia(cronologia_pubblicati)
                    
                    time.sleep(15)
                except Exception as e:
                    print(f"Errore nell'invio: {e}")
            
            time.sleep(60)

        time.sleep(7200) # Controllo ogni 2 ore

if __name__ == "__main__":
    if not TOKEN or not CHANNEL_ID or not AMAZON_TAG:
        print("Variabili d'ambiente mancanti!")
    else:
        t = threading.Thread(target=run_flask)
        t.daemon = True
        t.start()
        avvia_pubblicazione()