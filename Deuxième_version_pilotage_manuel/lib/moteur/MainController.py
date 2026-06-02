# Fichier : lib/moteur/IbusServoController.py

from machine import UART, Pin, PWM
import time

# Import des classes moteur
from .Servo import Servo
from .ESC import ESC


class MainController:

    # Taille d'une trame IBUS (en octets)
    FRAME_LENGTH = 32

    # Nombre de canaux IBUS (14 canaux standards)
    CHANNEL_COUNT = 14

    def __init__(self, config):

        # =========================
        # Initialisation UART (réception IBUS)
        # =========================
        conn = config["connexion"]

        self.uart = UART(
            1,
            baudrate=conn["baudrate"],
            bits=conn["bits"],
            parity=conn["parity"],
            stop=conn["stop"],
            rx=conn["pin_rx"]
        )

        # Buffer pour stocker une trame IBUS complète
        self.frame = bytearray(self.FRAME_LENGTH)

        # Valeurs des canaux (initialisées à neutre)
        self.channels = [1500] * self.CHANNEL_COUNT

        # Index de lecture dans la trame
        self.index = 0

        # Temps de la dernière trame reçue (pour failsafe)
        self.last_frame_time = time.ticks_ms()
        
        # =========================
        # Configuration du FAILSAFE
        # =========================

        self.FAILSAFE_CHANNEL = 4  # CH5 (index 4)
        self.FAILSAFE_THRESHOLD = 1900  # seuil activation
        self.FAILSAFE_TIMEOUT = 500  # ms sans signal

        self.failsafe_active = False

        # Stocke les dernières valeurs envoyées aux moteurs
        self.current_outputs = [1500] * self.CHANNEL_COUNT

        # =========================
        # Création des dispositifs (Servo / ESC)
        # =========================

        self.devices = []

        for name, moteur in config["moteur"].items():

            # Création du PWM sur le pin spécifié
            pwm = PWM(Pin(moteur["pin"]), freq=moteur["frequence"])

            # Type de moteur (servo par défaut)
            moteur_type = moteur.get("type", "servo")

            if moteur_type == "servo":

                # Création d'un servo
                device = Servo(
                    pwm,
                    moteur["etat_actif_min"],
                    moteur["etat_actif_max"],
                    moteur.get("centre", 1500),
                    moteur["frequence"]
                )

            elif moteur_type == "esc":

                # Création d'un ESC
                device = ESC(
                    pwm,
                    moteur["etat_actif_min"],
                    moteur["etat_actif_max"],
                    moteur["frequence"]
                )

                # Armement automatique de l'ESC
                device.arm()

            else:
                # Erreur si type inconnu
                raise ValueError(f"Type de moteur inconnu pour {name} : {moteur_type}")

            # Association du moteur à un canal IBUS (indexé à partir de 0)
            channel = moteur.get("channel", 1) - 1

            # Ajout à la liste des dispositifs
            self.devices.append((device, channel))
        
        # Petite pause au démarrage
        time.sleep(1)

        # Test optionnel des moteurs
        self.startup_test()

    # =========================
    # Validation checksum IBUS
    # =========================

    def validate(self):
        checksum = 0xFFFF

        # Calcul du checksum (somme inversée)
        for i in range(30):
            checksum -= self.frame[i]

        # Récupération du checksum reçu
        received = self.frame[30] | (self.frame[31] << 8)

        # Vérification
        return checksum == received

    # =========================
    # Lecture du protocole IBUS
    # =========================

    def read_ibus(self):
        # Lecture des données UART
        data = self.uart.read()

        if not data:
            return False

        for byte in data:

            # Synchronisation début de trame
            if self.index == 0 and byte != 0x20:
                continue

            if self.index == 1 and byte != 0x40:
                self.index = 0
                continue

            # Stockage de l'octet
            self.frame[self.index] = byte
            self.index += 1

            # Trame complète reçue
            if self.index == self.FRAME_LENGTH:

                self.index = 0

                # Vérification du checksum
                if not self.validate():
                    return False

                # Extraction des canaux
                for i in range(self.CHANNEL_COUNT):

                    low = self.frame[2 + i*2]
                    high = self.frame[3 + i*2]

                    # Conversion en valeur 16 bits
                    self.channels[i] = low | (high << 8)

                # Mise à jour du timestamp
                self.last_frame_time = time.ticks_ms()

                return True

        return False

    # =========================
    # Test des moteurs au démarrage
    # =========================

    def startup_test(self, delay=1, esc_pulse=1100):
        """
        Test des moteurs :
        - Servo : min → max → centre
        - ESC : rotation lente
        """

        print("=== TEST DE DÉMARRAGE DES MOTEURS ===")

        for device, channel in self.devices:

            # Test Servo
            if isinstance(device, Servo):
                print(f"Test servo canal {channel}")
                device.update(device.min)
                time.sleep(delay)

                device.update(device.max)
                time.sleep(delay)

                device.update(device.centre)
                time.sleep(delay)

            # Test ESC
            if isinstance(device, ESC):
                print(f"Test ESC canal {channel}")
                device.update(esc_pulse)
                time.sleep(delay * 3)

                device.update(device.min)

        print("=== TEST TERMINÉ ===\n")
        time.sleep(delay)

    # =========================
    # FAILSAFE
    # =========================
    
    def ramp_towards(self, current, target, step):
        # Approche progressive vers une valeur cible
        if current < target:
            return min(current + step, target)
        else:
            return max(current - step, target)
        
    def failsafe(self):

        # Détection via canal (interrupteur radio)
        channel_triggered = self.channels[self.FAILSAFE_CHANNEL] >= self.FAILSAFE_THRESHOLD

        # Détection perte de signal
        now = time.ticks_ms()
        signal_lost = time.ticks_diff(now, self.last_frame_time) > self.FAILSAFE_TIMEOUT

        if channel_triggered or signal_lost:

            if not self.failsafe_active:
                print("!!! FAILSAFE ACTIVÉ !!!")
                self.failsafe_active = True

            # Arrêt progressif des moteurs
            for i, (device, channel) in enumerate(self.devices):

                current = self.current_outputs[i]

                if isinstance(device, ESC):
                    target = device.min   # coupe moteur
                    step = 5              # descente lente

                elif isinstance(device, Servo):
                    target = device.centre  # retour neutre
                    step = 10

                else:
                    continue

                # Transition progressive
                new_value = self.ramp_towards(current, target, step)

                self.current_outputs[i] = new_value
                device.update(new_value)

            return True

        else:
            if self.failsafe_active:
                print("Failsafe désactivé")
                self.failsafe_active = False

        return False
        
    # =========================
    # Mise à jour des sorties
    # =========================

    def update_outputs(self):
        for i, (device, channel) in enumerate(self.devices):

            pulse = self.channels[channel]

            # évite updates inutiles
            if abs(pulse - self.current_outputs[i]) < 10:
                continue

            self.current_outputs[i] = pulse
            device.update(pulse)

    # =========================
    # Boucle principale
    # =========================

    def run(self):

        while True:

            # Lecture des données IBUS
            self.read_ibus()

            # Si failsafe NON actif → contrôle normal
            if not self.failsafe():
                self.update_outputs()

                # Debug : affiche les 6 premiers canaux
                print(self.channels[:6])

            # Petite pause pour stabilité (2 ms)
            time.sleep_ms(20)

