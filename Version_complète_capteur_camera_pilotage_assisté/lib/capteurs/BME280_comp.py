from machine import Pin, I2C
from lib.capteurs import bme280
import time

class FiltreLissage:
    """Classe pour lisser les valeurs (filtre complémentaire)"""
    def __init__(self, alpha=0.1):
        self.alpha = alpha
        self.valeur_filtree = None

    def mettre_a_jour(self, nouvelle_valeur):
        if self.valeur_filtree is None:
            # Initialisation lors de la première mesure
            self.valeur_filtree = nouvelle_valeur
        else:
            # Application de la formule du filtre complémentaire
            self.valeur_filtree = (1 - self.alpha) * self.valeur_filtree + self.alpha * nouvelle_valeur
        return self.valeur_filtree


class CapteurBME280:
    """Classe pour gérer le capteur BME280 et ses mesures"""
    def __init__(self, scl_pin, sda_pin, i2c_bus=1, freq=10000, adresse=0x76, p0_mer=1016):
        # Configuration I2C
        self.i2c = I2C(i2c_bus, scl=Pin(scl_pin), sda=Pin(sda_pin), freq=freq)
        self.adresse = adresse
        self.p0_mer = p0_mer
        self.capteur = None

        self.connecter()

    def connecter(self):
        """Initialise la communication avec le capteur"""
        
        try:
            # Reset software du BME280 (registre 0xE0 = 0xB6)
            self.i2c.writeto_mem(self.adresse, 0xE0, bytes([0xB6]))
            time.sleep_ms(10)  # Délai de démarrage obligatoire (datasheet: 2ms min)
        
            self.capteur = bme280.BME280(i2c=self.i2c, address=self.adresse,mode=bme280.MODE_FORCED)
            # Lecture à vide pour stabiliser le capteur
            # .values retourne des chaînes : ('25.30C', '1013.25hPa', '45.20%')
            _ = self.capteur.values
            print("Capteur BME280 initialisé avec succès !")
        except Exception as e:
            # En cas d'erreur (comme ENODEV), on affiche l'erreur
            print(f"Échec de connexion ({e}). Nouvelle tentative dans 2 secondes...")
            self.capteur = None  # Sécurité : on s'assure qu'il reste à None
            time.sleep(2)

    def _extraire_nombre(self, donnee_str):
        """Convertit les chaînes renvoyées par la lib (ex: '25.3C') en float"""
        try:
            return float(''.join(c for c in donnee_str if c.isdigit() or c == '.' or c == '-'))
        except ValueError:
            return 0.0

    def lire_temperature(self):
        if not self.capteur: return None
        # .values[0] → ex: '25.30C'
        return self._extraire_nombre(self.capteur.values[0])

    def lire_pression(self):
        if not self.capteur: return None
        # .values[1] → ex: '1013.25hPa' (déjà en hPa)
        return self._extraire_nombre(self.capteur.values[1])

    def lire_humidite(self):
        if not self.capteur: return None
        # .values[2] → ex: '45.20%'
        return self._extraire_nombre(self.capteur.values[2])

    def lire_altitude(self):
        pression = self.lire_pression()
        if pression is None: return None
        # Formule barométrique internationale
        altitude = 288.15 / 0.0065 * (1 - (pression / self.p0_mer) ** (1 / 5.255))
        return altitude

    def est_connecte(self):
        return self.capteur is not None
    
# =====================================================================
# Bloc d'exécution autonome (permet de lancer le script directement)
# =====================================================================
if __name__ == "__main__":
    print("Démarrage du programme autonome...")

    # Instanciation du capteur avec tes paramètres (Pins de l'ESP32 par exemple)
    mon_bme = CapteurBME280(scl_pin=33, sda_pin=34, p0_mer=1016)

    # Instanciation du filtre pour l'altitude (alpha=0.1)
    filtre_altitude = FiltreLissage(alpha=0.1)

    print("Début des mesures (Ctrl+C pour arrêter)...")
    try:
        while True:
            # Si le capteur s'est déconnecté en cours de route, on tente de le reconnecter
            if not mon_bme.est_connecte():
                print("Capteur perdu. Tentative de reconnexion...")
                mon_bme.connecter()

            # Récupération des données via les méthodes de la classe
            temp = mon_bme.lire_temperature()
            press = mon_bme.lire_pression()
            hum = mon_bme.lire_humidite()
            alt_brute = mon_bme.lire_altitude()

            # On vérifie qu'on a bien reçu les données avant d'afficher
            if temp is not None and press is not None and hum is not None and alt_brute is not None:
                # Lissage de l'altitude
                alt_filtree = filtre_altitude.mettre_a_jour(alt_brute)

                # Affichage formaté
                print("-" * 30)
                print(f"Température : {temp:.2f} °C")
                print(f"Pression    : {press:.2f} hPa")
                print(f"Humidité    : {hum:.2f} %")
                print(f"Altitude    : {alt_filtree:.2f} m (lissée)")
            
            time.sleep(0.5)

    except KeyboardInterrupt:
        print("\nArrêt du programme par l'utilisateur.")

