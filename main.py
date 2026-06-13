import json
import urllib.parse
import urllib.request

# --- CONFIGURACIÓN DEL BOT (Pon tus datos reales) ---
TELEGRAM_TOKEN = "TU_TOKEN_DE_BOTFATHER"
CHAT_ID = "TU_CHAT_ID_NUMERICO"
SIMBOLO = "ETHUSDC"

# Para un Cron Job, leemos el histórico directamente de la API de Binance
# para calcular las medias móviles al instante sin guardar datos en el servidor.
VENTANA_CORTA = 20
VENTANA_LARGA = 50


def enviar_mensaje_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={CHAT_ID}&text={urllib.parse.quote(mensaje)}"
    try:
        urllib.request.urlopen(url)
    except Exception as e:
        print(f"Error enviando a Telegram: {e}")


def calcular_estrategia():
    # Descargamos las últimas 60 velas de 1 minuto de Binance de forma nativa
    url = f"https://api.binance.us/api/v3/klines?symbol={SIMBOLO}&interval=1m&limit=60"
    try:
        response = urllib.request.urlopen(url)
        velas = json.loads(response.read().decode())

        # Extraemos los precios de cierre (posición 4 en la respuesta de Binance)
        precios = [float(vela[4]) for vela in velas]
        precio_actual = precios[-1]

        # Calculamos las medias aritméticas
        media_corta = sum(precios[-VENTANA_CORTA:]) / VENTANA_CORTA
        media_larga = sum(precios[-VENTANA_LARGA:]) / VENTANA_LARGA

        print(
            f"Precio: ${precio_actual:.2f} | SMA20: ${media_corta:.2f} | SMA50: ${media_larga:.2f}"
        )

        # Lógica de aviso
        if media_corta > media_larga:
            # Mandamos un mensaje notificando que el activo está subestimado y en tendencia alcista
            enviar_mensaje_telegram(
                f"🟢 [COMPRA TÉCNICA] {SIMBOLO} en tendencia alcista. Precio: ${precio_actual:.2f}."
            )
        elif media_corta < media_larga:
            enviar_mensaje_telegram(
                f"🔴 [VENTA TÉCNICA] {SIMBOLO} en tendencia bajista. Precio: ${precio_actual:.2f}."
            )

    except Exception as e:
        print(f"Error en el cálculo: {e}")


if __name__ == "__main__":
    calcular_estrategia()
