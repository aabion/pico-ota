# boot.py - Script de actualización OTA
# Se ejecuta en cada arranque para comprobar si hay una nueva versión de main.py

import machine
import network
import urequests
import os
import time

# --- CONFIGURACIÓN DEL USUARIO ---
WIFI_SSID = "AMBE"
WIFI_PASSWORD = "Ganuza210966"

# URL al archivo "raw" de tu main.py en GitHub
# ¡¡REEMPLAZA ESTA URL CON LA TUYA!!
OTA_URL = "https://raw.githubusercontent.com/aabion/pico-ota/refs/heads/main/main.py"

# --- LÓGICA DEL SCRIPT ---

def conectar_wifi():
    """Se conecta a la red WiFi configurada."""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print('Conectando a la red WiFi...')
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        # Espera a la conexión
        max_wait = 10
        while max_wait > 0:
            if wlan.status() < 0 or wlan.status() >= 3:
                break
            max_wait -= 1
            print('.', end='')
            time.sleep(1)

    if wlan.isconnected():
        print('\nConexión exitosa. IP:', wlan.ifconfig()[0])
        return True
    else:
        print('\nFallo al conectar.')
        return False

def check_for_updates():
    """Comprueba si hay una nueva versión de main.py, la descarga y reinicia."""
    print("Buscando actualizaciones desde:", OTA_URL)
    
    try:
        # Hacemos la petición para obtener el nuevo código
        respuesta = urequests.get(OTA_URL)
        
        if respuesta.status_code == 200:
            print("Nueva versión encontrada. Descargando...")
            
            # Guardamos el nuevo código en un archivo temporal
            with open('main_new.py', 'w') as f:
                f.write(respuesta.text)
            
            # Cerramos la respuesta para liberar memoria
            respuesta.close()
            
            # Verificamos si el archivo temporal se creó
            # 'os.stat' nos da información del archivo, si no existe, da error.
            stat_info = os.stat('main_new.py')
            
            if stat_info.st_size > 0:
                print(f"Descarga completada ({stat_info.st_size} bytes).")
                
                # Renombramos el main.py actual a main.py.bak (como backup)
                if 'main.py' in os.listdir():
                    os.rename('main.py', 'main.py.bak')
                    print("Backup 'main.py.bak' creado.")
                
                # Renombramos el nuevo archivo a main.py
                os.rename('main_new.py', 'main.py')
                print("Actualización instalada. Reiniciando el dispositivo...")
                time.sleep(1)
                machine.reset() # Reinicia la Pico para ejecutar el nuevo main.py
            else:
                print("La descarga falló (archivo vacío). Se aborta la actualización.")
                os.remove('main_new.py')

        else:
            print(f"No se pudo descargar el archivo. Código de estado: {respuesta.status_code}")
            respuesta.close()
            
    except Exception as e:
        print(f"Fallo en el proceso OTA: {e}")

# --- EJECUCIÓN ---

if conectar_wifi():
    check_for_updates()

# Al finalizar, MicroPython ejecutará automáticamente main.py
print("No hay actualizaciones o fallo en la conexión. Ejecutando main.py existente...")