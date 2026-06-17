# Fichier : lib/moteur/IbusServoController.py

from machine import Pin, PWM
import time

from lib.moteur.Servo import Servo
from lib.moteur.ESC import ESC

from lib.radio.IbusReceiver import IbusReceiver
from lib.assistance.FailsafeManager import FailsafeManager
from lib.assistance.AssistController import AssistController

from lib.imu.Stabilizer import Stabilizer


class IBusServoController:

    CHANNEL_COUNT = 14

    def __init__(self, config):

        # Modules séparés
        self.receiver = IbusReceiver(config["connexion"])
        self.failsafe = FailsafeManager()
        self.stabilizer = Stabilizer()
        self.assist = AssistController(self.stabilizer)

        self.devices = []
        self.current_outputs = [1500] * self.CHANNEL_COUNT

        # Calibration
        self.calib_start_time = None
        self.calib_done = False
        self.CALIB_HOLD_TIME = 1000

        # Mapping
        self.CH_THROTTLE = 2
        self.ASSIST_CHANNEL = 5
        self.ASSIST_THRESHOLD = 1900

        # =========================
        # INIT MOTEURS (inchangé)
        # =========================
        for name, moteur in config["moteur"].items():

            pwm = PWM(Pin(moteur["pin"]), freq=moteur["frequence"])
            moteur_type = moteur.get("type", "servo")

            if moteur_type == "servo":
                device = Servo(
                    pwm,
                    moteur["etat_actif_min"],
                    moteur["etat_actif_max"],
                    moteur.get("centre", 1500),
                    moteur["frequence"],
                    moteur["reverse"]
                )

            elif moteur_type == "esc":
                device = ESC(
                    pwm,
                    moteur["etat_actif_min"],
                    moteur["etat_actif_max"],
                    moteur["centre"],
                    moteur["frequence"]
                )
                device.arm()

            else:
                raise ValueError("Type inconnu")

            channel = moteur.get("channel", 1) - 1
            self.devices.append((device, channel))

        time.sleep(1)

    # =========================
    # CALIBRATION
    # =========================
    def handle_calibration(self, channels):

        ch6 = channels[self.ASSIST_CHANNEL]
        now = time.ticks_ms()

        if ch6 > self.ASSIST_THRESHOLD and channels[self.CH_THROTTLE] < 1100:

            if self.calib_start_time is None:
                self.calib_start_time = now

            elif not self.calib_done and time.ticks_diff(now, self.calib_start_time) > self.CALIB_HOLD_TIME:
                print("=== CALIBRATION DEMANDÉE ===")
                self.stabilizer.calibrate()
                self.calib_done = True

        else:
            self.calib_start_time = None
            self.calib_done = False

    # =========================
    # MODE NORMAL (fallback)
    # =========================
    def update_outputs_normal(self, channels):

        outputs = []

        for i, (device, channel) in enumerate(self.devices):

            pulse = pulse = self.assist.apply_limit(
                channels[channel],
                device.centre,
                channels
            )

            # CUT OFF THROTTLE
            if channel == self.CH_THROTTLE and pulse < 1100:
                pulse = 1000

            if abs(pulse - self.current_outputs[i]) < 2:
                pulse = self.current_outputs[i]

            outputs.append(pulse)

        return outputs

    # =========================
    # LOOP
    # =========================
    def run(self):

        while True:

            self.receiver.read()
            channels = self.receiver.channels

            self.handle_calibration(channels)

            # FAILSAFE
            is_failsafe = self.failsafe.update(
                channels,
                self.receiver.last_frame_time
            )

            # Descente progressive
            self.stabilizer.descent_bias *= 0.98

            # =========================
            # LOGIQUE DE VOL
            # =========================
            if is_failsafe:
                outputs = self.assist.compute(
                    channels,
                    self.devices,
                    self.current_outputs,
                    use_radio=False
                )
            else:
                if channels[self.ASSIST_CHANNEL] > self.ASSIST_THRESHOLD:
                    outputs = self.assist.compute(
                        channels,
                        self.devices,
                        self.current_outputs,
                        use_radio=True
                    )
                else:
                    self.assist.assist_active = False
                    outputs = None

            # Fallback NORMAL si besoin
            if outputs is None:
                outputs = self.update_outputs_normal(channels)

            # =========================
            # ENVOI AUX MOTEURS
            # =========================
            for i, ((device, _), pulse) in enumerate(zip(self.devices, outputs)):
                self.current_outputs[i] = pulse
                device.update(pulse)

            print(channels[:6])
            time.sleep_ms(20)
