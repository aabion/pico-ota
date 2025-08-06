# main.py - Script avanzado para Pico W con ADS1115, validación estadística y autocalibración

import machine
import time
import ujson
import math
import urequests
from umqtt.simple import MQTTClient
from ads1x15 import ADS1115 # Driver que hemos subido

# --- CONFIGURACIÓN ESPECÍFICA DE ESTE PICO ---
PICO_ID = "1" # ¡¡CAMBIAR PARA CADA PICO!! "1", "2", "3", etc.

# --- CONFIGURACIÓN GENERAL ---
WIFI_SSID = "TuNombreDeRedWiFi"
WIFI_PASS = "TuContraseñaWiFi"
MQTT_BROKER = "192.168.1.100" # IP de la Raspberry Pi 5
CONFIG_FILE = "config.json"
MAIN_LOOP_INTERVAL_S = 300 # 300s = 5 minutos

# --- CONFIGURACIÓN DE TELEGRAM ---
TELEGRAM_BOT_TOKEN = "TOKEN_DE_TU_BOT" # Pega aquí tu Token
TELEGRAM_CHAT_ID = "ID_DE_TU_CHAT"     # Pega aquí tu Chat ID

# --- CONFIGURACIÓN DEL SENSOR ADS1115 ---
I2C_BUS = 0
I2C_SCL_PIN = 5
I2C_SDA_PIN = 4
ADS_CHANNEL = 0 # Sensor conectado al canal A0
# El GAIN ajusta el rango de voltaje. GAIN=1 es para +/-4.096V. Perfecto para sensores de 3.3V.
ADS_GAIN = 1 

# --- Inicialización de objetos ---
i2c = machine.I2C(I2C_BUS, scl=machine.Pin(I2C_SCL_PIN), sda=machine.Pin(I2C_SDA_PIN))
ads = ADS1115(i2c, gain=ADS_GAIN)
config_data = {}
telegram_last_update_id = 0

# --- FUNCIONES AUXILIARES ---

def calculate_stats(measurements):
    """Calcula la media y la desviación estándar de una lista de números."""
    n = len(measurements)
    if n == 0:
        return 0, 0
    mean = sum(measurements) / n
    variance = sum([(x - mean) ** 2 for x in measurements]) / n
    std_dev = math.sqrt(variance)
    return mean, std_dev

def send_telegram_message(message):
    """Envía un mensaje al chat de Telegram configurado."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {'chat_id': TELEGRAM_CHAT_ID, 'text': message}
    try:
        print(f"Enviando a Telegram: {message}")
        response = urequests.post(url, json=payload)
        response.close()
        return True
    except Exception as e:
        print(f"Error enviando a Telegram: {e}")
        return False

def get_telegram_updates():
    """Obtiene el último mensaje del chat de Telegram."""
    global telegram_last_update_id
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates?offset={telegram_last_update_id + 1}&limit=1"
    try:
        response = urequests.get(url, timeout=5)
        data = response.json()
        response.close()
        if data['ok'] and data['result']:
            telegram_last_update_id = data['result'][0]['update_id']
            message_text = data['result'][0]['message']['text']
            return message_text
        return None
    except Exception as e:
        print(f"Error obteniendo updates de Telegram: {e}")
        return None

def check_or_request_config():
    """Carga la configuración o inicia el proceso interactivo para crearla."""
    global config_data
    try:
        with open(CONFIG_FILE, 'r') as f:
            config_data = ujson.load(f)
        if 'seco_raw' not in config_data or 'humedo_raw' not in config_data:
            raise ValueError("Faltan claves de configuración")
        print("Configuración cargada con éxito.")
        return True
    except (OSError, ValueError) as e:
        print(f"No se pudo cargar la configuración ({e}). Iniciando calibración interactiva...")
        config_data = {}
        
        # Pedir valor en SECO
        send_telegram_message(f"Planta {PICO_ID} necesita calibración.\n\nPor favor, introduce el valor del sensor en TIERRA COMPLETAMENTE SECA y responde solo con el número.")
        while 'seco_raw' not in config_data:
            print("Esperando valor en SECO...")
            msg = get_telegram_updates()
            if msg and msg.isdigit():
                config_data['seco_raw'] = int(msg)
                send_telegram_message(f"OK. Valor en SECO guardado: {msg}")
            time.sleep(5)
            
        # Pedir valor en HÚMEDO
        send_telegram_message(f"Ahora, introduce el valor del sensor en TIERRA COMPLETAMENTE MOJADA (saturada de agua).")
        while 'humedo_raw' not in config_data:
            print("Esperando valor en HÚMEDO...")
            msg = get_telegram_updates()
            if msg and msg.isdigit():
                config_data['humedo_raw'] = int(msg)
                send_telegram_message(f"OK. Valor en HÚMEDO guardado: {msg}")
            time.sleep(5)
            
        # Guardar configuración en el fichero
        with open(CONFIG_FILE, 'w') as f:
            ujson.dump(config_data, f)
        send_telegram_message(f"¡Planta {PICO_ID} calibrada y lista! El sistema se iniciará ahora.")
        print("Calibración completada.")
        return True

def get_stable_reading():
    """Realiza la lógica de medición y validación estadística."""
    MAX_TRIES = 5
    for attempt in range(MAX_TRIES):
        print(f"Intento de medición {attempt + 1}/{MAX_TRIES}...")
        measurements = []
        for _ in range(25):
            measurements.append(ads.read(channel=ADS_CHANNEL))
            time.sleep_ms(250)
            
        mean, std_dev = calculate_stats(measurements)
        
        if mean == 0: continue # Evitar división por cero

        deviation_percent = (std_dev / mean) * 100
        print(f"  Media: {mean:.2f}, Desv. Est.: {std_dev:.2f} ({deviation_percent:.2f}%)")
        
        if deviation_percent <= 1.0:
            print("Medición estable obtenida.")
            return mean
    
    print("No se pudo obtener una medición estable.")
    return None

def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print('Conectando a WiFi...')
        wlan.connect(WIFI_SSID, WIFI_PASS)
        while not wlan.isconnected():
            time.sleep(1)
    print('WiFi Conectado! IP:', wlan.ifconfig()[0])
    
# --- PROGRAMA PRINCIPAL ---

# 1. Calibración inicial (si es necesaria)
check_or_request_config()

# 2. Conexión a la red
connect_wifi()
mqtt_client = MQTTClient(f"pico_planta_{PICO_ID}", MQTT_BROKER)
mqtt_client.connect()
print("Conectado a MQTT.")

# 3. Bucle infinito de medición y envío
while True:
    print(f"\n--- Iniciando nuevo ciclo de medición ({time.ticks_ms()}) ---")
    
    valor_crudo = get_stable_reading()
    
    if valor_crudo is None:
        send_telegram_message(f"¡AVISO! El sensor de la Planta {PICO_ID} parece tener un problema. Lecturas inestables.")
    else:
        # Calcular valores derivados
        voltaje = ads.raw_to_v(valor_crudo)
        
        # Porcentaje basado en valor crudo (mapeo lineal)
        porc_crudo = max(0, min(100, 100 * (config_data['seco_raw'] - valor_crudo) / (config_data['seco_raw'] - config_data['humedo_raw'])))
        
        # Calcular voltajes de seco y húmedo para el mapeo por voltaje
        volt_seco = ads.raw_to_v(config_data['seco_raw'])
        volt_humedo = ads.raw_to_v(config_data['humedo_raw'])
        
        porc_voltaje = max(0, min(100, 100 * (volt_seco - voltaje) / (volt_seco - volt_humedo)))
        
        # Crear el paquete de datos JSON
        payload = {
            "id": PICO_ID,
            "raw": round(valor_crudo, 2),
            "volts": round(voltaje, 4),
            "percent_raw": round(porc_crudo, 2),
            "percent_v": round(porc_voltaje, 2)
        }
        
        # Enviar por MQTT
        try:
            mqtt_client.publish(f"planta/{PICO_ID}/data", ujson.dumps(payload))
            print(f"Datos enviados a MQTT: {ujson.dumps(payload)}")
        except Exception as e:
            print(f"Error enviando a MQTT: {e}. Reconectando...")
            mqtt_client.connect() # Intento simple de reconexión

    # Esperar para el siguiente ciclo
    print(f"Ciclo completado. Durmiendo por {MAIN_LOOP_INTERVAL_S} segundos.")
    time.sleep(MAIN_LOOP_INTERVAL_S)