import os
import time
import threading
import requests
import numpy as np
from flask import Flask
import telebot

# --- CONFIGURACIÓN DE VARIABLES DE ENTORNO ---
TOKEN_TELEGRAM = os.environ.get("TELEGRAM_TOKEN")
ID_TELEGRAM = os.environ.get("TELEGRAM_CHAT_ID")
PORT = int(os.environ.get("PORT", 10000))

# Inicializamos el bot de Telegram
bot = telebot.TeleBot(TOKEN_TELEGRAM)

# Inicializamos la app de Flask para engañar a Render y mantenerlo vivo
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is alive and running!"

def run_flask():
    app.run(host='0.0.0.0', port=PORT)

# --- LÓGICA DE TRADING (MOCK / EJEMPLO DE CÁLCULO) ---
# Nota: Guarda aquí tu lógica para rellenar la lista de precios
precios = [] 

def calcular_rsi(precios_list, periodo=14):
    if len(precios_list) < periodo + 1:
        return 50  # Valor neutral si no hay datos suficientes
    cambios = np.diff(precios_list)
    ganancias = np.where(cambios > 0, cambios, 0)
    perdidas = np.where(cambios < 0, -cambios, 0)
    
    avg_ganancia = np.mean(ganancias[:periodo])
    avg_perdida = np.mean(perdidas[:periodo])
    
    if avg_perdida == 0:
        return 100
    
    rs = avg_ganancia / avg_perdida
    return 100 - (100 / (1 + rs))

def calcular_bollinger(precios_list, periodo=20, multiplicador=2):
    if len(precios_list) < periodo:
        return np.mean(precios_list), np.mean(precios_list)
    media = np.mean(precios_list[-periodo:])
    desviacion = np.std(precios_list[-periodo:])
    sup = media + (multiplicador * desviacion)
    inf = media - (multiplicador * desviacion)
    return sup, inf

def obtener_precio():
    # Usamos la API de Dexscreener como respaldo estable si Jupiter falla por DNS
    url = "https://api.dexscreener.com/latest/dex/pairs/solana/7vfCg797rqwKCmwQNpepX8zmYbhG3wD6f1cMZaAht9wj"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            return float(r.json()['pair']['priceUsd'])
    except Exception as e:
        print(f"Error de conexión API: {e}")
    return None

# --- BUCLE PRINCIPAL DEL BOT ---
def algoritmo_scalping():
    print("Motor de trading iniciado...")
    while True:
        p = obtener_precio()
        if p is None:
            print("⏳ Saltando ciclo por falta de datos de precio...")
            time.sleep(30)
            continue
            
        precios.append(p)
        if len(precios) > 50:
            precios.pop(0)
            
        rsi = calcular_rsi(precios)
        sup, inf = calcular_bollinger(precios)
        
        # LÓGICA DE VALORACIÓN (Citas automáticas según mercado)
        if p < inf and rsi < 30:
            # CORREGIDO: Cambiado 'TD_TELEGRAM' por 'ID_TELEGRAM' para evitar caídas
            bot.send_message(ID_TELEGRAM, f"🟢 *UNDERVALUED*\nPrecio: ${p:.4f}\nRSI: {rsi:.1f}\nEstatus: *Barato*", parse_mode="Markdown")
        elif p > sup and rsi > 70:
            bot.send_message(ID_TELEGRAM, f"🔴 *OVERVALUED*\nPrecio: ${p:.4f}\nRSI: {rsi:.1f}\nEstatus: *Caro*", parse_mode="Markdown")
            
        time.sleep(30)

# --- INICIO DE LA APLICACIÓN ---
if __name__ == "__main__":
    # 1. Limpiamos cualquier Webhook previo en Telegram para fulminar el error 409/401
    try:
        bot.remove_webhook()
    except Exception as e:
        print(f"Error al limpiar webhook: {e}")

    # 2. Arrancamos el servidor Flask en un hilo secundario
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    # 3. Arrancamos la escucha de Telegram (Infinity Polling) en paralelo con reconexión automática
    telegram_thread = threading.Thread(
        target=lambda: bot.infinity_polling(none_stop=True, interval=1, timeout=20), 
        daemon=True
    )
    telegram_thread.start()

    # 4. Arrancamos el motor de trading en el hilo principal
    algoritmo_scalping()
