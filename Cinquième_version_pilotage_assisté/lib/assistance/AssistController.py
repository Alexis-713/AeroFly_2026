# Fichier : lib/assistance/AssistController.py

class AssistController:

    def __init__(self, stabilizer):
        # Objet responsable de calculer les corrections (roll/pitch)
        self.stabilizer = stabilizer

        # Limites du taux de débattement des servos
        self.MIN_RATE = 0.45
        self.MID_RATE = 0.7
        self.MAX_RATE = 1.0
        
        
        self.IMU_GAIN_DEBUTANT = 1.7
        self.IMU_GAIN_INTERMEDIAIRE = 1.3
        self.IMU_GAIN_EXPERT = 1.0

        self.RATE_CHANNEL = 8  # canal 9 => index 8
        
        # Exponentiel pour adoucir les mouvements autour du centre
        self.EXPO = 0.3
        
        # Deadzone
        self.PILOT_OVERRIDE = 200
        
        self.assist_active = False  # état interne
        
        # Mapping des canaux (index dans la liste channels)
        self.CH_ROLL = 0
        self.CH_PITCH = 1
        self.CH_YAW = 3
        self.CH_THROTTLE = 2
        
        self.LIMITED_CHANNELS = (self.CH_ROLL,self.CH_PITCH)
    # =========================
    # SELECTION DU MODE
    # =========================

    def __get_rate_limit(self, channels):
        """
        Retourne le taux de débattement
        selon la position de CH9.
        """
        ch = channels[self.RATE_CHANNEL]

        if ch < 1250:
            return self.MIN_RATE      # Débutant
        elif ch < 1750:
            return self.MID_RATE      # Intermédiaire
        else:
            return self.MAX_RATE      # Expert
    
    def __get_imu_gain(self, channels):
        ch = channels[self.RATE_CHANNEL]

        if ch < 1250:
            return self.IMU_GAIN_DEBUTANT

        elif ch < 1750:
            return self.IMU_GAIN_INTERMEDIAIRE

        else:
            return self.IMU_GAIN_EXPERT
        
    def get_current_rate(self, channels):
        return self.__get_rate_limit(channels)
    
    # =========================
    # LIMITATION
    # =========================
    def apply_limit(self, pulse, centre, limit):
        """
        Point unique de limitation (utilisé partout)
        """

        # expo + limitation
        x = (pulse - centre) / 500
        x = x**3 * self.EXPO + x * (1 - self.EXPO)
        x *= limit

        return centre + x * 500

    # =========================
    # ASSIST
    # =========================
    def compute(self, channels, devices, current_outputs, motor_locked=False, use_radio=True):
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
        
        limit = self.__get_rate_limit(channels)
        imu_gain = self.__get_imu_gain(channels)
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
                if abs(channels[self.CH_ROLL] - 1500) < self.PILOT_OVERRIDE:
                    pulse -= corr_roll * 1.2 * imu_gain

            elif channel == self.CH_PITCH:
                if abs(channels[self.CH_PITCH] - 1500) < self.PILOT_OVERRIDE:
                    pulse += corr_pitch * 1.2 * imu_gain
            
            if channel in self.LIMITED_CHANNELS:
                pulse = self.apply_limit(
                    pulse,
                    device.centre,
                    limit
                )
                
            # Sécurité moteur
            if channel == self.CH_THROTTLE:

                if motor_locked:
                    pulse = 1000

            # Clamp des valeurs PWM (1000 - 2000 µs)
            pulse = max(1000, min(2000, pulse))

            # Anti-jitter :
            # évite de petites variations inutiles (stabilise les servos)
            if abs(pulse - current_outputs[i]) < 2:
                pulse = current_outputs[i]

            outputs.append(pulse)

        return outputs