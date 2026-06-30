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
    # Render usa la porta 10000 di default per i servizi web
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHANNEL_ID = os.environ.get('TELEGRAM_CHANNEL_ID')
AMAZON_TAG = os.environ.get('AMAZON_TAG')

bot = telebot.TeleBot(TOKEN)
CACHE_FILE = "prodotti_pubblicati.json"

# Inserisci qui le parole chiave reali che vuoi cercare (NON i link interi)
KEYWORDS_DA_CERCARE = ["esn designer protein", "creatina monoidrato", "attrezzatura palestra home gym"]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, Gecko) Chrome/124.0.0.0 Safari/537.36"
]

# ==================== CONFIGURAZIONE PROXY WEBSHARE ====================
PROXY_LIST = [
    "http://fwwvbzyj:p2oxgzm3oc4n@31.59.20.176:6754",
    "http://fwwvbzyj:p2oxgzm3oc4n@31.56.127.193:7684",
    "http://fwwvbzyj:p2oxgzm3oc4n@45.38.107.97:6014",
    "http://fwwvbzyj:p2oxgzm3oc4n@38.154.203.95:5863",
    "http://fwwvbzyj:p2oxgzm3oc4n@198.105.121.200:6462",
    "http://fwwvbzyj:p2oxgzm3oc4n@64.137.96.74:6641",
    "http://fwwvbzyj:p2oxgzm3oc4n@198.23.243.226:6361",
    "http://fwwvbzyj:p2oxgzm3oc4n@38.154.185.97:6370",
    "http://fwwvbzyj:p2oxgzm3oc4n@142.111.67.146:5611",
    "http://fwwvbzyj:p2oxgzm3oc4n@191.96.254.138:6185"
]
# =======================================================================

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
    if not testo:
        return None
    testo_pulito = re.sub(r'[^\d.,]', '', testo)
    if not testo_pulito:
        return None
    
    if ',' in testo_pulito and ('.' not in testo_pulito or testo_pulito.rfind(',') > testo_pulito.rfind('.')):
        testo_pulito = testo_pulito.replace('.', '').replace(',', '.')
    else:
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
    
    proxy_scelto = random.choice(PROXY_LIST)
    proxies_config = {
        "http": proxy_scelto,
        "https": proxy_scelto
    }
    
    ip_visibile = proxy_scelto.split("@")[-1] if "@" in proxy_scelto else proxy_scelto
    print(f"🔄 Tento la ricerca usando il proxy: {ip_visibile}")
    
    try:
        time.sleep(random.uniform(2.0, 4.0))
        response = requests.get(url, headers=headers, proxies=proxies_config, timeout=8)
        
        if response.status_code == 503 or "captcha" in response.text.lower():
            print(f"⚠️ Amazon ha rilevato il bot (Bot Check / 503) per la keyword: {keyword}")
            return offerte_trovate
            
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
            
            prezzo_attuale_el = p.find("span", {"class": "a-price"})
            prezzo_barrato_el = p.find("span", {"class": "a-text-price"})
            
            if prezzo_attuale_el and prezzo_barrato_el:
                testo_attuale = prezzo_attuale_el.find("span", {"class": "a-offscreen"})
                testo_barrato = prezzo_barrato_el.find("span", {"class": "a-text-price"})
                
                if not testo_barrato:
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
        print(f"❌ Errore/Timeout con il proxy {ip_visibile}: {e}")
        
    return offerte_trovate

def avvia_pubblicazione():
    print("Bot avviato regolarmente in background...")
    cronologia_pubblicati = carica_cronologia()

    while True:
        for keyword in KEYWORDS_DA_CERCARE:
            print(f"Avvio ricerca per: {keyword}")
            prodotti_in_offerta = cerca_offerte_amazon(keyword)
            print(f"Trovati {len(prodotti_in_offerta)} prodotti in offerta per '{keyword}'.")
            
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
                    
                    time.sleep(15) 
                except Exception as e:
                    print(f"Errore nell'invio Telegram: {e}")
            
            time.sleep(30) 

        print("Giro completato. Attendo 2 ore...")
        time.sleep(7200)

if __name__ == "__main__":
    if not TOKEN or not CHANNEL_ID or not AMAZON_TAG:
        print("Variabili d'ambiente mancanti su Render!")
    else:
        # 1. Avviamo il bot in un thread separato in background
        bot_thread = threading.Thread(target=avvia_pubblicazione)
        bot_thread.daemon = True
        bot_thread.start()
        
        # 2. Avviamo Flask sul thread principale per Render
        run_flask()