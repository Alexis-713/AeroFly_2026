# Fichier : lib/moteur/MainController.py

from machine import Pin, PWM
import time

from lib.moteur.Servo import Servo
from lib.moteur.ESC import ESC

from lib.radio.IbusReceiver import IbusReceiver
from lib.assistance.FailsafeManager import FailsafeManager
from lib.assistance.AssistController import AssistController

from lib.imu.Stabilizer import Stabilizer


class MainController:

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
        
        # Canal assistance (SwA)
        self.ASSIST_CHANNEL = 6      # canal 7 => index 6
        self.ASSIST_THRESHOLD = 1500

        # Canal sécurité moteur (SwD)
        self.SAFETY_CHANNEL = 9      # canal 10 => index 9
        self.SAFETY_THRESHOLD = 1100
        
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
    def __handle_calibration(self, channels):

        ch7 = channels[self.ASSIST_CHANNEL]
        now = time.ticks_ms()
        motor_locked = self.__is_motor_locked(channels)
        
        if (ch7 > self.ASSIST_THRESHOLD and motor_locked and channels[self.CH_THROTTLE] < 1100):

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
    # BLOQUER LE MOTEUR
    # =========================
    def __is_motor_locked(self, channels):
        """
        Retourne True si la sécurité moteur est active.
        """
        return channels[self.SAFETY_CHANNEL] < self.SAFETY_THRESHOLD
    # =========================
    # MODE NORMAL (fallback)
    # =========================
    def __update_outputs_normal(self, channels):

        outputs = []

        for i, (device, channel) in enumerate(self.devices):

            if channel in self.assist.LIMITED_CHANNELS:
                limit = self.assist.get_current_rate(channels)
                pulse = self.assist.apply_limit(
                    channels[channel],
                    device.centre,
                    limit)
                
            else:
                pulse = channels[channel]

            
            if channel == self.CH_THROTTLE:

                if self.__is_motor_locked(channels):
                    pulse = 1000
            
            pulse = max(1000, min(2000, pulse))
            
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

            self.__handle_calibration(channels)

            # FAILSAFE
            is_failsafe = self.failsafe.update(
                channels,
                self.receiver.last_frame_time
            )
            
            # =========================
            # LOGIQUE DE VOL
            # =========================
            if is_failsafe:
            
                self.stabilizer.target_pitch -= 0.1
                self.stabilizer.target_pitch = max(-8, self.stabilizer.target_pitch)
                
                outputs = self.assist.compute(
                    channels,
                    self.devices,
                    self.current_outputs,
                    motor_locked=True,
                    use_radio=False)

            else:
                self.stabilizer.target_pitch = 0
                if channels[self.ASSIST_CHANNEL] > self.ASSIST_THRESHOLD:
                    motor_locked = self.__is_motor_locked(channels)
                    outputs = self.assist.compute(
                        channels,
                        self.devices,
                        self.current_outputs,
                        motor_locked=motor_locked,
                        use_radio=True
                    )
                else:
                    self.assist.assist_active = False
                    outputs = None

            # Fallback NORMAL si besoin
            if outputs is None:
                outputs = self.__update_outputs_normal(channels)

            # =========================
            # ENVOI AUX MOTEURS
            # =========================
            for i, ((device, _), pulse) in enumerate(zip(self.devices, outputs)):
                self.current_outputs[i] = pulse
                device.update(pulse)

            print(channels[:10])
            time.sleep_ms(20)