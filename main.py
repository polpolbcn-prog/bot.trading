import os, time, sqlite3, requests, threading
import numpy as np
from telebot import TeleBot

# --- CONFIGURACIÓN ---
TOKEN_TELEGRAM = os.getenv("TELEGRAM_TOKEN")
ID_TELEGRAM = os.getenv("TELEGRAM_CHAT_ID")
ETH_MINT = "7vfCg797rqwKCmwQNpepX8zmYbhG3wD6f1cMZaAht9wj"

bot = TeleBot(TOKEN_TELEGRAM)

# --- ESTRATEGIA (Lógica TradingView Estándar) ---
def calcular_rsi(precios, periodo=14): # Tradicional: 14
    if len(precios) < periodo + 1: return 50
    diff = np.diff(precios)
    ganancias = np.mean(np.where(diff > 0, diff, 0)[-periodo:])
    perdidas = abs(np.mean(np.where(diff < 0, diff, 0)[-periodo:]))
    if perdidas == 0: return 100
    return 100 - (100 / (1 + (ganancias / perdidas)))

def calcular_bollinger(precios, periodo=20): # Tradicional: 20 periodos, 2.0 desviaciones
    if len(precios) < periodo: return 0, 0
    media = np.mean(precios[-periodo:])
    desv = np.std(precios[-periodo:])
    return media + (2.0 * desv), media - (2.0 * desv)

# --- MOTOR PRINCIPAL ---
def obtener_precio():
    try:
        url = f"https://api.jup.ag/price/v2?ids={ETH_MINT}"
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        return float(r.json()["data"][ETH_MINT]["price"])
    except Exception as e:
        print(f"Error Júpiter: {e}")
        return None

def algoritmo_scalping():
    precios = []
    while True:
        p = obtener_precio()
        if p:
            precios.append(p)
            if len(precios) > 50: precios.pop(0) # Mantenemos histórico de 50 velas
            
            # Cálculo de indicadores
            rsi = calcular_rsi(precios)
            sup, inf = calcular_bollinger(precios)
            
            # --- LÓGICA DE VALORACIÓN ---
            # Undervalued: Precio bajo banda + RSI sobrevendido
            if p < inf and rsi < 30:
                bot.send_message(ID_TELEGRAM, f"🟢 *UNDERVALUED*\nPrecio: ${p:.4f}\nRSI: {rsi:.1f} (Sobreventa)\nEstatus: *Barato*")
            
            # Overvalued: Precio sobre banda + RSI sobrecomprado
            elif p > sup and rsi > 70:
                bot.send_message(ID_TELEGRAM, f"🔴 *OVERVALUED*\nPrecio: ${p:.4f}\nRSI: {rsi:.1f} (Sobrecompra)\nEstatus: *Caro*")
        
        time.sleep(30) # Escaneo cada 30 segundos

if __name__ == "__main__":
    # Arrancamos bot de Telegram en hilo separado
    threading.Thread(target=lambda: bot.infinity_polling(), daemon=True).start()
    # Arrancamos estrategia
    algoritmo_scalping()
