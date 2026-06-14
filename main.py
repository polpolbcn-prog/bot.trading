import os, time, sqlite3, requests, threading
import numpy as np
from telebot import TeleBot

# --- CONFIGURACIÓN ---
TOKEN_TELEGRAM = os.getenv("TELEGRAM_TOKEN")
ID_TELEGRAM = os.getenv("TELEGRAM_CHAT_ID")
ETH_MINT = "7vfCg797rqwKCmwQNpepX8zmYbhG3wD6f1cMZaAht9wj"

bot = TeleBot(TOKEN_TELEGRAM)

# --- ESTRATEGIA: INDICADORES TÉCNICOS ---
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

# --- CONEXIÓN RESILIENTE A PRECIOS ---
def obtener_precio():
    # Intenta primero con Júpiter, si falla, usa DexScreener
    urls = [
        f"https://price.jup.ag/v2/price?ids={ETH_MINT}",
        "https://api.dexscreener.com/latest/dex/tokens/" + ETH_MINT
    ]
    for url in urls:
        try:
            r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            if r.status_code == 200:
                data = r.json()
                if "jup.ag" in url:
                    return float(data["data"][ETH_MINT]["price"])
                else:
                    return float(data["pairs"][0]["priceUsd"])
        except: continue
    return None

# --- COMANDOS Y BOT ---
@bot.message_handler(commands=['balance'])
def comando_balance(message):
    precio = obtener_precio()
    msg = f"💰 *Precio actual:* ${precio:.4f}" if precio else "⚠️ *Error:* No se pudo obtener el precio."
    bot.reply_to(message, msg, parse_mode="Markdown")

def algoritmo_scalping():
    precios = []
    while True:
        p = obtener_precio()
        if p:
            precios.append(p)
            if len(precios) > 50: precios.pop(0)
            
            rsi = calcular_rsi(precios)
            sup, inf = calcular_bollinger(precios)
            
            # LÓGICA DE VALORACIÓN
            if p < inf and rsi < 30:
                bot.send_message(ID_TELEGRAM, f"🟢 *UNDERVALUED*\nPrecio: ${p:.4f}\nRSI: {rsi:.1f}\nEstatus: *Barato*", parse_mode="Markdown")
            elif p > sup and rsi > 70:
                bot.send_message(ID_TELEGRAM, f"🔴 *OVERVALUED*\nPrecio: ${p:.4f}\nRSI: {rsi:.1f}\nEstatus: *Caro*", parse_mode="Markdown")
        
        time.sleep(30)

# --- INICIO ---
if __name__ == "__main__":
    # Arrancar Telegram en paralelo
    threading.Thread(target=lambda: bot.infinity_polling(), daemon=True).start()
    # Arrancar el motor de trading
    algoritmo_scalping()
