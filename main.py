import os, time, threading, requests
import numpy as np
from telebot import TeleBot
from flask import Flask # Nueva librería para engañar a Render

# --- CONFIGURACIÓN ---
TOKEN_TELEGRAM = os.getenv("TELEGRAM_TOKEN")
ID_TELEGRAM = os.getenv("TELEGRAM_CHAT_ID")
PORT = int(os.environ.get("PORT", 10000))
ETH_MINT = "7vfCg797rqwKCmwQNpepX8zmYbhG3wD6f1cMZaAht9wj"

bot = TeleBot(TOKEN_TELEGRAM)
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot activo y operando"

# --- INDICADORES ---
def calcular_rsi(precios, periodo=14):
    if len(precios) < periodo + 1: return 50
    diff = np.diff(precios)
    ganancias = np.mean(np.where(diff > 0, diff, 0)[-periodo:])
    perdidas = abs(np.mean(np.where(diff < 0, diff, 0)[-periodo:]))
    if perdidas == 0: return 100
    return 100 - (100 / (1 + (ganancias / perdidas)))

def calcular_bollinger(precios, periodo=20):
    if len(precios) < periodo: return 0, 0
    media = np.mean(precios[-periodo:])
    desv = np.std(precios[-periodo:])
    return media + (2.0 * desv), media - (2.0 * desv)

def obtener_precio():
    urls = [f"https://price.jup.ag/v2/price?ids={ETH_MINT}", "https://api.dexscreener.com/latest/dex/tokens/" + ETH_MINT]
    for url in urls:
        try:
            r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            if r.status_code == 200:
                data = r.json()
                return float(data["data"][ETH_MINT]["price"]) if "jup.ag" in url else float(data["pairs"][0]["priceUsd"])
        except: continue
    return None

def algoritmo_scalping():
    precios = []
    while True:
        p = obtener_precio()
        if p:
            precios.append(p)
            if len(precios) > 50: precios.pop(0)
            rsi = calcular_rsi(precios)
            sup, inf = calcular_bollinger(precios)
            if p < inf and rsi < 30:
                bot.send_message(ID_TELEGRAM, f"🟢 *UNDERVALUED* (Barato)\nPrecio: ${p:.4f}\nRSI: {rsi:.1f}")
            elif p > sup and rsi > 70:
                bot.send_message(ID_TELEGRAM, f"🔴 *OVERVALUED* (Caro)\nPrecio: ${p:.4f}\nRSI: {rsi:.1f}")
        time.sleep(30)

# --- INICIO ---
if __name__ == "__main__":
    bot.remove_webhook()
    # Arrancar el servidor web falso (engaña a Render)
    threading.Thread(target=lambda: app.run(host="0.0.0.0", port=PORT), daemon=True).start()
    # Arrancar Telegram
    threading.Thread(target=lambda: bot.infinity_polling(none_stop=True), daemon=True).start()
    # Arrancar trading
    algoritmo_scalping()
