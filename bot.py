import os
import time
import random
import telebot
import threading
import requests
import re
from urllib.parse import quote_plus
from bs4 import BeautifulSoup
from flask import Flask
from supabase import create_client, Client

app = Flask('')

@app.route('/')
def home():
    return "Il bot Amazon Offerte (Grafica Sconti) è ONLINE!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port, debug=False)

TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHANNEL_ID = os.environ.get('TELEGRAM_CHANNEL_ID')
AMAZON_TAG = os.environ.get('AMAZON_TAG')
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')

if SUPABASE_URL and SUPABASE_KEY:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    print("⚠️ Attenzione: Supabase non configurato nelle variabili d'ambiente!")
    supabase = None

bot = telebot.TeleBot(TOKEN) if TOKEN else None

# ==================== CONFIGURAZIONE NICCHIA PALESTRA ====================
KEYWORDS_DA_CERCARE = [
    "esn designer protein",
    "creatina monoidrato",
    "proteine whey 1kg",
    "barrette proteiche box",
    "aminoacidi bcaa",
    "burro darachidi 1kg",
    "avena istantanea aromatizzata",
    "omega 3 integratore",
    "pre workout energetico",
    "integratore magnesio potassio",
    "crema di riso istantanea",
    "salsa zero calorie",
    "albume duovo brik"
]

PAROLE_BANNATE = [
    "manubri", "bilanciere", "panca", "elastici", "guanti", "tappetino", 
    "corda", "borraccia", "shaker", "cintura palestra", "gancio", "polsini", 
    "rack", "tapis roulant", "cyclette", "maglietta", "canotta", "pantaloncini",
    "borsa", "zaino", "Gym", "attrezzatura", "palla medica", "kettlebell"
]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
]

# ==================== GESTIONE PROXY DINAMICI ====================
PROXY_LIST = [] 
PROXY_CORRENTE = None
PROXY_CAMBIO_ORA = 0

def scarica_proxy_da_geonix():
    """Scrappa i proxy gratuiti direttamente da Geonix con timeout rigido"""
    url = "https://free.geonix.com/it/?page=1"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }
    proxy_scrappati = []
    
    try:
        print("🌐 Connessione a Geonix in corso...")
        # (3, 4) significa: 3 secondi per connettersi, 4 secondi per ricevere i dati. 
        # Se Geonix fa il furbo, la richiesta muore dopo 7 secondi totali invece di bloccarsi per ore.
        response = requests.get(url, headers=headers, timeout=(3, 4))
        print(f"📥 Geonix ha risposto con status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ Impossibile raggiungere Geonix. Status: {response.status_code}")
            return []
            
        soup = BeautifulSoup(response.text, "html.parser")
        righe = soup.find_all("tr")
        
        for riga in righe:
            celle = riga.find_all("td")
            if len(celle) >= 4:
                ip = celle[0].text.strip()
                ip = re.sub(r'[^\d.]', '', ip) 
                porta = celle[1].text.strip()
                
                if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', ip) and porta.isdigit():
                    stringa_proxy = f"http://{ip}:{porta}"
                    if stringa_proxy not in proxy_scrappati:
                        proxy_scrappati.append(stringa_proxy)
                        
        print(f"📡 Geonix: Scaricati con successo {len(proxy_scrappati)} proxy dinamici.")
        return proxy_scrappati
    except requests.exceptions.RequestException as geonix_err:
        print(f"⚠️ Geonix non ha risposto in tempo o ha rifiutato la connessione: {geonix_err}")
        return []
    except Exception as e:
        print(f"❌ Errore imprevisto durante lo scraping da Geonix: {e}")
        return []
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            print(f"❌ Impossibile raggiungere Geonix. Status: {response.status_code}")
            return []
            
        soup = BeautifulSoup(response.text, "html.parser")
        righe = soup.find_all("tr")
        
        for riga in righe:
            celle = riga.find_all("td")
            if len(celle) >= 4:
                ip = celle[0].text.strip()
                ip = re.sub(r'[^\d.]', '', ip) 
                porta = celle[1].text.strip()
                
                if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', ip) and porta.isdigit():
                    stringa_proxy = f"http://{ip}:{porta}"
                    if stringa_proxy not in proxy_scrappati:
                        proxy_scrappati.append(stringa_proxy)
                        
        print(f"📡 Geonix: Scaricati con successo {len(proxy_scrappati)} proxy dinamici.")
        return proxy_scrappati
    except Exception as e:
        print(f"❌ Errore durante lo scraping da Geonix: {e}")
        return []

def scegli_proxy(forza_cambio=False):
    global PROXY_CORRENTE, PROXY_CAMBIO_ORA, PROXY_LIST
    ora = time.time()

    if not PROXY_LIST or forza_cambio:
        print("🔄 Aggiornamento del pool di proxy da Geonix in corso...")
        PROXY_LIST = scarica_proxy_da_geonix()
        
        if not PROXY_LIST:
            print("⚠️ Fallback: Geonix vuoto. Uso proxy di emergenza temporaneo.")
            PROXY_LIST = ["http://91.214.62.121:8053"] 

    if PROXY_CORRENTE is None or ora > PROXY_CAMBIO_ORA or forza_cambio:
        PROXY_CORRENTE = random.choice(PROXY_LIST)
        PROXY_CAMBIO_ORA = ora + random.randint(1800, 3600) 
        print(f"🔄 {'[FORZATO]' if forza_cambio else ''} Nuovo proxy selezionato: {PROXY_CORRENTE}")

    return PROXY_CORRENTE

# ==================== SUPABASE DB ====================
def salva_offerta_su_db(asin, titolo, prezzo_attuale, prezzo_vecchio, pubblicato=False):
    if not supabase: return
    try:
        data = {
            "asin": asin,
            "titolo": titolo,
            "prezzo_base": prezzo_vecchio,
            "ultimo_prezzo": prezzo_attuale,
            "pubblicato": pubblicato,
            "ultimo_controllo": "now()"
        }
        supabase.table("offerte").upsert(data, on_conflict="asin").execute()
    except Exception as e:
        print(f"❌ Errore sincronizzazione Supabase: {e}")

def asin_gia_pubblicato(asin):
    if not supabase: return False
    try:
        res = supabase.table("offerte").select("pubblicato").eq("asin", asin).execute()
        if res.data and len(res.data) > 0:
            return res.data[0].get("pubblicato", False)
    except Exception as e:
        print(f"❌ Errore lettura Supabase: {e}")
    return False

# ==================== UTILS PREZZI ====================
def pulisci_prezzo(testo):
    if not testo: return None
    testo_pulito = re.sub(r'[^\d.,]', '', testo)
    if not testo_pulito: return None

    if ',' in testo_pulito and ('.' not in testo_pulito or testo_pulito.rfind(',') > testo_pulito.rfind('.')):
        testo_pulito = testo_pulito.replace('.', '').replace(',', '.')
    else:
        testo_pulito = testo_pulito.replace(',', '')

    try:
        return float(testo_pulito)
    except ValueError:
        return None

# ==================== SCRAPER ====================
def cerca_offerte_amazon(keyword):
    offerte_trovate = []
    url = f"https://www.amazon.it/s?k={quote_plus(keyword)}"

    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "it-IT,it;q=0.9",
        "Referer": "https://www.google.com/",
        "Connection": "keep-alive"
    }

    print("🔌 Selezione proxy...")
    proxy_scelto = scegli_proxy()
    proxies_config = {"http": proxy_scelto, "https": proxy_scelto}
    print(f"📡 Utilizzo proxy: {proxy_scelto}")

    try:
        attesa_casuale = random.uniform(3, 6)
        print(f"⏳ Attesa anti-bot di {attesa_casuale:.2f} secondi...")
        time.sleep(attesa_casuale)
        
        print(f"🌐 Invio richiesta ad Amazon per: {keyword}...")
        response = requests.get(url, headers=headers, proxies=proxies_config, timeout=(4, 7))
        print(f"📥 Risposta ricevuta. Status Code: {response.status_code}")

        if response.status_code in [503, 403] or "captcha" in response.text.lower():
            print("⚠️ Amazon ha rilevato un blocco/captcha o proxy non valido. Forzo rotazione.")
            scegli_proxy(forza_cambio=True)
            return offerte_trovate

        if response.status_code != 200:
            print(f"❌ Errore HTTP {response.status_code}")
            return offerte_trovate

        print("🥣 Analisi HTML della pagina...")
        soup = BeautifulSoup(response.text, "html.parser")
        prodotti = soup.find_all("div", {"data-component-type": "s-search-result"})
        print(f"📦 Elementi grezzi trovati nella pagina: {len(prodotti)}")

        for p in prodotti:
            asin = p.get("data-asin")
            if not asin: continue

            titolo_el = p.find("h2")
            titolo = titolo_el.text.strip() if titolo_el else "Prodotto Amazon"
            
            titolo_lower = titolo.lower()
            if any(parola in titolo_lower for parola in PAROLE_BANNATE):
                continue 

            titolo_troncato = titolo[:80] + "..." if len(titolo) > 80 else titolo

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

                    gia_inviato = asin_gia_pubblicato(asin)
                    if not gia_inviato:
                        salva_offerta_su_db(asin, titolo_troncato, prezzo_dopo, prezzo_prima, pubblicato=False)

                    if percentuale_sconto < 30 or gia_inviato:
                        continue

                    offerte_trovate.append({
                        "asin": asin,
                        "titolo": titolo_troncato,
                        "prezzo_prima": f"€ {prezzo_prima:.2f}".replace(".", ","),
                        "prezzo_dopo": f"€ {prezzo_dopo:.2f}".replace(".", ","),
                        "sconto": f"{percentuale_sconto}%",
                        "float_prezzo_dopo": prezzo_dopo,
                        "float_prezzo_prima": prezzo_prima
                    })

    except requests.exceptions.RequestException as req_err:
        print(f"❌ Errore di rete/Timeout della richiesta: {req_err}")
        scegli_proxy(forza_cambio=True)
    except Exception as e:
        print(f"❌ Errore generico durante lo scraping: {e}")

    return offerte_trovate

# ==================== PUBBLICAZIONE TELEGRAM ====================
def avvia_pubblicazione():
    print("🤖 Bot avviato regolarmente in background...")

    while True:
        try:
            keyword = random.choice(KEYWORDS_DA_CERCARE)
            print(f"🔎 Avvio ricerca nicchia fitness per: {keyword}")

            prodotti_in_offerta = cerca_offerte_amazon(keyword)
            print(f"Trovati {len(prodotti_in_offerta)} integratori/cibi validi.")

            if prodotti_in_offerta:
                random.shuffle(prodotti_in_offerta)
                prodotto = prodotti_in_offerta[0]

                link_affiliato = f"https://www.amazon.it/dp/{prodotto['asin']}/?tag={AMAZON_TAG}"

                messaggio = (
                    f"💥 <b>SCONTO DEL {prodotto['sconto']}</b> 💥\n\n"
                    f"📦 <b>{prodotto['titolo']}</b>\n\n"
                    f"❌ Prezzo Vecchio: <s>{prodotto['prezzo_prima']}</s>\n"
                    f"✅ <b>Prezzo Offerta: {prodotto['prezzo_dopo']}</b>\n\n"
                    f"🔗 👉 <a href='{link_affiliato}'>Apri l'Offerta su Amazon</a>"
                )

                try:
                    bot.send_message(
                        CHANNEL_ID,
                        messaggio,
                        parse_mode='HTML',
                        disable_web_page_preview=False
                    )
                    print(f"✅ Pubblicato su Telegram: {prodotto['titolo']}")
                    
                    salva_offerta_su_db(
                        prodotto['asin'], 
                        prodotto['titolo'], 
                        prodotto['float_prezzo_dopo'], 
                        prodotto['float_prezzo_prima'], 
                        pubblicato=True
                    )
                except Exception as tel_err:
                    print(f"❌ Errore durante l'invio del messaggio a Telegram: {tel_err}")
            else:
                print("ℹ️ Nessun nuovo integratore in forte sconto trovato in questo ciclo.")

        except Exception as main_err:
            print(f"🚨 Errore critico nel loop: {main_err}")

        attesa = random.randint(900, 1500)
        print(f"⏳ Prossima ricerca tra {attesa // 60} minuti")
        time.sleep(attesa)

# ==================== AVVIO ====================
if __name__ == "__main__":
    if not TOKEN or not CHANNEL_ID or not AMAZON_TAG:
        print("Variabili d'ambiente di Telegram/Amazon mancanti!")
    else:
        bot_thread = threading.Thread(target=avvia_pubblicazione)
        bot_thread.daemon = True
        bot_thread.start()

        run_flask()
