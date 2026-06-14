import time
import math
import unittest

# =====================================================================
# 1. Simulateur de bus I2C (Mock) pour le capteur MS4525DO
# =====================================================================
class MockI2C:
    """
    Simule la connexion matérielle I2C en générant les 4 octets de réponse
    du capteur MS4525DO en fonction des valeurs brutes configurées.
    """
    def __init__(self):
        self.status = 0     # Statut normal
        self.p_raw = 8192   # Valeur brute correspondant à ~0 PSI (milieu de plage)
        self.t_raw = 1024   # Valeur brute correspondant à ~47 °C

    def readfrom(self, address, count):
        """
        Génère une trame de 4 octets telle qu'envoyée par le MS4525DO.
        """
        if count != 4:
            raise ValueError("Ce capteur ne supporte que la lecture de 4 octets.")
            
        # Encodage de l'octet 0 (Statut sur les 2 bits de poids fort, Pression sur les 6 restants)
        b0 = ((self.status & 0x03) << 6) | ((self.p_raw >> 8) & 0x3F)
        # Encodage de l'octet 1 (Reste de la pression sur 8 bits)
        b1 = self.p_raw & 0xFF
        # Encodage de l'octet 2 (Température sur les 8 bits de poids fort)
        b2 = (self.t_raw >> 3) & 0xFF
        # Encodage de l'octet 3 (Reste de la température sur 3 bits, décalés)
        b3 = (self.t_raw & 0x07) << 5

        return bytes([b0, b1, b2, b3])


# =====================================================================
# 2. Classe du capteur (Adaptée pour Python Standard)
# =====================================================================
class PitotSensor:
    """
    Pilote orienté objets pour le capteur de pression différentielle MS4525DO.
    Utilisé pour mesurer la vitesse via un tube de Pitot.
    """

    # --- Constantes du capteur ---
    P_MIN = -1.0          # Pression minimum en PSI
    P_MAX = 1.0           # Pression maximum en PSI
    PSI_TO_PA = 6894.757  # Conversion PSI -> Pascals
    RHO = 1.225           # Masse volumique de l'air (kg/m³)

    def __init__(self, i2c_bus=None, address=0x28, debug=False):
        """
        Initialise le capteur avec un bus I2C (réel ou simulé).

        :param i2c_bus: Objet I2C ou MockI2C. Si None, utilise le Mock.
        :param address: Adresse I2C du capteur (défaut: 0x28)
        :param debug:   Active les messages de débogage (défaut: False)
        """
        self.address = address
        self.debug = debug
        self._offset = 0.0  # Offset de calibration en Pascals

        # Injection de dépendance : si aucun bus n'est fourni, on utilise le simulateur
        if i2c_bus is None:
            if self.debug:
                print("[PitotSensor] Aucun bus matériel fourni, utilisation de MockI2C.")
            self.i2c = MockI2C()
        else:
            self.i2c = i2c_bus

    def read_raw(self):
        """
        Lit les 4 octets du capteur et retourne (pression_Pa, température_°C).
        Retourne (None, None) en cas d'erreur ou de statut invalide.
        """
        try:
            data = self.i2c.readfrom(self.address, 4)
        except Exception as e:
            if self.debug:
                print(f"[PitotSensor] Erreur I2C : {e}")
            return None, None

        status = (data[0] & 0xC0) >> 6
        if status in (2, 3):
            if self.debug:
                print(f"[PitotSensor] Statut invalide : {status}")
            return None, None

        # Décodage de la pression (14 bits)
        p_raw = ((data[0] & 0x3F) << 8) | data[1]
        p_psi = ((p_raw - 1638.3) / 13107.0) * (self.P_MAX - self.P_MIN) + self.P_MIN
        p_pa = -(p_psi * self.PSI_TO_PA)

        # Décodage de la température (11 bits)
        t_raw = (data[2] << 3) | ((data[3] & 0xE0) >> 5)
        t_celsius = (t_raw / 2047.0) * 200.0 - 50.0

        return p_pa, t_celsius

    def calibrate(self, nb_readings=50, delay_ms=50):
        """
        Effectue l'Auto-Zéro : mesure la pression au repos et calcule l'offset.
        """
        if self.debug:
            print(f"\n[PitotSensor] --- DÉBUT CALIBRATION ({nb_readings} mesures) ---")

        total = 0.0
        valid = 0

        for _ in range(nb_readings):
            p, _ = self.read_raw()
            if p is not None:
                total += p
                valid += 1
            # Conversion ms -> secondes pour Python standard
            time.sleep(delay_ms / 1000.0) 

        if valid > 0:
            self._offset = total / valid
            if self.debug:
                print(f"[PitotSensor] Calibration OK — Offset : {self._offset:.2f} Pa\n")
        else:
            self._offset = 0.0
            if self.debug:
                print("[PitotSensor] ÉCHEC : impossible de lire le capteur.\n")

        return self._offset

    def read(self):
        """
        Lit le capteur et applique l'offset de calibration pour calculer la vitesse.
        """
        p_raw, temperature = self.read_raw()

        if p_raw is None:
            return None

        # Applique l'offset et évite les valeurs négatives (bruit) sous la racine carrée
        p_calibrated = max(p_raw - self._offset, 0.0)
        
        # Formule de Bernoulli
        speed_ms = math.sqrt((2 * p_calibrated) / self.RHO)
        speed_kmh = speed_ms * 3.6

        return {
            'pressure_pa':  p_calibrated,
            'temperature_c': temperature,
            'speed_ms':     speed_ms,
            'speed_kmh':    speed_kmh,
        }

    @property
    def offset(self):
        return self._offset


# =====================================================================
# 3. Tests Unitaires Automatisés (Version Corrigée)
# =====================================================================
class TestPitotSensor(unittest.TestCase):
    
    def setUp(self):
        """S'exécute avant chaque test. Initialise le mock et le capteur."""
        self.mock_i2c = MockI2C()
        self.sensor = PitotSensor(i2c_bus=self.mock_i2c, debug=False)

    def test_read_raw_zero_pressure(self):
        """Test la lecture brute avec une valeur proche de 0 PSI."""
        self.mock_i2c.p_raw = 8192  # Milieu de la plage de 14 bits
        p_pa, t_celsius = self.sensor.read_raw()
        
        self.assertIsNotNone(p_pa)
        self.assertIsNotNone(t_celsius)
        
        # Corrigé : à 8192 la valeur exacte est de ~ -0.21 Pa. 
        # On teste à 0.5 Pa près (places=0) ou on cible la valeur théorique exacte.
        self.assertAlmostEqual(p_pa, -0.21, places=2)
        self.assertAlmostEqual(t_celsius, 50.0, places=1)

    def test_status_error_handling(self):
        """Vérifie que le capteur retourne None en cas de statut d'erreur (ex: 2)."""
        self.mock_i2c.status = 2  
        p_pa, t_celsius = self.sensor.read_raw()
        
        self.assertIsNone(p_pa)
        self.assertIsNone(t_celsius)

    def test_calibration(self):
        """Vérifie que la calibration calcule correctement l'offset moyen."""
        self.mock_i2c.p_raw = 8192
        offset = self.sensor.calibrate(nb_readings=5, delay_ms=0)
        
        # L'offset doit être égal à la valeur lue (ici environ -0.21 Pa)
        self.assertAlmostEqual(offset, -0.21, places=2)
        self.assertEqual(self.sensor.offset, offset)

    def test_read_speed_calculation(self):
        """Simule une pression positive (vent en face) et valide les calculs de vitesse."""
        # Un p_raw de 7500 donne une pression brute positive d'environ 110 Pa
        self.mock_i2c.p_raw = 7500 
        
        # On force l'offset à la valeur brute attendue pour simuler un "zéro" parfait
        self.sensor._offset = -0.2104144960708011
        
        data = self.sensor.read()
        self.assertIsNotNone(data)
        
        self.assertGreater(data['pressure_pa'], 0)
        self.assertGreater(data['speed_ms'], 0)
        
        # Vérification de la cohérence de conversion m/s vers km/h
        expected_kmh = data['speed_ms'] * 3.6
        self.assertAlmostEqual(data['speed_kmh'], expected_kmh, places=4)


if __name__ == "__main__":
    # Lancement du module de tests unitaires
    unittest.main(verbosity=2)