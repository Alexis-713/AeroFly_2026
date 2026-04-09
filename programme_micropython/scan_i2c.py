from machine import Pin, I2C

# Configuration du bus I2C (on baisse un peu la fréquence pour plus de stabilité)
i2c = I2C(0, sda=Pin(43), scl=Pin(44), freq=100000)

print("Scan du bus I2C en cours...")
appareils = i2c.scan()

if len(appareils) == 0:
    print("Oups ! Aucun périphérique I2C trouvé.")
    print("C'est probablement un problème de câblage ou d'alimentation.")
else:
    print(f"{len(appareils)} périphérique(s) trouvé(s) :")
    for appareil in appareils:
        print(f" - Adresse décimale : {appareil} | Adresse hexadécimale : {hex(appareil)}")