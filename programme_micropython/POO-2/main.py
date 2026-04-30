"""
main.py — Système aéronautique unifié (Caméra + Pitot)
=======================================================

Architecture orientée objets :

    AeroSystem
    ├── Camera        (camera.py  — SPI2)
    ├── FileManager   (camera.py)
    └── PitotSensor   (pitot_sensor.py — I2C0)

Branchement caméra (SPI 2) :
    VCC  - 5V      rouge
    GND  - GND     noir
    SCK  - GP40    blanc
    MISO - GP41    marron
    MOSI - GP42    jaune
    CS   - GP39    orange

Branchement Pitot (I2C 0) :
    SDA  - GP43
    SCL  - GP44
"""

from machine import Pin, SPI
from utime import sleep_ms
import time

from camera import Camera, FileManager
from pitot_sensor import PitotSensor


class AeroSystem:
    """
    Système embarqué unifié pilotant la caméra Arducam et le tube de Pitot.

    Utilisation typique
    -------------------
        sys = AeroSystem()
        sys.setup()                     # Calibration Pitot + config caméra
        sys.capture_and_log()           # Photo horodatée + mesure vitesse
        sys.run(duration_s=30)          # Boucle de mesure pendant 30 s
    """

    def __init__(self,
                 # --- Caméra ---
                 cam_spi_id=2,
                 cam_sck=40, cam_miso=41, cam_mosi=42, cam_cs=39,
                 cam_baudrate=1_000_000,
                 cam_resolution='1600X1200',
                 cam_brightness=Camera.BRIGHTNESS_PLUS_4,
                 cam_contrast=Camera.CONTRAST_MINUS_3,
                 # --- Pitot ---
                 pitot_sda=43, pitot_scl=44,
                 pitot_address=0x28,
                 pitot_calib_readings=50,
                 # --- Général ---
                 photo_prefix='flight',
                 debug=True):

        self.debug = debug
        self.photo_prefix = photo_prefix
        self._pitot_calib_readings = pitot_calib_readings

        # ── Caméra ──────────────────────────────────────────────────────
        if self.debug:
            print("[AeroSystem] Initialisation de la caméra...")

        spi = SPI(cam_spi_id,
                  sck=Pin(cam_sck),
                  miso=Pin(cam_miso),
                  mosi=Pin(cam_mosi),
                  baudrate=cam_baudrate)
        cs = Pin(cam_cs, Pin.OUT)

        self.file_manager = FileManager()
        self.camera = Camera(spi, cs, debug_text_enabled=debug)
        self.camera.resolution = cam_resolution
        self.camera.set_brightness_level(cam_brightness)
        self.camera.set_contrast(cam_contrast)

        # ── Pitot ────────────────────────────────────────────────────────
        if self.debug:
            print("[AeroSystem] Initialisation du capteur Pitot...")

        self.pitot = PitotSensor(
            sda_pin=pitot_sda,
            scl_pin=pitot_scl,
            address=pitot_address,
            debug=debug,
        )

        if self.debug:
            print("[AeroSystem] Système prêt.\n")

    # ------------------------------------------------------------------
    # Configuration initiale
    # ------------------------------------------------------------------

    def setup(self):
        """
        Lance la calibration du Pitot.
        À appeler une fois au démarrage, tube immobile et à l'abri du vent.
        """
        print("[AeroSystem] Calibration du capteur Pitot en cours...")
        time.sleep(1)  # Laisse le temps au capteur de démarrer
        self.pitot.calibrate(self._pitot_calib_readings)

    # ------------------------------------------------------------------
    # Capture photo
    # ------------------------------------------------------------------

    def capture_photo(self, name=None):
        """
        Prend une photo et la sauvegarde.

        :param name: Préfixe du fichier (utilise self.photo_prefix par défaut)
        :return: Nom du fichier sauvegardé
        """
        prefix = name or self.photo_prefix
        filename = self.file_manager.new_jpg_fn(prefix)

        if self.debug:
            print(f"[AeroSystem] Capture → {filename}")

        self.camera.capture_jpg()
        sleep_ms(50)
        self.camera.saveJPG(filename)
        return filename

    # ------------------------------------------------------------------
    # Lecture Pitot
    # ------------------------------------------------------------------

    def read_pitot(self):
        """
        Lit le capteur Pitot (avec offset de calibration appliqué).

        :return: dict ou None en cas d'erreur
        """
        data = self.pitot.read()
        if data is None:
            print("[AeroSystem] Erreur de lecture Pitot.")
        return data

    def print_pitot(self, data):
        """Affiche les données Pitot de façon lisible."""
        if data:
            print(
                f"  Pression : {data['pressure_pa']:6.2f} Pa | "
                f"Temp : {data['temperature_c']:5.1f} °C | "
                f"Vitesse : {data['speed_ms']:5.2f} m/s "
                f"({data['speed_kmh']:5.1f} km/h)"
            )
        else:
            print("  [Pitot] Lecture invalide.")

    # ------------------------------------------------------------------
    # Action combinée : photo + mesure
    # ------------------------------------------------------------------

    def capture_and_log(self, photo_name=None):
        """
        Prend une photo ET enregistre simultanément les données de vitesse/pression.

        :return: (filename, pitot_data)
        """
        filename = self.capture_photo(photo_name)
        data = self.read_pitot()
        self.print_pitot(data)
        return filename, data

    # ------------------------------------------------------------------
    # Boucle de mesure continue
    # ------------------------------------------------------------------

    def run(self, duration_s=None, interval_s=1, capture_every_n=0):
        """
        Boucle principale de mesures Pitot, avec captures photo optionnelles.

        :param duration_s:     Durée totale en secondes (None = infini)
        :param interval_s:     Intervalle entre deux mesures en secondes
        :param capture_every_n: Prend une photo toutes les N mesures (0 = jamais)
        """
        print("[AeroSystem] Démarrage de la boucle de mesure. (Ctrl+C pour arrêter)\n")
        count = 0
        start = time.time()

        try:
            while True:
                count += 1

                # Prise de photo si demandé
                if capture_every_n > 0 and count % capture_every_n == 0:
                    self.capture_photo()

                # Lecture et affichage Pitot
                data = self.read_pitot()
                self.print_pitot(data)

                # Vérification de la durée
                if duration_s and (time.time() - start) >= duration_s:
                    print(f"\n[AeroSystem] Durée atteinte ({duration_s} s). Arrêt.")
                    break

                time.sleep(interval_s)

        except KeyboardInterrupt:
            print("\n[AeroSystem] Arrêt demandé par l'utilisateur.")

    # ------------------------------------------------------------------
    # Représentation
    # ------------------------------------------------------------------

    def __repr__(self):
        return (f"AeroSystem(camera={self.camera.camera_idx}, "
                f"pitot={self.pitot})")


# ══════════════════════════════════════════════════════════════════════
#  PROGRAMME PRINCIPAL
# ══════════════════════════════════════════════════════════════════════

if __name__ == '__main__':

    # 1. Création du système
    system = AeroSystem(
        cam_resolution='1600X1200',
        photo_prefix='vol',
        debug=True,
    )

    # 2. Calibration du Pitot au démarrage
    system.setup()

    # 3a. Exemple : photo unique + lecture vitesse
    # system.capture_and_log()

    # 3b. Exemple : boucle 60 s, 1 mesure/s, photo toutes les 10 mesures
    system.run(duration_s=60, interval_s=1, capture_every_n=10)
