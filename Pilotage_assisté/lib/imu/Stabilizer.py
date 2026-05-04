# Fichier : lib/imu/Stabilizer.py

from machine import I2C, Pin
import time
from bno055 import BNO055


class Stabilizer:

    def __init__(self, scl=48, sda=47, freq=100000):

        self.i2c = I2C(0, scl=Pin(scl), sda=Pin(sda), freq=freq)

        self.imu = None
        self.init_imu()

        # PID (à ajuster en vol)
        self.Kp_roll = 1.0
        self.Kd_roll = 0.5

        self.Kp_pitch = 1.0
        self.Kd_pitch = 0.5

        # Inversion axes (IMPORTANT)
        self.roll_sign = -1
        self.pitch_sign = -1

        self.prev_roll = 0
        self.prev_pitch = 0

        self.roll_f = 0
        self.pitch_f = 0
        self.alpha = 0.7

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

    def update(self):

        if self.imu is None:
            self.init_imu()
            return None

        try:
            heading, roll, pitch = self.imu.euler()

            if roll is None or pitch is None:
                raise Exception("Invalid IMU")

            if abs(roll) > 180 or abs(pitch) > 180:
                raise Exception("Glitch")

            self.last_valid_time = time.ticks_ms()

        except:
            print("IMU ERROR → reinit")
            time.sleep(0.2)
            self.init_imu()
            return None

        if time.ticks_diff(time.ticks_ms(), self.last_valid_time) > 500:
            print("IMU TIMEOUT")
            return None

        # Filtre
        self.roll_f = self.alpha * self.roll_f + (1 - self.alpha) * roll
        self.pitch_f = self.alpha * self.pitch_f + (1 - self.alpha) * pitch

        # Erreurs avec correction axes
        err_roll = -self.roll_f * self.roll_sign
        err_pitch = -self.pitch_f * self.pitch_sign

        d_roll = self.roll_f - self.prev_roll
        d_pitch = self.pitch_f - self.prev_pitch

        self.prev_roll = self.roll_f
        self.prev_pitch = self.pitch_f

        corr_roll = self.Kp_roll * err_roll - self.Kd_roll * d_roll
        corr_pitch = self.Kp_pitch * err_pitch - self.Kd_pitch * d_pitch

        return corr_roll, corr_pitch