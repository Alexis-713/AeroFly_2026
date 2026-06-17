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

        # Zone de limitation progressive autour de 1500
        self.BEGINNER_RANGE = 200  # ±200 µs autour du centre

        # Limites de débattement (remplacées par RATE)
        self.MIN_RATE = 0.5   # mode intermédiaire
        self.MAX_RATE = 1.0   # libre

        self.EXPO = 0.3       # douceur autour du centre
        
        self.control_mode = "NORMAL"
        # NORMAL / ASSIST / FAILSAFE
        
        # FAILSAFE
        self.FAILSAFE_CHANNEL = 4
        self.FAILSAFE_THRESHOLD = 1900
        self.FAILSAFE_TIMEOUT = 500
        self.failsafe_pitch_target = 1500

        # ASSIST
        self.ASSIST_CHANNEL = 5
        self.ASSIST_THRESHOLD = 1900
        self.assist_active = False

        # Stabilizer
        self.stabilizer = Stabilizer()

        self.devices = []
        self.current_outputs = [1500] * self.CHANNEL_COUNT

        # Calibration par switch
        self.calib_start_time = None
        self.calib_done = False
        self.CALIB_HOLD_TIME = 1000  # ms

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

        # Petite pause avant démarrage
        time.sleep(1)

        # Test optionnel des moteurs
        #self.startup_test()

    # =========================
    # MODE DÉBUTANT PROGRESSIF
    # =========================
    def get_beginner_strength(self):
        ch6 = self.channels[self.ASSIST_CHANNEL]

        distance = abs(ch6 - 1500)

        if distance >= self.BEGINNER_RANGE:
            return 0

        return 1 - (distance / self.BEGINNER_RANGE)

    def get_dynamic_limit(self):
        strength = self.get_beginner_strength()
        return self.MAX_RATE - (self.MAX_RATE - self.MIN_RATE) * strength

    def limit_servo_travel(self, pulse, centre, limit):

        x = (pulse - centre) / 500
        x = x**3 * self.EXPO + x * (1 - self.EXPO)
        x *= limit

        return centre + x * 500

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
    # Test des moteurs au démarrage
    # =========================

    def startup_test(self, delay=1, esc_pulse=1100):
        """
        Test des moteurs :
        - Servo : min → max → centre
        - ESC : rotation lente
        """

        print("=== TEST DE DÉMARRAGE DES MOTEURS ===")

        for device, channel in self.devices:

            # Test Servo
            if isinstance(device, Servo):
                print(f"Test servo canal {channel}")
                device.update(device.min)
                time.sleep(delay)

                device.update(device.max)
                time.sleep(delay)

                device.update(device.centre)
                time.sleep(delay)

            # Test ESC
#             if isinstance(device, ESC):
#                 print(f"Test ESC canal {channel}")
#                 device.update(esc_pulse)
#                 time.sleep(delay * 3)
# 
#                 device.update(device.min)

        print("=== TEST TERMINÉ ===\n")
        time.sleep(delay)

    # =========================
    # FAILSAFE AVEC STABILISATION
    # =========================
    def failsafe(self):

        now = time.ticks_ms()

        signal_lost = time.ticks_diff(now, self.last_frame_time) > self.FAILSAFE_TIMEOUT
        switch_trigger = self.channels[self.FAILSAFE_CHANNEL] >= self.FAILSAFE_THRESHOLD

        triggered = signal_lost or switch_trigger

        if triggered and self.control_mode != "FAILSAFE":
            print("!!! FAILSAFE ON !!!")
            self.control_mode = "FAILSAFE"

        if not triggered and self.control_mode == "FAILSAFE":
            print("Failsafe OFF")
            self.control_mode = "NORMAL"
            return False

        if self.control_mode != "FAILSAFE":
            return False

        # =========================
        # MODE FAILSAFE : IGNORE RADIO
        # =========================

        self.assist_control(use_radio=False)

        # coupure progressive gaz
        for i, (device, channel) in enumerate(self.devices):
            if channel == self.CH_THROTTLE:
                self.current_outputs[i] = 1000
                device.update(1000)

        return True

    # =========================
    # ASSIST
    # =========================
    def assist_control(self, use_radio=True):

        if not self.assist_active:
            print("ASSIST ON")
            self.assist_active = True

        # =========================
        # STABILISATION (adaptatif désactivé en failsafe)
        # =========================
        corr = self.stabilizer.update(adaptive=use_radio)

        if corr is None:
            self.update_outputs()
            return

        corr_roll, corr_pitch = corr

        # =========================
        # LIMITATION DES CORRECTIONS EN FAILSAFE
        # =========================
        
        limit = self.get_dynamic_limit()

        for i, (device, channel) in enumerate(self.devices):

            if use_radio:
                pulse = self.channels[channel]
            else:
                if channel == self.CH_THROTTLE:
                    pulse = 1000  # coupure directe
                else:
                    pulse = device.centre

            if channel == self.CH_ROLL:
                pulse -= corr_roll * 1.2

            elif channel == self.CH_PITCH:
                pulse += corr_pitch * 1.2

            if channel != self.CH_THROTTLE:
                if use_radio and self.channels[self.ASSIST_CHANNEL] < self.ASSIST_THRESHOLD:
                    pulse = self.limit_servo_travel(pulse, device.centre, limit)

            # =========================
            # CUT OFF THROTTLE
            # =========================
            if channel == self.CH_THROTTLE:
                if pulse < 1100:
                    pulse = 1000
        
            pulse = max(1000, min(2000, pulse))

            self.current_outputs[i] = pulse
            device.update(pulse)

    # =========================
    # CALIBRATION
    # =========================
    def handle_calibration(self):

        ch6 = self.channels[self.ASSIST_CHANNEL]
        now = time.ticks_ms()

        if ch6 > self.ASSIST_THRESHOLD and self.channels[self.CH_THROTTLE] < 1100:

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
    # NORMAL
    # =========================
    def update_outputs(self):

        limit = self.get_dynamic_limit()

        for i, (device, channel) in enumerate(self.devices):

            pulse = self.channels[channel]
            if channel != self.CH_THROTTLE:
                if self.channels[self.ASSIST_CHANNEL] < self.ASSIST_THRESHOLD:
                    pulse = self.limit_servo_travel(pulse, device.centre, limit)

            # =========================
            # CUT OFF THROTTLE
            # =========================
            if channel == self.CH_THROTTLE:
                if pulse < 1100:
                    pulse = 1000

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
            self.handle_calibration()

            # FAILSAFE toujours vérifié
            if self.failsafe():
                pass
            else:

                self.stabilizer.descent_bias *= 0.98

                if self.channels[self.ASSIST_CHANNEL] > self.ASSIST_THRESHOLD:
                    self.assist_control()
                else:
                    self.update_outputs()

            print(self.channels[:6])
            time.sleep_ms(20)