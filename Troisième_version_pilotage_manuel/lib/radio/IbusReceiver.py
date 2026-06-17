# Fichier : lib/radio/IbusReceiver.py

from machine import UART
import time


class IbusReceiver:

    # Longueur fixe d'une trame IBUS (en octets)
    FRAME_LENGTH = 32

    # Nombre de canaux transmis (max 14 en IBUS)
    CHANNEL_COUNT = 14

    def __init__(self, conn):
        """
        Initialise la liaison UART pour recevoir les données IBUS.

        conn : dictionnaire de configuration contenant :
            - baudrate
            - bits
            - parity
            - stop
            - pin_rx
        """

        # Initialisation du port série (UART1)
        self.uart = UART(
            1,
            baudrate=conn["baudrate"],
            bits=conn["bits"],
            parity=conn["parity"],
            stop=conn["stop"],
            rx=conn["pin_rx"]
        )

        # Buffer pour stocker une trame complète IBUS
        self.frame = bytearray(self.FRAME_LENGTH)

        # Valeurs des canaux initialisées au neutre (1500 µs)
        self.channels = [1500] * self.CHANNEL_COUNT

        # Index courant dans la trame (pour reconstruction byte par byte)
        self.index = 0

        # Timestamp de la dernière trame valide reçue
        self.last_frame_time = time.ticks_ms()

    # =========================
    # VALIDATION IBUS
    # =========================
    def validate(self):
        """
        Vérifie l'intégrité de la trame IBUS via checksum.

        Le checksum IBUS :
        - commence à 0xFFFF
        - soustrait les 30 premiers octets
        - doit correspondre aux 2 derniers octets
        """

        checksum = 0xFFFF

        # Calcul du checksum sur les 30 premiers octets
        for i in range(30):
            checksum -= self.frame[i]

        # Reconstruction du checksum reçu (little endian)
        received = self.frame[30] | (self.frame[31] << 8)

        return checksum == received

    # =========================
    # LECTURE IBUS
    # =========================
    def read(self):
        """
        Lit les données UART et reconstruit une trame IBUS.

        Returns:
            True si une trame valide a été reçue
            False sinon
        """

        # Lecture des données disponibles sur l'UART
        data = self.uart.read()
        if not data:
            return False

        # Traitement byte par byte
        for byte in data:

            # Synchronisation sur le début de trame :
            # Premier octet attendu = 0x20
            if self.index == 0 and byte != 0x20:
                continue

            # Deuxième octet attendu = 0x40
            if self.index == 1 and byte != 0x40:
                self.index = 0
                continue

            # Stockage du byte dans le buffer
            self.frame[self.index] = byte
            self.index += 1

            # Si la trame est complète
            if self.index == self.FRAME_LENGTH:

                # Reset pour la prochaine trame
                self.index = 0

                # Vérification du checksum
                if not self.validate():
                    return False

                # Extraction des canaux :
                # chaque canal = 2 octets (little endian)
                for i in range(self.CHANNEL_COUNT):
                    low = self.frame[2 + i*2]
                    high = self.frame[3 + i*2]
                    self.channels[i] = low | (high << 8)

                # Mise à jour du timestamp (important pour failsafe)
                self.last_frame_time = time.ticks_ms()

                return True  # trame valide reçue

        # Aucune trame complète valide
        return False