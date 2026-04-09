from machine import Pin, I2C
import bme280
import time

# 1. Configuration de l'I2C (Adapté pour ESP32, changez les pins pour Pico)
# Sur Raspberry Pi Pico : I2C(0, scl=Pin(9), sda=Pin(8))
i2c = I2C(0, scl=Pin(44), sda=Pin(43), freq=10000) # Passage à 10kHz pour tester
time.sleep(0.5) # Laisser le temps au bus de se stabiliser

# 2. Initialisation du capteur
# Note : L'adresse est souvent 0x76 ou 0x77
try:
    sensor = bme280.BME280(i2c=i2c, address=0x76)
except Exception as e:
    print("Erreur d'initialisation :", e)

def lire_meteo():
    while True:
        try:
            # Lecture des valeurs
            temp, press, hum = sensor.values
            # Affichage formaté
            print("-" * 20)
            print(f"Température : {temp}")
            print(f"Pression    : {press}")
            print(f"Humidité    : {hum}")  
        except Exception as e:
            print("Erreur de lecture :", e)           
        time.sleep(2) # Attendre 2 secondes entre chaque mesure



# Lancement du programme
print("Démarrage des mesures...")
lire_meteo()