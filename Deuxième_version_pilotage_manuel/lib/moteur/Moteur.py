# Fichier : lib/moteur/Moteur.py

# Import du module PWM (génération de signal) depuis machine
from machine import PWM
import time

class Moteur():
    """
    Classe générique pour Servo et ESC (contrôleur de moteur brushless).
    Sert de base commune pour gérer les signaux PWM.
    """

    def __init__(self, pwm: PWM, min_v=1000, max_v=2000):
        # Objet PWM utilisé pour piloter le moteur / servo
        self.pwm = pwm

        # Valeur minimale du pulse (en microsecondes)
        # Correspond généralement à la position minimale ou arrêt
        self.min = min_v
        # Valeur maximale du pulse (en microsecondes)
        # Correspond généralement à la position maximale ou puissance max
        self.max = max_v

    def limite(self, pulse):
        """
        Limite la valeur du pulse dans l'intervalle autorisé.
        Évite d'envoyer des valeurs dangereuses au matériel.
        """

        # max(self.min, ...) empêche d'aller sous la valeur minimale
        # min(self.max, ...) empêche de dépasser la valeur maximale
        return max(self.min, min(self.max, pulse))

    def update(self, pulse):
        """
        Méthode générique pour mettre à jour le moteur.
        Doit être redéfinie (override) dans les classes enfants
        comme Servo ou ESC.
        """

        # Si une classe enfant ne redéfinit pas cette méthode,
        # une erreur explicite est levée
        raise NotImplementedError("update() doit être implémenté dans la classe fille")

