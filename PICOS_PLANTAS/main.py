# main.py - Script avanzado para Pico W con ADS1115, validación estadística y autocalibración
import machine
import time
import ujson
import math
import urequests
import network
from simple import MQTTClient
from ads1x15 import ADS1115 # Driver que hemos subido
from ota_updater import OTAUpdater # NUEVO: Importamos la librería de actualización

# --- CONFIGURACIÓN ESPECÍFICA DE ESTE PICO ---
PICO_ID = "1" # ¡¡CAMBIAR PARA CADA PICO!! "1", "2", "3", etc.

# --- CONFIGURACIÓN GENERAL ---
WIFI_SSID = "AMBE"
WIFI_PASS = "Ganuza210966"
MQTT_BROKER = "192.168.68.107" # IP de la Raspberry Pi 5
CONFIG_FILE = "config.json"
MAIN_LOOP_INTERVAL_S = 15 # 300 seg.=5 minutos / pongo 60 seg=1 minu

# --- NUEVO: Temas MQTT ---
TOPIC_DATA = f"planta/{PICO_ID}/data"
TOPIC_RIEGO = f"planta/{PICO_ID}/riego"
TOPIC_ADMIN = f"planta/{PICO_ID}/admin" # NUEVO: Tema para comandos administrativos

# --- CONFIGURACIÓN DE TELEGRAM ---
TELEGRAM_BOT_TOKEN = "8290589551:AAFO0Ya0Xj_PERXtNHLgoDeZEoLwFRip47A"
TELEGRAM_CHAT_ID = "1413941022"

# --- NUEVO: CONFIGURACIÓN OTA DESDE GITHUB ---
# Reemplaza 'tu-usuario' y 'tu-repositorio' con los tuyos
#GITHUB_REPO_URL = "https://api.github.com/repos/tu-usuario/tu-repositorio/contents/"
GITHUB_REPO_URL = "https://github.com/aabion/pico-ota/"

# Lista de ficheros que el actualizador OTA debe gestionar
OTA_FILES = ['main.py'] 

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

# --- NUEVAS FUNCIONES Y FUNCIONES MODIFICADAS ---
def get_telegram_updates_and_check_command():
    """Obtiene el último mensaje de Telegram y comprueba si es un comando de actualización."""
    global telegram_last_update_id
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates?offset={telegram_last_update_id + 1}&limit=1"
    
    try:
        response = urequests.get(url, timeout=10)
        data = response.json()
        response.close()

        if data['ok'] and data['result']:
            update = data['result'][0]
            telegram_last_update_id = update['update_id']
            message_text = update['message']['text'].upper()

            # Lógica para que cualquier Pico se actualice con el comando "ACTUALIZAR"
            if message_text == "ACTUALIZAR":
                print(f"¡Comando de actualización recibido para todos los Picos! (ID: {PICO_ID})")
                send_telegram_message(f"Pico {PICO_ID}: OK, iniciando proceso de actualización desde GitHub...")
                print("Actualización descargada. Reiniciando en 3 segundos...")
                time.sleep(3)
                machine.reset()
                #perform_ota_update()
    except Exception as e:
        print(f"No se pudo comprobar Telegram o comando inválido: {e}")
        
def perform_ota_update():
    """Usa la librería OTA para descargar e instalar actualizaciones desde GitHub."""
    #try:
        # Pasa una cadena vacía para github_src_dir si los archivos están en la raíz.
        # El argumento main_dir='main' le dice dónde guardar la nueva versión,
        # lo que es útil si el script principal está en la raíz.
    ota_updater = OTAUpdater(GITHUB_REPO_URL, github_src_dir='PICOS_PLANTAS')
    
    update_available = ota_updater.install_update_if_available()
    #print(update_available)
    
    if update_available:
        send_telegram_message(f"Pico {PICO_ID}: Actualización de main.py completada. Reiniciando ahora.")
        print("Actualización descargada. Reiniciando en 3 segundos...")
        time.sleep(3)
        machine.reset()
    else:
        send_telegram_message(f"Pico {PICO_ID}: Ya estoy en la última versión. No se requiere actualización.")
        print("Ya en la última versión.")
    '''        
    except Exception as e:
        send_telegram_message(f"Pico {PICO_ID}: ¡ERROR durante la actualización OTA! {e}")
        print(f"Error OTA: {e}")
    '''
# --- MODIFICADO: La función on_message ahora maneja múltiples temas ---
def on_message(topic, msg):
    """Se ejecuta cuando llega un mensaje de la Pi 5 en CUALQUIER tema suscrito."""
    # Decodificamos el tema y el mensaje para poder compararlos
    topic_str = topic.decode()
    comando = msg.decode()
    
    print(f"Comando '{comando}' recibido en el tema '{topic_str}'")

    # Lógica para el tema de RIEGO
    if topic_str == TOPIC_RIEGO:
        if comando == "REGAR":
            print("Activando riego por 5 segundos...")
            # ... (código para activar el relé de la bomba) ...
            print("Riego finalizado.")
    
    # NUEVA LÓGICA: para el tema de ADMIN
    elif topic_str == TOPIC_ADMIN:
        if comando == "ACTUALIZAR":
            print("¡Comando de reinicio recibido! Reiniciando en 3 segundos...")
            send_telegram_message(f"Pico {PICO_ID}: Recibido. Reiniciando ahora.")
            time.sleep(3)
            machine.reset() # ¡La magia ocurre aquí!

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
            measurements.append(ads.read(ADS_CHANNEL))
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
mqtt_client.set_callback(on_message)
mqtt_client.connect()
print("Conectado a MQTT.")

# Nos suscribimos a AMBOS temas: el de riego y el nuevo de administración
mqtt_client.subscribe(TOPIC_RIEGO)
mqtt_client.subscribe(TOPIC_ADMIN)
print(f"Suscrito a los temas: {TOPIC_RIEGO} y {TOPIC_ADMIN}")

# 3. Bucle infinito de medición y envío
while True:
    # 3.1: Medir y enviar datos a la Pi 5 vía MQTT
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

    # 3.2: NUEVO - Comprobar si hay comandos de actualización en Telegram
    print("Comprobando comandos de actualización en Telegram...")
    get_telegram_updates_and_check_command()
    
    # 3.3: Esperar para el siguiente ciclo
    print(f"Ciclo completado. Durmiendo por {MAIN_LOOP_INTERVAL_S} segundos.")
    time.sleep(MAIN_LOOP_INTERVAL_S)
