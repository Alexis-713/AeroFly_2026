# Fichier : lib/capteurs/SensorManager.py

from machine import Pin, SPI
import time

from lib.capteurs.pitot_sensor import PitotSensor
from lib.capteurs.BME280_comp import CapteurBME280, FiltreLissage

from lib.camera.camera import FileManager, Camera


class SensorManager:

    SENSOR_INTERVAL_SENSORS_MS = 30000  # 30 secondes
    SENSOR_INTERVAL_CAMERA_MS = 60000  # 30 secondes

    def __init__(self, config):

        print("=== INITIALISATION CAPTEURS ===")

        self.config = config

        # ==========================================
        # CONFIGURATION
        # ==========================================
        capteurs_config = config["capteurs"]
        camera_config = config["camera"]

        pitot_config = capteurs_config["Pitot"]
        bme_config = capteurs_config["BME280"]

        # ==========================================
        # BME280
        # ==========================================
        self.bme = None
        self.filtre_alt = None

        try:

            self.bme = CapteurBME280(
                sda_pin=bme_config["SDA"],
                scl_pin=bme_config["SCL"],
                i2c_bus=bme_config["i2c_bus"]
            )

            self.filtre_alt = FiltreLissage(alpha=0.1)

            print("[OK] BME280")

        except Exception as e:

            print("[ERREUR] BME280 :", e)

        # ==========================================
        # PITOT
        # ==========================================
        self.pitot = None

        try:

            self.pitot = PitotSensor(
                sda_pin=pitot_config["SDA"],
                scl_pin=pitot_config["SCL"],
                i2c_id=pitot_config["i2c_id"],
                debug=False
            )

            self.pitot.calibrate()

            print("[OK] PITOT")

        except Exception as e:

            print("[ERREUR] PITOT :", e)

        # ==========================================
        # CAMERA
        # ==========================================
        self.cam = None
        self.fm = None

        try:

            self.fm = FileManager()

            spi = SPI(
                camera_config["SPI"],
                sck=Pin(camera_config["SCK"]),
                miso=Pin(camera_config["MISO"]),
                mosi=Pin(camera_config["MOSI"]),
                baudrate=camera_config["baudrate"]
            )

            cs = Pin(camera_config["CS"], Pin.OUT)

            self.cam = Camera(
                spi,
                cs,
                debug_text_enabled=False
            )

            self.cam.resolution = "1600X1200"

            self.cam.set_brightness_level(
                self.cam.BRIGHTNESS_PLUS_4
            )

            self.cam.set_contrast(
                self.cam.CONTRAST_MINUS_3
            )

            print("[OK] CAMERA")

        except Exception as e:

            print("[ERREUR] CAMERA :", e)

        # ==========================================
        # DONNÉES CAPTEURS
        # ==========================================
        self.temperature = None
        self.pressure = None
        self.altitude = None
        self.speed = None

        # ==========================================
        # TIMER
        # ==========================================
        self.last_sensor_update = time.ticks_ms()

    # =====================================================
    # UPDATE
    # =====================================================
    def update(self):

        now = time.ticks_ms()

        # Lecture toutes les 30 secondes
        if time.ticks_diff(now, self.last_sensor_update) >= self.SENSOR_INTERVAL_SENSORS_MS:

            self.last_sensor_update = now

            self.read_sensors()

        # Photo prise toutes les 60 secondes
        if time.ticks_diff(now, self.last_sensor_update) >= self.SENSOR_INTERVAL_CAMERA_MS:

            self.last_sensor_update = now

            self.take_a_screen()

    # =====================================================
    # LECTURE CAPTEURS
    # =====================================================
    def read_sensors(self):

        print("=== LECTURE CAPTEURS ===")

        # ==========================================
        # BME280
        # ==========================================
        if self.bme and self.bme.est_connecte():

            try:

                self.temperature = self.bme.lire_temperature()

                self.pressure = self.bme.lire_pression()

                alt_brute = self.bme.lire_altitude()

                if alt_brute is not None:

                    self.altitude = self.filtre_alt.mettre_a_jour(
                        alt_brute
                    )

                print(
                    f"[BME280] "
                    f"T={self.temperature:.1f}°C | "
                    f"P={self.pressure:.1f}hPa | "
                    f"ALT={self.altitude:.1f}m"
                )

            except Exception as e:

                print("Erreur lecture BME280 :", e)

        # ==========================================
        # PITOT
        # ==========================================
        if self.pitot:

            try:

                data = self.pitot.read()

                if data:

                    self.speed = data["speed_kmh"]

                    print(
                        f"[PITOT] "
                        f"Vitesse={self.speed:.2f} km/h"
                    )

            except Exception as e:

                print("Erreur lecture PITOT :", e)

    # ==========================================
    # CAMERA
    # ==========================================
    def take_a_screen(self):
        if self.cam:

            try:

                print("[CAMERA] Capture en cours...")

                filename = self.fm.new_jpg_fn(
                    "flight"
                )

                self.cam.capture_jpg()

                time.sleep_ms(50)

                self.cam.saveJPG(
                    filename,
                    progress_bar=False
                )

                print(
                    f"[CAMERA] Image sauvegardée : "
                    f"{filename}"
                )

            except Exception as e:

                print("Erreur CAMERA :", e)

        print("===========================\n")