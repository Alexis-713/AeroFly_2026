from machine import Pin, I2C
import time

# Initialisation I2C sur les pins
i2c1 = I2C(0, scl=Pin(33), sda=Pin(34), freq=10000)
i2c2 = I2C(0, scl=Pin(4), sda=Pin(5), freq=100000)
i2c3 = I2C(0, scl=Pin(47), sda=Pin(48), freq=100000)

print("Scan I2C en cours...")
devices1 = i2c1.scan()
devices2 = i2c2.scan()
devices3 = i2c3.scan()
while True:
    if devices1:
        print("Périphériques trouvés :")
        for addr in devices1:
            print("Adresse1:", hex(addr))
    else:
        print("Aucun périphérique trouvé1")
    
    if devices2:
        print("Périphériques trouvés :")
        for addr in devices2:
            print("Adresse2:", hex(addr))
    else:
        print("Aucun périphérique trouvé2")
        
    if devices3:
        print("Périphériques trouvés :")
        for addr in devices3:
            print("Adresse3:", hex(addr))
    else:
        print("Aucun périphérique trouvé3")
    
    time.sleep(1)