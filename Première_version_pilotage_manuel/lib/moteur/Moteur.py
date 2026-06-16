# lib/moteur/Moteur.py
from machine import PWM
import time

class Moteur():
    """Classe générique pour Servo et ESC."""

    def __init__(self, pwm: PWM, min_v=1000, max_v=2000):
        self.pwm = pwm
        self.min = min_v
        self.max = max_v

    def limite(self, pulse):
        """Limite le pulse entre min et max."""
        return max(self.min, min(self.max, pulse))

    def update(self, pulse):
        """Doit être surchargé par les classes filles."""
        raise NotImplementedError("update() doit être implémenté dans la classe fille")