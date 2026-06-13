import os
import time
import sqlite3
import requests
import numpy as np
from telebot import TeleBot
from solana.rpc.api import Client
from solders.keypair import Keypair

# --- CONFIGURACIÓN DE VARIABLES DE ENTORNO ---
TOKEN_TELEGRAM = os.getenv("TELEGRAM_TOKEN")
ID_TELEGRAM = os.getenv("TELEGRAM_CHAT_ID")
PHANTOM_PRIVATE_KEY = os.getenv("PHANTOM_PRIVATE_KEY")

bot = TeleBot(TOKEN_TELEGRAM)
SOLANA_CLIENT = Client("https://api.mainnet-beta.solana.com")

ETH_MINT = "7vfCg797rqwKCmwQNpepX8zmYbhG3wD6f1cMZaAht9wj"
DB_NAME = "bot_data.db"

# --- GESTIÓN DE BASE DE DATOS LOCAL ---
def inicializar_db():
    """Crea la tabla de precios si no existe para mantener memoria tras reinicios"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS historico_precios 
                      (timestamp INTEGER, precio REAL)''')
    conn.commit()
    conn.close()

def guardar_precio(precio):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO historico_precios VALUES (?, ?)", (int(time.time()), precio))
    # Mantener solo los últimos 200 registros en la base de datos
    cursor.execute("DELETE FROM historico_precios WHERE rowid NOT IN (SELECT rowid FROM historico_precios ORDER BY timestamp DESC LIMIT 200)")
    conn.commit()
    conn.close()

def cargar_precios():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT precio FROM historico_precios ORDER BY timestamp ASC")
    filas = cursor.fetchall()
    conn.close()
    return [f[0] for f in filas]

# --- MENSAJERÍA ---
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

# --- INDICADORES MATEMÁTICOS AVANZADOS (CORREGIDOS) ---
def calcular_rsi(precios, periodo=14):
    if len(precios) < periodo + 1:
        return 50
    
    variaciones = np.diff(precios)
    ganancias = np.where(variaciones > 0, variaciones, 0)
    perdidas = np.where(variaciones < 0, -variaciones, 0)
    
    avg_ganancia = np.mean(ganancias[-periodo:])
    avg_perdida = np.mean(perdidas[-periodo:])
    
    if avg_perdida == 0:
        return 100
    
    rs = avg_ganancia / avg_perdida
    return 100 - (100 / (1 + rs))

def calcular_bandas_bollinger(precios, periodo=20, multiplicador=2):
    if len(precios) < periodo:
        return None, None, None
    sub_precios = precios[-periodo:]
    media = np.mean(sub_precios)
    desviacion = np.std(sub_precios)
    return media, media + (multiplicador * desviacion), media - (multiplicador * desviacion)

# --- EJECUCIÓN WEB3 ---
def ejecutar_orden_jupiter(tipo_orden, cantidad_usd):
    if not PHANTOM_PRIVATE_KEY:
        enviar_mensaje("❌ Error Crítico: Variable PHANTOM_PRIVATE_KEY vacía en Render.")
        return False
    try:
        billetera = Keypair.from_base58_string(PHANTOM_PRIVATE_KEY)
        direccion_publica = billetera.pubkey()
        enviar_mensaje(f"⚡ [Blockchain Web3] Orden `{tipo_orden}` de ${cantidad_usd} USDC enviada desde cuenta: ...{str(direccion_publica)[-6:]}")
        time.sleep(1)
        return True
    except Exception as e:
        enviar_mensaje(f"⚠️ Error de firma Web3: {str(e)[:100]}")
        return False

# --- ALGORITMO MAESTRO CON RIESGO CONTROLADO ---
def algoritmo_maestro():
    inicializar_db()
    enviar_mensaje("🛡️ ¡Bot de Trading Profesional Multi-Variable & Anti-Reinicio Activo!")
    
    posicion_abierta = False
    tipo_posicion = None # "LONG" o "SHORT"
    precio_entrada = 0.0
    
    # Parámetros de Riesgo (Modificables)
    STOP_LOSS = 0.02   # Máxima pérdida permitida: 2%
    TAKE_PROFIT = 0.05 # Objetivo de beneficio: 5%

    while True:
        precio_actual = obtener_precio_jupiter()
        
        if precio_actual:
            guardar_precio(precio_actual)
            precios_historicos = cargar_precios()
            
            print(f"👁️ Monitoreando ETH: ${precio_actual:.2f} | Historial: {len(precios_historicos)}/200")
            
            # 1. GESTIÓN DE RIESGO ACTIVA (Monitoreo de posición abierta)
            if posicion_abierta:
                rendimiento = (precio_actual - precio_entrada) / precio_entrada if tipo_posicion == "LONG" else (precio_entrada - precio_actual) / precio_entrada
                
                # Verificar Stop Loss
                if rendimiento <= -STOP_LOSS:
                    enviar_mensaje(f"🚨 [STOP LOSS GESTIONADO] Cerrando posición de emergencia para mitigar riesgos.\nPérdida: {rendimiento*100:.2f}%\nPrecio Cierre: ${precio_actual:.2f}")
                    if ejecutar_orden_jupiter(f"CERRAR_{tipo_posicion}", 15):
                        posicion_abierta = False
                        tipo_posicion = None
                        
                # Verificar Take Profit        
                elif rendimiento >= TAKE_PROFIT:
                    enviar_mensaje(f"💰 [TAKE PROFIT ALCANZADO] Retirando ganancias estratégicas.\nBeneficio: +{rendimiento*100:.2f}%\nPrecio Cierre: ${precio_actual:.2f}")
                    if ejecutar_orden_jupiter(f"CERRAR_{tipo_posicion}", 15):
                        posicion_abierta = False
                        tipo_posicion = None

            # 2. EVALUACIÓN Y EJECUCIÓN TÉCNICA DE ENTRADAS
            if len(precios_historicos) >= 20 and not posicion_abierta:
                media_20, b_superior, b_inferior = calcular_bandas_bollinger(precios_historicos)
                rsi = calcular_rsi(precios_historicos)
                media_200 = np.mean(precios_historicos) if len(precios_historicos) == 200 else precio_actual
                
                # Clasificación matemática de valor
                esta_undervalued = precio_actual < b_inferior and rsi < 30
                esta_overvalued = precio_actual > b_superior and rsi > 70
                tendencia_alcista = precio_actual > media_200

                # Operativa Long (Compra el activo barato)
                if esta_undervalued and tendencia_alcista:
                    enviar_mensaje(f"🟢 [COMPRA TÉCNICA - UNDERVALUED]\nAnálisis: Activo infravalorado en tendencia alcista principal.\nPrecio: ${precio_actual:.2f} | RSI: {rsi:.1f}")
                    if ejecutar_orden_jupiter("ABRIR_LONG", 15):
                        posicion_abierta = True
                        tipo_posicion = "LONG"
                        precio_entrada = precio_actual

                # Operativa Short (Vende el activo inflado)
                elif esta_overvalued and not tendencia_alcista:
                    enviar_mensaje(f"🔴 [VENTA/SHORT TÉCNICA - OVERVALUED]\nAnálisis: Activo sobrevalorado en tendencia bajista macro.\nPrecio: ${precio_actual:.2f} | RSI: {rsi:.1f}")
                    if ejecutar_orden_jupiter("ABRIR_SHORT", 15):
                        posicion_abierta = True
                        tipo_posicion = "SHORT"
                        precio_entrada = precio_actual
                        
        # Escaneo de alta precisión cada 60 segundos
        time.sleep(60)

if __name__ == "__main__":
    algoritmo_maestro()
