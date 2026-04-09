from machine import Pin, I2C
import bme280
import time

# --- Configuration ---
i2c = I2C(0, scl=Pin(44), sda=Pin(43), freq=10000)
time.sleep(0.5)

# Pression standard au niveau de la mer en hPa (ajustable selon la météo locale)
P0 = 1022

sensor = None
try:
    sensor = bme280.BME280(i2c=i2c, address=0x76)
    time.sleep(0.2)
    _ = sensor.values 
    print("Capteur BME280 prêt !")
except Exception as e:
    time.sleep(0.5)

def calculer_altitude(pression_hpa):
    # Formule barométrique internationale
    altitude = 44330 * (1 - (pression_hpa / P0)**(1/5.255))
    return altitude

def extraire_valeur(donnee_str):
    # Nettoie la chaîne (ex: "1015.2hPa" -> 1015.2)
    return float(''.join(c for c in donnee_str if c.isdigit() or c == '.'))

def lire_meteo():
    if sensor is None: return

    while True:
        try:
            # Récupération des valeurs brutes (souvent des strings selon la lib)
            t_str, p_str, h_str = sensor.values
            
            # Conversion en nombres
            pression = extraire_valeur(p_str)
            altitude = calculer_altitude(pression)
            
            print("-" * 25)
            print(f"Température : {t_str}")
            print(f"Pression    : {pression:.2f} hPa")
            print(f"Humidité    : {h_str}")
            print(f"Altitude est.: {altitude:.2f} m")
            
        except Exception as e:
            print("Erreur de lecture :", e)
            
        time.sleep(0.2)

#if sensor:
print("Démarrage des mesures avec calcul d'altitude...")
lire_meteo()