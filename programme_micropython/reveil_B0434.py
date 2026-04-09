from machine import Pin, SPI
import time

cs = Pin(39, Pin.OUT, value=1)
# On descend la vitesse à 10kHz (très lent) pour éliminer les problèmes de câbles
spi = SPI(2, baudrate=10000, sck=Pin(40), mosi=Pin(42), miso=Pin(41))

def read_id():
    cs.value(0)
    spi.write(bytearray([0x40])) # Registre ID sur Mega
    val = spi.read(1)[0]
    cs.value(1)
    return val

print("--- Test de réveil ---")
for i in range(5):
    print(f"Essai {i+1} - ID reçu: {hex(read_id())}")
    time.sleep(0.5)