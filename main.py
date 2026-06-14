import os
import time
import threading
import requests
import numpy as np
from flask import Flask
import telebot

# --- 1. CONFIGURACIÓN DE VARIABLES DE ENTORNO ---
# Esto conecta directamente con las claves que guardamos en Render
TOKEN_TELEGRAM = os.environ.get("TELEGRAM_TOKEN")
ID_TELEGRAM = os.environ.get("TELEGRAM_CHAT_ID")
PORT = int(os.environ.get("PORT", 10000))

# Inicializamos el bot de Telegram con el token seguro
bot = telebot.TeleBot(TOKEN_TELEGRAM)

# Inicializamos la app web auxiliar para Render
app = Flask(__name__)

@app.route('/')
def home():
    return "¡Bot de trading activo y funcionando de forma segura!"

def run_flask():
    app.run(host='0.0.0.0', port=PORT)

# --- 2. MOTOR DE TRADING Y VARIABLES DE CONTROL ---
precios = [] 

def calcular_rsi(precios_list, periodo=14):
    if len(precios_list) < periodo + 1:
        return 50  
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
    # Usamos la API pública de Dexscreener para evitar caídas de DNS en Render
    url = "https://api.dexscreener.com/latest/dex/pairs/solana/7vfCg797rqwKCmwQNpepX8zmYbhG3wD6f1cMZaAht9wj"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            return float(r.json()['pair']['priceUsd'])
    except Exception as e:
        print(f"Error de conexión al proveedor de precios: {e}")
    return None

# --- 3. BUCLE PRINCIPAL DEL ALGORITMO ---
def algoritmo_scalping():
    print("🚀 Ejecutando algoritmo_maestro... Enviando señal de inicio.")
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
        
        # CORREGIDO: Usamos 'ID_TELEGRAM' de forma unificada para evitar el crash del bot
        if p < inf and rsi < 30:
            bot.send_message(ID_TELEGRAM, f"🟢 *UNDERVALUED*\nPrecio: ${p:.4f}\nRSI: {rsi:.1f}\nEstatus: *Compra*", parse_mode="Markdown")
        elif p > sup and rsi > 70:
            bot.send_message(ID_TELEGRAM, f"🔴 *OVERVALUED*\nPrecio: ${p:.4f}\nRSI: {rsi:.1f}\nEstatus: *Venta*", parse_mode="Markdown")
            
        time.sleep(30)

# --- 4. PUNTO DE ENTRADA ÚNICO ---
if __name__ == "__main__":
    print("🌍 Puerto falso activo en el puerto 10000 para Render Free.")
    print("🏁 Iniciando hilos del sistema...")

    # Limpiamos webhooks conflictivos en los servidores de Telegram antes de empezar
    try:
        bot.remove_webhook()
    except Exception as e:
        print(f"Aviso de Webhook: {e}")

    # Hilo 1: Servidor Web Flask
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    # Hilo 2: Escucha del Bot de Telegram (Infinity Polling)
    print("🤖 Intentando activar escucha de comandos de Telegram (infinity_polling)...")
    telegram_thread = threading.Thread(
        target=lambda: bot.infinity_polling(none_stop=True, interval=1, timeout=20), 
        daemon=True
    )
    telegram_thread.start()

    # Hilo Principal: Motor de Trading
    algoritmo_scalping()
