# --- prog_BMEP280_complementaire --- #

from machine import Pin, I2C
import bme280
import time

# --- Configuration --- #
i2c = I2C(0, scl=Pin(48), sda=Pin(47), freq=10000)
time.sleep(0.5)

# Pression standard au niveau de la mer en hPa (ajustable selon la météo locale)
P0 = 1024

# Variables globales pour le filtre complémentaire
# altitude_filtree = 0.1
alpha = 0.1 # Facteur de lissage (0.1 = 10% de la nouvelle mesure, 90% de l'ancienne)

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
    altitude = 288.15/0.0065 * (1 - (pression_hpa / P0)**(1/5.255))
    return altitude

def extraire_valeur(donnee_str):
    # Nettoie la chaîne (ex: "1015.2hPa" -> 1015.2)
    return float(''.join(c for c in donnee_str if c.isdigit() or c == '.'))


def lire_meteo():
    if sensor is None: return
    # valeur pour avoir l'altitude a l'aide d'un filtre complémentaire
    # global altitude_filtree
    # Initialisation à la première lecture
    p_str = sensor.values[1]
    altitude_filtree = calculer_altitude(extraire_valeur(p_str))
    while True:
        try:
            # Récupération des valeurs brutes (souvent des strings selon la lib)
            t_str, p_str, h_str = sensor.values
            
            # Conversion en nombres
            pression = extraire_valeur(p_str)
            altitude = calculer_altitude(pression)
            
            # filtre complémentaire
            p_str = sensor.values[1]
            alt_brute = calculer_altitude(extraire_valeur(p_str))
            
            # Formule : Moyenne pondérée entre l'ancien et le nouveau
            altitude_filtree = (1 - alpha) * altitude_filtree + alpha * alt_brute
            
            print("-" * 25)
            print(f"Température : {t_str}")
            print(f"Pression    : {pression:.2f} hPa")
            print(f"Humidité    : {h_str}")
            print(f"Altitude est.: {altitude_filtree:.2f}m")
            
        except Exception as e:
            print("Erreur de lecture :", e)
            
        time.sleep(0.2)

print("Démarrage des mesures avec calcul d'altitude...")
lire_meteo()
