from machine import Pin, I2C
import time
import math

# --- Configuration ---
# I2C sur SDA=12 et SCL=13
i2c = I2C(0, sda=Pin(43), scl=Pin(44), freq=100000) 
MS4525DO_ADDR = 0x28  # Modifiez ici si votre adresse est différente (ex: 0x36, 0x46)

# Constantes du capteur et de l'air
P_MIN = -1.0          # Pression minimum en PSI
P_MAX = 1.0           # Pression maximum en PSI
PSI_TO_PA = 6894.757  # Conversion PSI -> Pascals
RHO = 1.225           # Masse volumique de l'air (kg/m3)

def lire_capteur_ms4525do():
    """Lit le capteur et retourne la pression brute en Pascals et la température en °C"""
    try:
        data = i2c.readfrom(MS4525DO_ADDR, 4)
        status = (data[0] & 0xC0) >> 6
        
        if status == 2 or status == 3:
            return None, None
            
        # Pression (14 bits)
        p_raw = ((data[0] & 0x3F) << 8) | data[1]
        p_psi = ((p_raw - 1638.3) / 13107.0) * (P_MAX - P_MIN) + P_MIN
        p_pa = -(p_psi * PSI_TO_PA)
        
        # Température (11 bits)
        t_raw = (data[2] << 3) | ((data[3] & 0xE0) >> 5)
        t_celsius = (t_raw / 2047.0) * 200.0 - 50.0
        
        return p_pa, t_celsius

    except OSError:
        return None, None
    except Exception as e:
        return None, None

def calibrer_capteur(nb_lectures=200):
    """Effectue l'Auto-Zéro en prenant plusieurs mesures au repos"""
    print(f"\n--- DÉBUT DE LA CALIBRATION ({nb_lectures} mesures) ---")
    print("ATTENTION : Ne touchez pas au tube de Pitot et couvrez-le s'il y a du vent !")
    
    somme_pression = 0.0
    lectures_valides = 0
    
    for i in range(nb_lectures):
        p, t = lire_capteur_ms4525do()
        if p is not None:
            somme_pression += p
            lectures_valides += 1
            # Affiche une petite barre de progression dans la console
            print(".", end="")
        time.sleep(0.05) # Pause de 50ms entre chaque mesure
        
    print("\n") # Retour à la ligne
    
    if lectures_valides > 0:
        offset = somme_pression / lectures_valides
        print(f"--- CALIBRATION TERMINÉE ---")
        print(f"Offset calculé : {offset:.2f} Pa (Sera soustrait des futures mesures)\n")
        return offset
    else:
        print("ÉCHEC DE LA CALIBRATION : Impossible de lire le capteur.")
        return 0.0

# ==========================================
#             PROGRAMME PRINCIPAL
# ==========================================

print("Démarrage du système Pitot...")
time.sleep(1) # Laisse le temps au capteur de s'allumer correctement

# 1. On lance l'Auto-Zéro au démarrage
offset_pression = calibrer_capteur(50) 

# 2. Boucle principale de mesure
print("Prêt pour la mesure de vitesse ! (Appuyez sur Ctrl+C pour arrêter)")

try:
    while True:
        p_brute, temperature = lire_capteur_ms4525do()
        
        if p_brute is not None:
            # On applique la calibration : on soustrait l'erreur mesurée au démarrage
            p_calibree = p_brute - offset_pression
            
            # On ignore les valeurs négatives dues au bruit résiduel du capteur
            if p_calibree < 0:
                p_calibree = 0.0
                
            # Calcul de la vitesse (Formule de Bernoulli)
            vitesse_ms = math.sqrt((2 * p_calibree) / RHO)
            vitesse_kmh = vitesse_ms * 3.6
            
            # Affichage formaté
            print(f"Pression: {p_calibree:6.2f} Pa | Temp: {temperature:5.1f} °C | Vitesse: {vitesse_ms:5.2f} m/s ({vitesse_kmh:5.1f} km/h)")
        else:
            print("Erreur de lecture du capteur...")
            
        time.sleep(1) # 10 lectures par seconde
        
except KeyboardInterrupt:
    print("\nProgramme arrêté.")