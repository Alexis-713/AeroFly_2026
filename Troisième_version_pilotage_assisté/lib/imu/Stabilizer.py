from machine import I2C, Pin
import time
from lib.imu.bno055 import BNO055


class Stabilizer:

    def __init__(self, scl=48, sda=47, freq=100_000):
        """
        Initialise la communication I2C et les paramètres du stabilisateur
        """

        # Initialisation du bus I2C pour communiquer avec l'IMU
        self.i2c = I2C(0, scl=Pin(scl), sda=Pin(sda), freq=freq)

        # Objet IMU (sera initialisé ensuite)
        self.imu = None
        self.init_imu()

        # =========================
        # PARAMÈTRES PID 
        # =========================

        self.Kp_roll = 4.0
        self.Kd_roll = 0.2

        self.Kp_pitch = 4.0
        self.Kd_pitch = 0.2

        # =========================
        # ORIENTATION DES AXES
        # =========================

        self.roll_sign = -1
        self.pitch_sign = -1

        # =========================
        # MÉMOIRE (pour dérivée)
        # =========================

        self.prev_roll = 0
        self.prev_pitch = 0

        # =========================
        # FILTRE BASSE PASSE
        # =========================

        self.roll_f = 0
        self.pitch_f = 0

        self.alpha = 0.5

        # =========================
        # SORTIE LISSÉE
        # =========================

        self.out_roll = 0
        self.out_pitch = 0
        self.output_smooth = 0.45

        # =========================
        # LIMITES
        # =========================

        self.max_angle = 250

        # =========================
        # DEADZONE
        # =========================

        self.deadband = 0.5

        # =========================
        # MODE ADAPTATIF IMU
        # =========================

        self.adaptive_min_gain = 1.0
        self.adaptive_max_gain = 3.0
        self.adaptive_angle_ref = 15  # sensibilité de montée du gain

        # =========================
        # CALIBRATION
        # =========================

        self.roll_offset = 0
        self.pitch_offset = 0
        self.calibrated = False
        
        # =========================
        # DESCENTE (FAILSAFE / AUTO LANDING)
        # =========================
        self.target_pitch = 0
        
        # Timestamp
        self.last_valid_time = time.ticks_ms()

    def init_imu(self):
        try:
            self.imu = BNO055(self.i2c)
            time.sleep(1)
            self.imu.mode(0x0C)
            time.sleep(1)
            print("IMU OK")
        except:
            print("IMU init failed")
            self.imu = None

    def clamp(self, value, min_val, max_val):
        return max(min(value, max_val), min_val)

    def calibrate(self, samples=50):
        """
        Calibration manuelle (appelée depuis la radio)
        """
        sum_roll = 0
        sum_pitch = 0
        count = 0

        print("Calibration IMU... NE PAS BOUGER")

        while count < samples:
            try:
                _, roll, pitch = self.imu.euler()

                if roll is not None and pitch is not None:
                    sum_roll += roll
                    sum_pitch += pitch
                    count += 1

                time.sleep(0.02)

            except:
                pass

        self.roll_offset = sum_roll / samples
        self.pitch_offset = sum_pitch / samples
        self.calibrated = True

        print("Calibration OK")

    # =========================
    # GAIN ADAPTATIF IMU
    # =========================

    def get_adaptive_gain(self):
        """
        Gain dynamique basé sur l'inclinaison réelle de l'avion
        """

        angle = max(abs(self.roll_f), abs(self.pitch_f))

        if angle < 1:
            return 1.0

        gain = 1.0 + (angle / self.adaptive_angle_ref)

        return self.clamp(
            gain,
            self.adaptive_min_gain,
            self.adaptive_max_gain
        )

    # =========================
    # UPDATE IMU
    # =========================

    def update(self, adaptive=True):

        if self.imu is None:
            self.init_imu()
            return None

        try:
            _, roll, pitch = self.imu.euler()

            if roll is None or pitch is None:
                raise Exception()

            if abs(roll) > 180 or abs(pitch) > 180:
                raise Exception()

            self.last_valid_time = time.ticks_ms()

        except:
            print("IMU ERROR → reinit")
            time.sleep(0.2)
            self.init_imu()
            return None

        if time.ticks_diff(time.ticks_ms(), self.last_valid_time) > 500:
            print("IMU TIMEOUT")
            return None

        # =========================
        # APPLICATION OFFSET
        # =========================

        roll -= self.roll_offset
        pitch -= self.pitch_offset

        # =========================
        # FILTRE
        # =========================

        self.roll_f = self.alpha * self.roll_f + (1 - self.alpha) * roll
        self.pitch_f = self.alpha * self.pitch_f + (1 - self.alpha) * pitch

        # =========================
        # ERREURS
        # =========================

        err_roll = -self.roll_f * self.roll_sign

        # ajout du biais de descente
        err_pitch = (self.target_pitch - self.pitch_f) * self.pitch_sign
        
        # DEADZONE
        if abs(err_roll) < self.deadband:
            err_roll = 0

        if abs(err_pitch) < self.deadband:
            err_pitch = 0

        # =========================
        # DERIVEE
        # =========================

        d_roll = self.roll_f - self.prev_roll
        d_pitch = self.pitch_f - self.prev_pitch

        self.prev_roll = self.roll_f
        self.prev_pitch = self.pitch_f

        # =========================
        # PID
        # =========================

        corr_roll = self.Kp_roll * err_roll - self.Kd_roll * d_roll
        corr_pitch = self.Kp_pitch * err_pitch - self.Kd_pitch * d_pitch

        # =========================
        # GAIN ADAPTATIF IMU
        # =========================

        if adaptive:
            gain = self.get_adaptive_gain()
            corr_roll *= gain
            corr_pitch *= gain

        # =========================
        # LIMITES
        # =========================

        corr_roll = self.clamp(corr_roll, -self.max_angle, self.max_angle)
        corr_pitch = self.clamp(corr_pitch, -self.max_angle, self.max_angle)
        
        # =========================
        # LISSAGE SORTIE
        # =========================

        self.out_roll = self.output_smooth * self.out_roll + (1 - self.output_smooth) * corr_roll
        self.out_pitch = self.output_smooth * self.out_pitch + (1 - self.output_smooth) * corr_pitch

        return self.out_roll, self.out_pitch