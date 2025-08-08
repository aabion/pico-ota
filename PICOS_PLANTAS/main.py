from machine import Pin
import time

# Asigna el pin del LED integrado a una variable.
# En la Raspberry Pi Pico, el LED integrado está conectado al pin GPIO 25.
led = Pin("LED", Pin.OUT)

# Bucle infinito para alternar el estado del LED.
# Presiona Ctrl+C en tu terminal para detener el script.
while True:
    # Enciende el LED.
    led.value(1) 
    print("LED encendido")
    time.sleep(5)  # Espera 0.5 segundos.

    # Apaga el LED.
    led.value(0)
    print("LED apagado")
    time.sleep(5)  # Espera 0.5 segundos.
