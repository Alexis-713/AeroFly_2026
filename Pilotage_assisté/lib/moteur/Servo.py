# Fichier : lib/moteur/Servo.py

# Import de la classe de base Moteur
from .Moteur import Moteur

# Classe Servo héritant de Moteur
# Représente un servo-moteur piloté en PWM
class Servo(Moteur):

    def __init__(self, pwm, min_v=1000, max_v=2000, centre=1500, freq=50):
        # Appel du constructeur de la classe parent (Moteur)
        # Initialise le PWM + les limites min/max du signal
        super().__init__(pwm, min_v, max_v)

        # Valeur de position centrale du servo 
        self.centre = centre
        # Fréquence du signal PWM
        self.freq = freq

    def update(self, pulse):
        """Met à jour la position du servo"""
        # Sécurise la valeur du pulse (reste entre min_v et max_v)
        pulse = self.limite(pulse)

        # Convertit le pulse (µs) en duty cycle compatible PWM (0–65535)
        duty = self.pulse_to_duty(pulse)
        # Applique le duty cycle au module PWM
        self.pwm.duty_u16(duty)

    def pulse_to_duty(self, pulse):
        """Convertit une durée d'impulsion (en microsecondes)
        en valeur de duty cycle pour un PWM 16 bits"""

        # Calcul de la période du signal en microsecondes
        # (ex: 50 Hz → 20 000 µs)
        period_us = 1_000_000 / self.freq
        # Conversion :
        # rapport (pulse / période) → valeur sur 16 bits (0 à 65535)
        return int((pulse / period_us) * 65535)