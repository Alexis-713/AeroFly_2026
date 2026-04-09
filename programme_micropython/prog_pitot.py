from machine import Pin, I2C
import time
import math

# Configuration du bus I2C avec SDA sur 12 et SCL sur 13
i2c = I2C(0, sda=Pin(43), scl=Pin(44), freq=100000)

# Adresse par défaut du MS4525DO
MS4525DO_ADDR = 0x28

# Constantes pour la calibration (Modèle classique 1 PSI bidirectionnel)
P_MIN = -1.0          # Pression minimum en PSI
P_MAX = 1.0           # Pression maximum en PSI
PSI_TO_PA = 6894.757  # Facteur de conversion de PSI vers Pascals
RHO = 1.225           # Masse volumique de l'air en kg/m3

def lire_capteur_ms4525do():
    """Lit le capteur et retourne la pression en Pascals et la température en °C"""
    try:
        # Le capteur renvoie 4 octets de données
        data = i2c.readfrom(MS4525DO_ADDR, 4)
        
        # Les 2 premiers bits du premier octet indiquent le statut
        status = (data[0] & 0xC0) >> 6
        
        # Statut 2 ou 3 signifie que la donnée est périmée ou en erreur
        if status == 2 or status == 3:
            return None, None
            
        # --- Extraction de la pression (14 bits) ---
        # On masque les 2 bits de statut et on combine avec le 2ème octet
        p_raw = ((data[0] & 0x3F) << 8) | data[1]
        
        # Conversion des données brutes en PSI (formule de la datasheet 10%-90%)
        # 1638 correspond à 10% de la plage, 14745 correspond à 90% (delta de 13107)
        p_psi = ((p_raw - 1638.3) / 13107.0) * (P_MAX - P_MIN) + P_MIN
        
        # Conversion en Pascals (Pression dynamique)
        p_pa = -(p_psi * PSI_TO_PA)
        
        # --- Extraction de la température (11 bits) ---
        t_raw = (data[2] << 3) | ((data[3] & 0xE0) >> 5)
        
        # Conversion en degrés Celsius (formule de la datasheet)
        t_celsius = (t_raw / 2047.0) * 200.0 - 50.0
        
        return p_pa, t_celsius

    except OSError:
        print("Erreur : Impossible de communiquer avec le capteur sur l'adresse 0x28.")
        return None, None
    except Exception as e:
        print("Erreur de lecture :", e)
        return None, None

print("Démarrage des mesures de vitesse (Pitot)...")

# Petite pause pour s'assurer que le capteur est prêt
time.sleep(1)

while True:
    pression_dyn_pa, temperature = lire_capteur_ms4525do()
    
    if pression_dyn_pa is not None:
        
        # On met la pression à 0 si elle est légèrement négative (bruit du capteur à l'arrêt)
        # Cela évite les erreurs mathématiques lors de la racine carrée
        if pression_dyn_pa < 0:
            pression_dyn_pa = 0.0
            
        # Calcul de la vitesse selon la formule de Bernoulli
        vitesse_ms = math.sqrt((2 * pression_dyn_pa) / RHO)
        
        # Conversion en km/h
        vitesse_kmh = vitesse_ms * 3.6
        
        print(f"Pression Dyn: {pression_dyn_pa:6.2f} Pa | Temp: {temperature:5.1f} °C | Vitesse: {vitesse_ms:5.2f} m/s ({vitesse_kmh:5.1f} km/h)")
    
    # Pause entre chaque lecture (20Hz max recommandé pour éviter de saturer le bus I2C)
    time.sleep(1)