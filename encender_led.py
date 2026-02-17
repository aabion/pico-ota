import machine
import time

# Configuramos el pin del LED interno como salida
led = machine.Pin("LED", machine.Pin.OUT)

# Bucle infinito para parpadear
while True:
    led.toggle()      # Cambia el estado (si está encendido lo apaga y viceversa)
    time.sleep(1)     # Espera 1 segundo