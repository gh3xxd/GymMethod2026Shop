import os
import time
import json
import random
import telebot
import threading
import requests
import re
from bs4 import BeautifulSoup
from flask import Flask

app = Flask('')

@app.route('/')
def home():
    return "Il bot Amazon Offerte (Grafica Sconti) è ONLINE!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHANNEL_ID = os.environ.get('TELEGRAM_CHANNEL_ID')
AMAZON_TAG = os.environ.get('AMAZON_TAG')

bot = telebot.TeleBot(TOKEN)
CACHE_FILE = "prodotti_pubblicati.json"

KEYWORDS_DA_CERCARE = ["creatina monoidrato", "attrezzatura palestra home gym"]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
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

def pulisci_prezzo(testo):
    """Estrae in modo sicuro un valore float da una stringa di prezzo in formato italiano (es. € 1.250,45 o 24,99€)"""
    if not testo:
        return None
    # Rimuove tutto tranne numeri, virgole e punti
    testo_pulito = re.sub(r'[^\d.,]', '', testo)
    if not testo_pulito:
        return None
    
    # Se l'ultimo separatore è una virgola, scambiamo i punti con stringa vuota e la virgola con il punto
    if ',' in testo_pulito and ('.' not in testo_pulito or testo_pulito.rfind(',') > testo_pulito.rfind('.')):
        testo_pulito = testo_pulito.replace('.', '').replace(',', '.')
    else:
        # Se c'è solo il punto come decimale (formato anglosassone o parziale)
        testo_pulito = testo_pulito.replace(',', '')
        
    try:
        return float(testo_pulito)
    except ValueError:
        return None

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
        time.sleep(random.uniform(3.0, 6.0)) # Un po' più di respiro
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code == 503 or "captcha" in response.text.lower():
            print(f"⚠️ Amazon ha rilevato il bot (Bot Check / 503) per la keyword: {keyword}")
            return ofertas_trovate
            
        if response.status_code != 200:
            print(f"Errore HTTP {response.status_code} per la keyword {keyword}")
            return offerte_trovate
        
        soup = BeautifulSoup(response.text, "html.parser")
        prodotti = soup.find_all("div", {"data-component-type": "s-search-result"})
        
        for p in prodotti:
            asin = p.get("data-asin")
            if not asin:
                continue
                
            titolo_el = p.find("h2")
            titolo = titolo_el.text.strip() if titolo_el else "Prodotto Amazon"
            
            # Trova prezzo attuale e barrato
            prezzo_attuale_el = p.find("span", {"class": "a-price"})
            prezzo_barrato_el = p.find("span", {"class": "a-text-price"})
            
            if prezzo_attuale_el and prezzo_barrato_el:
                testo_attuale = prezzo_attuale_el.find("span", {"class": "a-offscreen"})
                testo_barrato = prezzo_barrato_el.find("span", {"class": "a-offscreen"})
                
                if testo_attuale and testo_barrato:
                    prezzo_dopo = pulisci_prezzo(testo_attuale.text)
                    prezzo_prima = pulisci_prezzo(testo_barrato.text)
                    
                    if not prezzo_dopo or not prezzo_prima or prezzo_prima <= prezzo_dopo:
                        continue
                        
                    percentuale_sconto = int(round(((prezzo_prima - prezzo_dopo) / prezzo_prima) * 100))
                    
                    if percentuale_sconto <= 0:
                        continue
                        
                    offerte_trovate.append({
                        "asin": asin,
                        "titolo": titolo[:80] + "..." if len(titolo) > 80 else titolo,
                        "prezzo_prima": f"€ {prezzo_prima:.2f}".replace(".", ","),
                        "prezzo_dopo": f"€ {prezzo_dopo:.2f}".replace(".", ","),
                        "sconto": f"{percentuale_sconto}%"
                    })
                    
    except Exception as e:
        print(f"Errore durante lo scraping: {e}")
        
    return offerte_trovate

def avvia_pubblicazione():
    print("Bot avviato con nuova grafica sconti...")
    cronologia_pubblicati = carica_cronologia()

    while True:
        for keyword in KEYWORDS_DA_CERCARE:
            print(f"Avvio ricerca per: {keyword}")
            prodotti_in_offerta = cerca_offerte_amazon(keyword)
            print(f"Trovati {len(prodotti_in_offerta)} prodotti in offerta.")
            
            for prodotto in prodotti_in_offerta:
                asin = prodotto['asin']
                
                if asin in cronologia_pubblicati:
                    continue 
                
                link_affiliato = f"https://www.amazon.it/dp/{asin}/?tag={AMAZON_TAG}"
                
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
                    
                    time.sleep(15) # Delay tra i messaggi inviati su Telegram
                except Exception as e:
                    print(f"Errore nell'invio Telegram: {e}")
            
            time.sleep(30) # Pausa tra una keyword e l'altra

        print("Giro completato. Attendo 2 ore...")
        time.sleep(7200)

if __name__ == "__main__":
    if not TOKEN or not CHANNEL_ID or not AMAZON_TAG:
        print("Variabili d'ambiente mancanti!")
    else:
        t = threading.Thread(target=run_flask)
        t.daemon = True
        t.start()
        avvia_pubblicazione()