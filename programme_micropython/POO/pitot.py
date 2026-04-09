import time
import math

class PitotMS4525DO:
    def __init__(self, i2c, adresse=0x28, p_min=-1.0, p_max=1.0, rho=1.225):
        self.i2c = i2c
        self.adresse = adresse
        self.p_min = p_min
        self.p_max = p_max
        self.rho = rho
        self.psi_to_pa = 6894.757
        self.offset = 0.0  # Erreur à soustraire après calibration

    def lire_brut(self):
        """Lit les données brutes du capteur sur le bus I2C"""
        try:
            data = self.i2c.readfrom(self.adresse, 4)
            status = (data[0] & 0xC0) >> 6
            
            if status == 2 or status == 3:
                return None, None
                
            p_raw = ((data[0] & 0x3F) << 8) | data[1]
            p_psi = ((p_raw - 1638.3) / 13107.0) * (self.p_max - self.p_min) + self.p_min
            p_pa = -(p_psi * self.psi_to_pa) # Inversion conservée de votre code
            
            t_raw = (data[2] << 3) | ((data[3] & 0xE0) >> 5)
            t_celsius = (t_raw / 2047.0) * 200.0 - 50.0
            
            return p_pa, t_celsius
        except Exception:
            return None, None

    def calibrer(self, nb_lectures=50):
        """Calibre le capteur pour trouver le zéro (offset)"""
        print(f"Calibration Pitot ({nb_lectures} mesures)... Ne touchez à rien !")
        somme_pression = 0.0
        lectures_valides = 0
        
        for _ in range(nb_lectures):
            p, _ = self.lire_brut()
            if p is not None:
                somme_pression += p
                lectures_valides += 1
            time.sleep(0.05)
            
        if lectures_valides > 0:
            self.offset = somme_pression / lectures_valides
            print(f"Offset Pitot: {self.offset:.2f} Pa")
        else:
            print("Erreur calibration Pitot")
            self.offset = 0.0

    def lire_vitesse(self):
        """Retourne un dictionnaire avec la pression calibrée, température et vitesse"""
        p_brute, temp = self.lire_brut()
        
        if p_brute is None:
            return None
            
        p_calibree = p_brute - self.offset
        if p_calibree < 0:
            p_calibree = 0.0
            
        v_ms = math.sqrt((2 * p_calibree) / self.rho)
        v_kmh = v_ms * 3.6
        
        return {
            "pression_pa": p_calibree,
            "temperature_c": temp,
            "vitesse_ms": v_ms,
            "vitesse_kmh": v_kmh
        }