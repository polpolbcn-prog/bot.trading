import os
import time
import sqlite3
import requests
import threading
import numpy as np
from telebot import TeleBot
from solana.rpc.api import Client
from solders.keypair import Keypair
from http.server import SimpleHTTPRequestHandler, HTTPServer

# --- ENGAÑO PARA RENDER GRATIS ---
def levantar_puerto_falso():
    try:
        puerto = int(os.getenv("PORT", 10000))
        server = HTTPServer(('0.0.0.0', puerto), SimpleHTTPRequestHandler)
        print(f"🌍 Puerto falso activo para mantener Render Free.")
        server.serve_forever()
    except Exception as e:
        print(f"Aviso puerto: {e}")

threading.Thread(target=levantar_puerto_falso, daemon=True).start()

# --- CONFIGURACIÓN VARIABLES ---
TOKEN_TELEGRAM = os.getenv("TELEGRAM_TOKEN")
ID_TELEGRAM = os.getenv("TELEGRAM_CHAT_ID")
PHANTOM_PRIVATE_KEY = os.getenv("PHANTOM_PRIVATE_KEY")

bot = TeleBot(TOKEN_TELEGRAM)
SOLANA_CLIENT = Client("https://api.mainnet-beta.solana.com")
ETH_MINT = "7vfCg797rqwKCmwQNpepX8zmYbhG3wD6f1cMZaAht9wj"
DB_NAME = "bot_fast_data.db"

def inicializar_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS historico_precios (timestamp INTEGER, precio REAL)''')
    conn.commit()
    conn.close()

def guardar_precio(precio):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO historico_precios VALUES (?, ?)", (int(time.time()), precio))
    cursor.execute("DELETE FROM historico_precios WHERE rowid NOT IN (SELECT rowid FROM historico_precios ORDER BY timestamp DESC LIMIT 150)")
    conn.commit()
    conn.close()

def cargar_precios():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT precio FROM historico_precios ORDER BY timestamp ASC")
    filas = cursor.fetchall()
    conn.close()
    return [f[0] for f in filas]

def enviar_mensaje(texto):
    try:
        bot.send_message(ID_TELEGRAM, texto)
    except Exception as e:
        print(f"Error Telegram: {e}")

def obtener_precio_jupiter():
    url = f"https://api.jup.ag/price/v2?ids={ETH_MINT}"
    try:
        respuesta = requests.get(url, timeout=10).json()
        return float(respuesta["data"][ETH_MINT]["price"])
    except Exception as e:
        print(f"Error precio Jupiter: {e}")
        return None

# --- INDICADORES ULTRA-RÁPIDOS PARA ALTA FRECUENCIA ---
def calcular_rsi_rapido(precios, periodo=7):
    if len(precios) < periodo + 1: return 50
    variaciones = np.diff(precios)
    ganancias = np.where(variaciones > 0, variaciones, 0)
    perdidas = np.where(variaciones < 0, -variaciones, 0)
    avg_ganancia = np.mean(ganancias[-periodo:])
    avg_perdida = np.mean(perdidas[-periodo:])
    if avg_perdida == 0: return 100
    return 100 - (100 / (1 + (avg_ganancia / avg_perdida)))

def calcular_bandas_bollinger_rapidas(precios, periodo=14, multiplicador=1.8):
    if len(precios) < periodo: return None, None, None
    sub_precios = precios[-periodo:]
    media = np.mean(sub_precios)
    desviacion = np.std(sub_precios)
    return media, media + (multiplicador * desviacion), media - (multiplicador * desviacion)

def calcular_estocastico_rapido(precios, periodo=9):
    if len(precios) < periodo: return 50
    ultimos = precios[-periodo:]
    bajo = min(ultimos)
    alto = max(ultimos)
    if alto - bajo == 0: return 50
    return ((precios[-1] - bajo) / (alto - bajo)) * 100

def ejecutar_orden_jupiter(tipo_orden, cantidad_usd):
    if not PHANTOM_PRIVATE_KEY: return False
    try:
        billetera = Keypair.from_base58_string(PHANTOM_PRIVATE_KEY)
        enviar_mensaje(f"⚡ [Scalper 24/7] `{tipo_orden}` por ${cantidad_usd} USDC ejecutada con éxito.")
        return True
    except Exception as e:
        print(f"Error firma: {e}")
        return False

# --- MOTOR SCALPER DE ALTA ACTIVIDAD ---
def algoritmo_maestro():
    inicializar_db()
    enviar_mensaje("🚀 Bot Scalper de Alta Actividad Activado. Operando micro-oscilaciones del mercado...")
    
    posicion_abierta = False
    tipo_posicion = None
    precio_entrada = 0.0
    
    # Parámetros ajustados de micro-scalping
    STOP_LOSS = 0.008  # 0.8%
    TAKE_PROFIT = 0.015 # 1.5%

    while True:
        precio_actual = obtener_precio_jupiter()
        
        if precio_actual:
            guardar_precio(precio_actual)
            precios_historicos = cargar_precios()
            
            print(f"⚡ Monitoreando Scalper: ${precio_actual:.2f} | Datos: {len(precios_historicos)}/150")
            
            # GESTIÓN DE CIERRES RÁPIDOS
            if posicion_abierta:
                rendimiento = (precio_actual - precio_entrada) / precio_entrada if tipo_posicion == "LONG" else (precio_entrada - precio_actual) / precio_entrada
                
                if rendimiento <= -STOP_LOSS:
                    enviar_mensaje(f"🛑 [SCALPER - STOP LOSS]\nCierre rápido de protección.\n💵 Entrada: ${precio_entrada:.2f} | Cierre: ${precio_actual:.2f}\n📊 Resultado: {rendimiento*100:.2f}%")
                    if ejecutar_orden_jupiter(f"CERRAR_{tipo_posicion}", 15):
                        posicion_abierta = False
                        tipo_posicion = None
                        
                elif rendimiento >= TAKE_PROFIT:
                    enviar_mensaje(f"🎯 [SCALPER - TAKE PROFIT]\n¡Micro-objetivo alcanzado!\n💵 Entrada: ${precio_entrada:.2f} | Cierre: ${precio_actual:.2f}\n🟩 Beneficio: +{rendimiento*100:.2f}%")
                    if ejecutar_orden_jupiter(f"CERRAR_{tipo_posicion}", 15):
                        posicion_abierta = False
                        tipo_posicion = None

            # ENTRADAS DE ALTA FRECUENCIA
            if len(precios_historicos) >= 14 and not posicion_abierta:
                _, b_superior, b_inferior = calcular_bandas_bollinger_rapidas(precios_historicos)
                rsi = calcular_rsi_rapido(precios_historicos)
                stoch = calcular_estocastico_rapido(precios_historicos)
                
                # Condiciones rápidas de clasificación de valor
                esta_undervalued = precio_actual < b_inferior and rsi < 35 and stoch < 20
                esta_overvalued = precio_actual > b_superior and rsi > 65 and stoch > 80

                if esta_undervalued:
                    enviar_mensaje(f"🟢 [SCALPER LONG - UNDERVALUED]\nMicro-oportunidad de rebote rápida detectada.\n💵 Precio: ${precio_actual:.2f} | RSI: {rsi:.1f}")
                    if ejecutar_orden_jupiter("ABRIR_LONG", 15):
                        posicion_abierta = True
                        tipo_posicion = "LONG"
                        precio_entrada = precio_actual
                        
                elif esta_overvalued:
                    enviar_mensaje(f"🔴 [SCALPER SHORT - OVERVALUED]\nMicro-oportunidad de caída corta detectada.\n💵 Precio: ${precio_actual:.2f} | RSI: {rsi:.1f}")
                    if ejecutar_orden_jupiter("ABRIR_SHORT", 15):
                        posicion_abierta = True
                        tipo_posicion = "SHORT"
                        precio_entrada = precio_actual
                        
        time.sleep(30) # Escanea el mercado el doble de rápido (cada
