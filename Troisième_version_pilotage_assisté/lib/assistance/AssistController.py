# Fichier : lib/assistance/AssistController.py

class AssistController:

    def __init__(self, stabilizer):
        # Objet responsable de calculer les corrections (roll/pitch)
        self.stabilizer = stabilizer

        # Zone autour du neutre où l'assistance "débutant" est active
        self.BEGINNER_RANGE = 200

        # Limites du taux de débattement des servos
        self.MIN_RATE = 0.5
        self.MAX_RATE = 1.0

        # Exponentiel pour adoucir les mouvements autour du centre
        self.EXPO = 0.3

        # Canal radio utilisé pour activer/moduler l'assistance
        self.ASSIST_CHANNEL = 5
        self.ASSIST_THRESHOLD = 1900  # seuil d’activation

        self.assist_active = False  # état interne

        # Mapping des canaux (index dans la liste channels)
        self.CH_ROLL = 0
        self.CH_PITCH = 1
        self.CH_YAW = 3
        self.CH_THROTTLE = 2

    # =========================
    # LIMITATION
    # =========================
    def get_beginner_strength(self, channels):
        """
        Calcule la force de l'assistance "débutant"
        Plus le stick est proche du neutre (1500), plus l'assistance est forte.
        """
        ch = channels[self.ASSIST_CHANNEL]
        distance = abs(ch - 1500)

        # Si on est en dehors de la zone, pas d’assistance
        if distance >= self.BEGINNER_RANGE:
            return 0

        # Retourne une valeur entre 0 et 1
        return 1 - (distance / self.BEGINNER_RANGE)

    def get_dynamic_limit(self, channels):
        """
        Calcule une limite dynamique du débattement
        Plus l’assistance est forte, plus on limite les mouvements
        """
        strength = self.get_beginner_strength(channels)
        return self.MAX_RATE - (self.MAX_RATE - self.MIN_RATE) * strength

    def limit_servo_travel(self, pulse, centre, limit):
        """
        Applique :
        - un expo (courbe non linéaire)
        - une limitation du débattement
        """
        # Normalisation autour du centre (-1 à 1)
        x = (pulse - centre) / 500

        # Application de l'exponentiel (adoucir autour du centre)
        x = x**3 * self.EXPO + x * (1 - self.EXPO)

        # Application de la limite
        x *= limit

        # Retour en valeur PWM
        return centre + x * 500

    def apply_limit(self, pulse, centre, channels):
        """
        Point unique de limitation (utilisé partout)
        """

        limit = self.get_dynamic_limit(channels)

        # expo + limitation
        x = (pulse - centre) / 500
        x = x**3 * self.EXPO + x * (1 - self.EXPO)
        x *= limit

        return centre + x * 500

    # =========================
    # ASSIST
    # =========================
    def compute(self, channels, devices, current_outputs, use_radio=True):
        """
        Fonction principale :
        - applique les corrections du stabilizer
        - limite les débattements si assistance active
        - génère les sorties finales (PWM)
        """

        # Détection activation
        if not self.assist_active:
            print("ASSIST ON")
            self.assist_active = True

        outputs = []

        # Récupération des corrections (roll, pitch)
        corr = self.stabilizer.update(adaptive=True)

        # Si pas de correction dispo → fallback mode normal
        if corr is None:
            return None

        corr_roll, corr_pitch = corr

        # Calcul de la limite dynamique
        limit = self.get_dynamic_limit(channels)

        # Parcours de tous les dispositifs (servos / moteurs)
        for i, (device, channel) in enumerate(devices):

            # Lecture de la commande radio ou valeur par défaut
            if use_radio:
                pulse = channels[channel]
            else:
                # Sécurité : throttle à 0, autres au neutre
                pulse = 1000 if channel == self.CH_THROTTLE else device.centre

            # Application des corrections stabilisées
            if channel == self.CH_ROLL:
                pulse -= corr_roll * 1.2

            elif channel == self.CH_PITCH:
                pulse += corr_pitch * 1.2

            # Limitation des débattements (sauf throttle)
            if channel != self.CH_THROTTLE:
                if use_radio:
                    pulse = self.apply_limit(pulse, device.centre, channels)

            # Sécurité : coupe le throttle si trop bas
            if channel == self.CH_THROTTLE and pulse < 1100:
                pulse = 1000

            # Clamp des valeurs PWM (1000 - 2000 µs)
            pulse = max(1000, min(2000, pulse))

            # Anti-jitter :
            # évite de petites variations inutiles (stabilise les servos)
            if abs(pulse - current_outputs[i]) < 2:
                pulse = current_outputs[i]

            outputs.append(pulse)

        return outputs