# Fichier : lib/moteur/IbusServoController.py

from machine import UART, Pin, PWM
import time

from lib.moteur.Servo import Servo
from lib.moteur.ESC import ESC
from lib.imu.Stabilizer import Stabilizer


class IBusServoController:

    FRAME_LENGTH = 32
    CHANNEL_COUNT = 14

    def __init__(self, config):

        conn = config["connexion"]

        self.uart = UART(
            1,
            baudrate=conn["baudrate"],
            bits=conn["bits"],
            parity=conn["parity"],
            stop=conn["stop"],
            rx=conn["pin_rx"]
        )

        self.frame = bytearray(self.FRAME_LENGTH)
        self.channels = [1500] * self.CHANNEL_COUNT
        self.index = 0
        self.last_frame_time = time.ticks_ms()

        # FAILSAFE
        self.FAILSAFE_CHANNEL = 4
        self.FAILSAFE_THRESHOLD = 1900
        self.FAILSAFE_TIMEOUT = 500

        self.failsafe_active = False

        # ASSIST
        self.ASSIST_CHANNEL = 5
        self.ASSIST_THRESHOLD = 1900
        self.assist_active = False

        # Stabilizer
        self.stabilizer = Stabilizer()

        self.devices = []
        self.current_outputs = [1500] * self.CHANNEL_COUNT

        # Mapping propre
        self.CH_ROLL = 0
        self.CH_PITCH = 1
        self.CH_YAW = 3
        self.CH_THROTTLE = 2

        for name, moteur in config["moteur"].items():

            pwm = PWM(Pin(moteur["pin"]), freq=moteur["frequence"])
            moteur_type = moteur.get("type", "servo")

            if moteur_type == "servo":
                device = Servo(
                    pwm,
                    moteur["etat_actif_min"],
                    moteur["etat_actif_max"],
                    moteur.get("centre", 1500),
                    moteur["frequence"]
                )

            elif moteur_type == "esc":
                device = ESC(
                    pwm,
                    moteur["etat_actif_min"],
                    moteur["etat_actif_max"],
                    moteur["frequence"]
                )
                device.arm()

            else:
                raise ValueError("Type inconnu")

            channel = moteur.get("channel", 1) - 1
            self.devices.append((device, channel))

        time.sleep(1)
        #self.startup_test()
    # =========================
    # IBUS
    # =========================

    def validate(self):
        checksum = 0xFFFF
        for i in range(30):
            checksum -= self.frame[i]

        received = self.frame[30] | (self.frame[31] << 8)
        return checksum == received

    def read_ibus(self):
        data = self.uart.read()
        if not data:
            return False

        for byte in data:

            if self.index == 0 and byte != 0x20:
                continue

            if self.index == 1 and byte != 0x40:
                self.index = 0
                continue

            self.frame[self.index] = byte
            self.index += 1

            if self.index == self.FRAME_LENGTH:

                self.index = 0

                if not self.validate():
                    return False

                for i in range(self.CHANNEL_COUNT):
                    low = self.frame[2 + i*2]
                    high = self.frame[3 + i*2]
                    self.channels[i] = low | (high << 8)

                self.last_frame_time = time.ticks_ms()
                return True

        return False

    # =========================
    # FAILSAFE AVEC STABILISATION
    # =========================

    def failsafe(self):

        now = time.ticks_ms()

        channel_triggered = self.channels[self.FAILSAFE_CHANNEL] >= self.FAILSAFE_THRESHOLD
        signal_lost = time.ticks_diff(now, self.last_frame_time) > self.FAILSAFE_TIMEOUT

        if channel_triggered or signal_lost:

            if not self.failsafe_active:
                print("!!! FAILSAFE ACTIVÉ !!!")
                self.failsafe_active = True

            corr = self.stabilizer.update()

            for i, (device, channel) in enumerate(self.devices):

                pulse = self.current_outputs[i]

                # Stabilisation seulement sur roll/pitch
                if corr is not None:

                    corr_roll, corr_pitch = corr

                    if channel == self.CH_ROLL:
                        pulse -= corr_roll * 1.5

                    elif channel == self.CH_PITCH:
                        pulse += corr_pitch * 1.5

                # Pas de modification throttle ni yaw

                pulse = max(1200, min(1800, pulse))

                self.current_outputs[i] = pulse
                device.update(pulse)

            return True

        else:
            if self.failsafe_active:
                print("Failsafe désactivé")
                self.failsafe_active = False

        return False

    # =========================
    # ASSIST
    # =========================

    def assist_control(self):

        if not self.assist_active:
            print("ASSIST ON")
            self.assist_active = True

        corr = self.stabilizer.update()

        if corr is None:
            self.update_outputs()
            return

        corr_roll, corr_pitch = corr

        for i, (device, channel) in enumerate(self.devices):

            pulse = self.channels[channel]

            if channel == self.CH_ROLL:
                pulse -= corr_roll * 1.5

            elif channel == self.CH_PITCH:
                pulse += corr_pitch * 1.5

            pulse = max(1200, min(1800, pulse))

            self.current_outputs[i] = pulse
            device.update(pulse)

    # =========================
    # NORMAL
    # =========================

    def update_outputs(self):
        for i, (device, channel) in enumerate(self.devices):

            pulse = self.channels[channel]

            # évite updates inutiles
            if abs(pulse - self.current_outputs[i]) < 2:
                continue

            self.current_outputs[i] = pulse
            device.update(pulse)

    # =========================
    # LOOP
    # =========================

    def run(self):

        while True:

            self.read_ibus()

            if not self.failsafe():

                if self.channels[self.ASSIST_CHANNEL] > self.ASSIST_THRESHOLD:
                    self.assist_control()
                else:
                    if self.assist_active:
                        print("ASSIST OFF")
                        self.assist_active = False

                    self.update_outputs()

                print(self.channels[:6])

            time.sleep_ms(20)