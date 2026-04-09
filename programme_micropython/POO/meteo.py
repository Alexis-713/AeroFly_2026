import time
import bme280

class CapteurMeteo:
    def __init__(self, i2c, adresse=0x76, p0=1020, alpha=0.1):
        self.i2c = i2c
        self.adresse = adresse
        self.p0 = p0
        self.alpha = alpha
        self.altitude_filtree = 0.0
        
        try:
            self.sensor = bme280.BME280(i2c=self.i2c, address=self.adresse)
            # Initialisation du filtre
            _, p_str, _ = self.sensor.values
            self.altitude_filtree = self._calculer_altitude(self._extraire_valeur(p_str))
        except Exception as e:
            print("Erreur initialisation BME280:", e)
            self.sensor = None

    def _extraire_valeur(self, donnee_str):
        """Nettoie la chaîne pour la convertir en float"""
        return float(''.join(c for c in donnee_str if c.isdigit() or c == '.'))

    def _calculer_altitude(self, pression_hpa):
        """Formule barométrique internationale"""
        return 288.15 / 0.0065 * (1 - (pression_hpa / self.p0)**(1 / 5.255))

    def lire_donnees(self):
        """Lit le capteur, applique le filtre et retourne un dictionnaire"""
        if self.sensor is None:
            return None
            
        try:
            t_str, p_str, h_str = self.sensor.values
            pression = self._extraire_valeur(p_str)
            
            # Application du filtre complémentaire
            alt_brute = self._calculer_altitude(pression)
            self.altitude_filtree = (1 - self.alpha) * self.altitude_filtree + self.alpha * alt_brute
            
            return {
                "temperature_str": t_str,
                "pression_hpa": pression,
                "humidite_str": h_str,
                "altitude_m": self.altitude_filtree
            }
        except Exception:
            return None