from machine import Pin, I2C
import time
from pitot import PitotMS4525DO
from meteo import CapteurMeteo

# 1. Initialisation matérielle (Bus I2C partagé)
print("Initialisation du bus I2C...")
bus_i2c = I2C(0, sda=Pin(43), scl=Pin(44), freq=100000)

# --- Optionnel mais recommandé : Scan du bus au démarrage ---
appareils = bus_i2c.scan()
print(f"I2C Scan : {len(appareils)} appareil(s) trouvé(s) -> {[hex(a) for a in appareils]}")

# 2. Création des objets (Instanciation des classes)
print("\nConfiguration des capteurs...")
capteur_pitot = PitotMS4525DO(i2c=bus_i2c, adresse=0x28)
capteur_bme = CapteurMeteo(i2c=bus_i2c, adresse=0x76, p0=1020)

# 3. Phase de Calibration
time.sleep(1) # Laisse le temps aux capteurs de s'allumer
capteur_pitot.calibrer(nb_lectures=50)

print("\n--- SYSTÈME PRÊT ---")
print("Appuyez sur Ctrl+C pour stopper.\n")

# 4. Boucle principale de vol
try:
    while True:
        # Récupération des données via nos objets
        donnees_pitot = capteur_pitot.lire_vitesse()
        donnees_meteo = capteur_bme.lire_donnees()
        
        # Affichage Console
        print("=" * 40)
        
        if donnees_pitot:
            print(f"VIT: {donnees_pitot['vitesse_kmh']:5.1f} km/h | Pdyn: {donnees_pitot['pression_pa']:6.1f} Pa")
        else:
            print("Erreur Pitot")
            
        if donnees_meteo:
            print(f"ALT: {donnees_meteo['altitude_m']:5.1f} m    | Psta: {donnees_meteo['pression_hpa']:6.1f} hPa")
            print(f"TMP: {donnees_meteo['temperature_str']}  | HUM : {donnees_meteo['humidite_str']}")
        else:
            print("Erreur BME280")
            
        # Pause de 200ms (5 Hz) pour ne pas saturer la console
        time.sleep(0.2)
        
except KeyboardInterrupt:
    print("\nArrêt du programme.")