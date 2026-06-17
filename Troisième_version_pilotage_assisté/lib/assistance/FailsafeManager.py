# Fichier : lib/assistance/FailsafeManager.py

import time


class FailsafeManager:

    def __init__(self):
        # Canal radio utilisé pour déclencher manuellement le failsafe
        self.FAILSAFE_CHANNEL = 4

        # Seuil au-dessus duquel on considère que le switch est activé
        self.FAILSAFE_THRESHOLD = 1900

        # Temps maximum (ms) sans réception de trame avant de considérer une perte de signal
        self.FAILSAFE_TIMEOUT = 500

        # Mode actuel du système ("NORMAL" ou "FAILSAFE")
        self.control_mode = "NORMAL"

    def update(self, channels, last_frame_time):
        """
        Met à jour l'état du failsafe.

        Args:
            channels: liste des valeurs PWM des canaux radio
            last_frame_time: timestamp (ms) de la dernière trame reçue

        Returns:
            True si le failsafe est actif, sinon False
        """

        # Temps actuel en millisecondes
        now = time.ticks_ms()

        # Détection perte de signal :
        # si trop de temps s'est écoulé depuis la dernière trame reçue
        signal_lost = time.ticks_diff(now, last_frame_time) > self.FAILSAFE_TIMEOUT

        # Détection activation manuelle via un switch radio
        switch_trigger = channels[self.FAILSAFE_CHANNEL] >= self.FAILSAFE_THRESHOLD

        # Le failsafe est déclenché si :
        # - perte de signal
        # OU
        # - switch activé
        triggered = signal_lost or switch_trigger

        # Passage en mode FAILSAFE (une seule fois)
        if triggered and self.control_mode != "FAILSAFE":
            print("!!! FAILSAFE ON !!!")
            self.control_mode = "FAILSAFE"

        # Retour en mode NORMAL (une seule fois)
        if not triggered and self.control_mode == "FAILSAFE":
            print("Failsafe OFF")
            self.control_mode = "NORMAL"
            return False  # indique qu'on vient de quitter le failsafe

        # Retourne True si on est actuellement en failsafe
        return self.control_mode == "FAILSAFE"