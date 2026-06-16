# Import de la classe de base Moteur
from .Moteur import Moteur
import time

# Classe ESC (Electronic Speed Controller)
# Permet de contrôler la vitesse d'un moteur brushless via PWM
class ESC(Moteur):

    def __init__(self, pwm, min_v=1000, max_v=2000, freq=50, arm_sequence=True):
        # Initialisation de la classe parent (PWM + limites)
        super().__init__(pwm, min_v, max_v)

        # Fréquence du signal PWM 
        self.freq = freq

        # Indique si l'ESC est armé
        self.armed = False
        # Lance automatiquement la séquence d'armement si demandé
        if arm_sequence:
            self.arm()

    def pulse_to_duty(self, pulse):
        """Convertit une impulsion (µs) en duty cycle (0–65535)"""
        # Calcul de la période en microsecondes
        # ex : 50 Hz → 20 000 µs
        period_us = 1_000_000 / self.freq
        # Conversion proportionnelle vers une valeur 16 bits
        return int((pulse / period_us) * 65535)

    def set_us(self, us):
        """Applique directement une valeur en microsecondes au PWM"""

        # Sécurise la valeur dans les limites autorisées
        us = self.limite(us)
        # Conversion en duty cycle
        duty = self.pulse_to_duty(us)
        # Envoi au module PWM
        self.pwm.duty_u16(duty)

    def arm(self):
        """Séquence d'armement classique d'un ESC
        # (dépend du modèle mais souvent min → max → min)"""

        print("Arming ESC...")
        # Signal minimum (sécurité / arrêt)
        self.set_us(self.min)
        time.sleep(1.0)
        # Signal maximum (calibration)
        self.set_us(self.max)
        time.sleep(1.0)
        # Retour au minimum (prêt à fonctionner)
        self.set_us(self.min)
        time.sleep(1.0)
        # Marque l'ESC comme armé
        self.armed = True

        print("ESC armé")

    def update(self, pulse):
        """Met à jour la vitesse du moteur"""

        # Sécurité : ne fait rien si l'ESC n'est pas armé
        if not self.armed:
            return
        # Limite la valeur du signal
        pulse = self.limite(pulse)
        # Applique la commande au moteur
        self.set_us(pulse)

