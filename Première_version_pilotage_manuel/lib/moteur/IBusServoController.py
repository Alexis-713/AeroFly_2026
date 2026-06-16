# lib/moteur/IbusServoController.py
from machine import UART, Pin, PWM
import time
from .Servo import Servo
from .ESC import ESC


class IBusServoController:

    FRAME_LENGTH = 32
    CHANNEL_COUNT = 14

    def __init__(self, config):

        conn = config["connexion"]
        # Initialisation de la connexion
        self.uart = UART(
            1,
            baudrate=conn["baudrate"],
            bits=conn["bits"],
            parity=conn["parity"],
            stop=conn["stop"],
            rx=conn["pin_rx"]
        )

        self.frame = bytearray(self.FRAME_LENGTH)
        self.channels = [1500] * self.CHANNEL_COUNT
        self.index = 0
        self.last_frame_time = 0
        # =========================
        # Création des dispositifs
        # =========================

        self.devices = []

        for name, moteur in config["moteur"].items():

            pwm = PWM(Pin(moteur["pin"]), freq=moteur["frequence"])

            moteur_type = moteur.get("type", "servo")

            if moteur_type == "servo":

                device = Servo(
                    pwm,
                    moteur["etat_actif_min"],
                    moteur["etat_actif_max"],
                    moteur.get("centre", 1500)
                )

            elif moteur_type == "esc":

                device = ESC(
                    pwm,
                    moteur["etat_actif_min"],
                    moteur["etat_actif_max"]
                )

                # Arming automatique de l'ESC
                device.arm()

            else:
                raise ValueError(f"Type de moteur inconnu pour {name} : {moteur_type}")

            # canal iBus correspondant (0-indexé)
            channel = moteur.get("channel", 1) - 1
            
            self.devices.append((device, channel))
        
        # Test de démarrage des moteurs
        time.sleep(2)
        self.startup_test()
    # =========================
    # Validation checksum
    # =========================

    def validate(self):

        checksum = 0xFFFF

        for i in range(30):
            checksum -= self.frame[i]

        received = self.frame[30] | (self.frame[31] << 8)

        return checksum == received

    # =========================
    # Lecture IBUS
    # =========================

    def read_ibus(self):

        data = self.uart.read()

        if not data:
            return False

        for byte in data:

            if self.index == 0 and byte != 0x20:
                continue

            if self.index == 1 and byte != 0x40:
                self.index = 0
                continue

            self.frame[self.index] = byte
            self.index += 1

            if self.index == self.FRAME_LENGTH:

                self.index = 0

                if not self.validate():
                    return False

                for i in range(self.CHANNEL_COUNT):

                    low = self.frame[2 + i*2]
                    high = self.frame[3 + i*2]

                    self.channels[i] = low | (high << 8)

                self.last_frame_time = time.ticks_ms()

                return True

        return False

    # =========================
    # Test fonctionnement servomoteurs
    # =========================
    def startup_test(self, delay=1, esc_pulse=1200):
        """
        Test des moteurs au démarrage :
        - servos : min → max → centre
        - ESC : petite rotation
        """
        print("=== TEST DE DÉMARRAGE DES MOTEURS ===")
        for device, channel in self.devices:
            # Test Servo
#             if isinstance(device, Servo):
#                 print(f"Test servo canal {channel}")
#                 device.update(device.min)
#                 time.sleep(delay)
#                 device.update(device.max)
#                 time.sleep(delay)
#                 device.update(device.centre)
#                 time.sleep(delay)
            # Test ESC (brushless)
            if isinstance(device, ESC):
                print(f"Test ESC canal {channel}")
                device.update(esc_pulse)  # petite vitesse
                time.sleep(delay*2)
                device.update(device.min)  # arrêt
        print("=== TEST DE DÉMARRAGE TERMINÉ ===\n")
        time.sleep(delay)
    # =========================
    # Mise à jour dispositifs
    # =========================

    def update_outputs(self):

        for device, channel in self.devices:

            pulse = self.channels[channel]

            device.update(pulse)

    # =========================
    # Boucle principale
    # =========================

    def run(self):

        while True:

            now = time.ticks_ms()

            if self.read_ibus():

                self.update_outputs()

                #if time.ticks_ms() % 200 == 0:
                print(self.channels[:6])
