from machine import Pin
import time

# Sur la Heltec WiFi LoRa 32 V3 (HTIT-WB32LAF), 
# la LED utilisateur est sur le GPIO 35.
led_pin = 35

# Configuration de la broche en sortie
led = Pin(led_pin, Pin.OUT)

print("Lancement du script sur Heltec V3...")

try:
    while True:
        led.value(1)            # Allume la LED
        print("LED Allumée")
        time.sleep(0.5)         # Attend 500ms
        
        led.value(0)            # Éteint la LED
        print("LED Éteinte")
        time.sleep(0.5)         # Attend 500ms
except KeyboardInterrupt:
    # Arrêt propre si vous pressez Ctrl+C dans Thonny
    led.value(0)
    print("Programme arrêté.")