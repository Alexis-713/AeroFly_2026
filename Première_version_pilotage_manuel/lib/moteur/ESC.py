# lib/moteur/ESC.py
from .Moteur import Moteur
import time

class ESC(Moteur):
    def __init__(self, pwm, min_v=1000, max_v=2000, arm_sequence=True):
        super().__init__(pwm, min_v, max_v)
        self.armed = False
        if arm_sequence:
            self.arm()

    def arm(self):
        print("Arming ESC...")
        self.set_us(self.min)
        time.sleep(1.0)
        self.set_us(self.max)
        time.sleep(1.0)
        self.set_us(self.min)
        time.sleep(1.0)
        self.armed = True
        print("ESC armé")

    def set_us(self, us):
        us = self.limite(us)
        duty = int(us * 1023 / 20000)  # 50 Hz → période 20 ms
        self.pwm.duty(duty)

    def update(self, pulse):
        if not self.armed:
            return
        pulse = self.limite(pulse)
        self.set_us(pulse)