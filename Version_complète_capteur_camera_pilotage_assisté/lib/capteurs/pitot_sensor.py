from machine import Pin, I2C
import time
import math


class PitotSensor:
    """
    Pilote orienté objets pour le capteur de pression différentielle MS4525DO.
    Utilisé pour mesurer la vitesse via un tube de Pitot (Formule de Bernoulli).

    Branchement :
        SDA - GP43
        SCL - GP44
    """

    # --- Constantes du capteur ---
    P_MIN = -1.0          # Pression minimum en PSI
    P_MAX = 1.0           # Pression maximum en PSI
    PSI_TO_PA = 6894.757  # Conversion PSI -> Pascals
    RHO = 1.225           # Masse volumique de l'air (kg/m³)

    def __init__(self, sda_pin=43, scl_pin=44, i2c_id=0, freq=100000,
                 address=0x28, debug=False):
        """
        Initialise le bus I2C et le capteur MS4525DO.

        :param sda_pin: Numéro de broche SDA (défaut: 43)
        :param scl_pin: Numéro de broche SCL (défaut: 44)
        :param i2c_id:  Identifiant du bus I2C (défaut: 0)
        :param freq:    Fréquence I2C en Hz (défaut: 100 000)
        :param address: Adresse I2C du capteur (défaut: 0x28)
        :param debug:   Active les messages de débogage (défaut: False)
        """
        self.address = address
        self.debug = debug
        self._offset = 0.0  # Offset de calibration en Pascals

        self.i2c = I2C(i2c_id, sda=Pin(sda_pin), scl=Pin(scl_pin), freq=freq)

        if self.debug:
            print(f"[PitotSensor] Initialisé sur I2C{i2c_id} "
                  f"SDA=GP{sda_pin} SCL=GP{scl_pin} @ 0x{address:02X}")

    # ------------------------------------------------------------------
    # Lecture brute du capteur
    # ------------------------------------------------------------------

    def read_raw(self):
        """
        Lit les 4 octets du capteur et retourne (pression_Pa, température_°C).
        Retourne (None, None) en cas d'erreur ou de statut invalide.
        """
        try:
            data = self.i2c.readfrom(self.address, 4)
        except OSError as e:
            if self.debug:
                print(f"[PitotSensor] Erreur I2C : {e}")
            return None, None

        status = (data[0] & 0xC0) >> 6
        if status in (2, 3):
            if self.debug:
                print(f"[PitotSensor] Statut invalide : {status}")
            return None, None

        # Pression (14 bits)
        p_raw = ((data[0] & 0x3F) << 8) | data[1]
        p_psi = ((p_raw - 1638.3) / 13107.0) * (self.P_MAX - self.P_MIN) + self.P_MIN
        p_pa = -(p_psi * self.PSI_TO_PA)

        # Température (11 bits)
        t_raw = (data[2] << 3) | ((data[3] & 0xE0) >> 5)
        t_celsius = (t_raw / 2047.0) * 200.0 - 50.0

        return p_pa, t_celsius

    # ------------------------------------------------------------------
    # Calibration (Auto-Zéro)
    # ------------------------------------------------------------------

    def calibrate(self, nb_readings=50, delay_ms=50):
        """
        Effectue l'Auto-Zéro : mesure la pression au repos et calcule l'offset.

        :param nb_readings: Nombre de lectures pour la moyenne (défaut: 50)
        :param delay_ms:    Pause entre deux lectures en ms (défaut: 50)
        :return: Offset calculé en Pascals
        """
        print(f"\n[PitotSensor] --- DÉBUT CALIBRATION ({nb_readings} mesures) ---")
        print("[PitotSensor] Ne touchez pas au tube de Pitot !")

        total = 0.0
        valid = 0

        for _ in range(nb_readings):
            p, _ = self.read_raw()
            if p is not None:
                total += p
                valid += 1
                print(".", end="")
            time.sleep_ms(delay_ms)

        print()

        if valid > 0:
            self._offset = total / valid
            print(f"[PitotSensor] Calibration OK — Offset : {self._offset:.2f} Pa\n")
        else:
            self._offset = 0.0
            print("[PitotSensor] ÉCHEC : impossible de lire le capteur.\n")

        return self._offset

    # ------------------------------------------------------------------
    # Lecture corrigée
    # ------------------------------------------------------------------

    def read(self):
        """
        Lit le capteur et applique l'offset de calibration.

        :return: dict {'pressure_pa': float, 'temperature_c': float,
                       'speed_ms': float, 'speed_kmh': float}
                 ou None en cas d'erreur de lecture.
        """
        p_raw, temperature = self.read_raw()

        if p_raw is None:
            return None

        p_calibrated = max(p_raw - self._offset, 0.0)
        speed_ms = math.sqrt((2 * p_calibrated) / self.RHO)
        speed_kmh = speed_ms * 3.6

        return {
            'pressure_pa':  p_calibrated,
            'temperature_c': temperature,
            'speed_ms':     speed_ms,
            'speed_kmh':    speed_kmh,
        }

    # ------------------------------------------------------------------
    # Propriété utilitaire
    # ------------------------------------------------------------------

    @property
    def offset(self):
        """Retourne l'offset de calibration actuel (Pa)."""
        return self._offset

    def __repr__(self):
        return (f"PitotSensor(address=0x{self.address:02X}, "
                f"offset={self._offset:.2f} Pa)")
