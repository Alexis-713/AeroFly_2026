# Fichier : lib/moteur/Servo.py

# Import de la classe de base Moteur
from .Moteur import Moteur

# Classe Servo héritant de Moteur
# Représente un servo-moteur piloté en PWM
class Servo(Moteur):

    def __init__(self, pwm, min_v=1000, max_v=2000, centre=1500, freq=50, reverse=False):
        # Appel du constructeur de la classe parent (Moteur)
        # Initialise le PWM + les limites min/max du signal
        super().__init__(pwm, min_v, max_v)

        # Valeur de position centrale du servo 
        self.centre = centre
        # Fréquence du signal PWM
        self.freq = freq
        # Position du servomoteur inversé
        self.reverse = reverse
        
    def process_input(self, pulse):
        """
        Applique les transformations sur la consigne :
        - sécurisation
        - inversion éventuelle
        """

        # 1. Sécurise la valeur en entrée
        pulse = self.limite(pulse)

        # 2. Inversion autour du centre si activée
        if self.reverse:
            pulse = 2 * self.centre - pulse

        # 3. Sécurise à nouveau après inversion
        pulse = self.limite(pulse)

        return pulse
    
    def update(self, pulse):
        """Met à jour la position du servo"""
        # Applique la logique reverse si besoin
        pulse = self.process_input(pulse)
        
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