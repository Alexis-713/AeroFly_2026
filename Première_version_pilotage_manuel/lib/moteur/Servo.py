# lib/moteur/Servo.py
from .Moteur import Moteur

class Servo(Moteur):
    def __init__(self, pwm, min_v=1000, max_v=2000, centre=1500):
        super().__init__(pwm, min_v, max_v)
        self.centre = centre

    def update(self, pulse):
        pulse = self.limite(pulse)
        duty = self.pulse_to_duty(pulse)
        self.pwm.duty_u16(duty)

    @staticmethod
    def pulse_to_duty(pulse):
        min_duty = 1638   # ~1000 µs
        max_duty = 8192   # ~2000 µs
        scale = (max_duty - min_duty) / 1000
        return int(min_duty + (pulse - 1000) * scale)