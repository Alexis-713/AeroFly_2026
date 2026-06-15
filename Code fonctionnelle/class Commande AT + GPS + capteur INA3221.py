from machine import UART, I2C, Pin
import time


# =========================
# LoRaWAN Wio-E5
# =========================
class LoRaWAN:
    def __init__(self, uart_id=1, baudrate=9600, tx=43, rx=44, appkey=""):
        self.uart = UART(uart_id, baudrate=baudrate, tx=tx, rx=rx)
        self.appkey = appkey

    def send_cmd(self, cmd, wait=1):
        print(">>", cmd)
        self.uart.write(cmd + "\r\n")
        time.sleep(wait)

        response = ""
        while self.uart.any():
            try:
                response += self.uart.read().decode()
            except:
                pass

        print(response)
        return response

    def join(self):
        self.send_cmd("AT+MODE=LWOTAA")
        self.send_cmd("AT+ID=DevEui")
        self.send_cmd("AT+ID=AppEui")
        self.send_cmd('AT+KEY=APPKEY,"{}"'.format(self.appkey))

        join_response = self.send_cmd("AT+JOIN", 5)

        if (
            "JOINED" in join_response
            or "Join Success" in join_response
            or "NORMAL" in join_response
        ):
            print("Connecte au reseau LoRaWAN")
            return True

        print("Erreur JOIN")
        return False

    def send_message(self, payload):
        cmd = 'AT+MSG="{}"'.format(payload)
        return self.send_cmd(cmd, 2)


# =========================
# Gravity GNSS GPS BeiDou
# =========================
class GravityGNSS:
    def __init__(self, i2c, address=0x66):
        self.i2c = i2c
        self.address = address

    def read_reg(self, reg, length):
        try:
            self.i2c.writeto(self.address, bytes([reg]))
            return list(self.i2c.readfrom(self.address, length))
        except:
            return None

    def get_lat(self):
        data = self.read_reg(7, 6)

        if data:
            dd = data[0]
            mm = data[1]
            mmmmm = (data[2] << 16) | (data[3] << 8) | data[4]

            lat = dd + (mm + mmmmm / 100000.0) / 60.0
            return abs(lat)  # France = Nord

        return None

    def get_lon(self):
        data = self.read_reg(13, 6)

        if data:
            ddd = data[0]
            mm = data[1]
            mmmmm = (data[2] << 16) | (data[3] << 8) | data[4]

            lon = ddd + (mm + mmmmm / 100000.0) / 60.0
            return -abs(lon)  # France = Ouest

        return None

    def get_sat(self):
        data = self.read_reg(19, 1)
        return data[0] if data else 0

    def get_position(self):
        return self.get_lat(), self.get_lon(), self.get_sat()


# =========================
# INA3221
# =========================
class INA3221:
    POSSIBLE_ADDRESSES = [0x40, 0x41, 0x42, 0x43]

    BUS_VOLTAGE_REGISTERS = {
        1: 0x02,
        2: 0x04,
        3: 0x06
    }

    def __init__(self, i2c, address=None):
        self.i2c = i2c
        self.address = address

        if self.address is None:
            self.address = self.detect()

        if self.address is None:
            print("INA3221 non detecte")
        else:
            print("INA3221 pret a l'adresse :", hex(self.address))

    def detect(self):
        devices = self.i2c.scan()
        print("I2C detectes :", [hex(d) for d in devices])

        for addr in self.POSSIBLE_ADDRESSES:
            if addr in devices:
                try:
                    self.i2c.readfrom_mem(addr, 0x00, 2)
                    print("INA3221 detecte a :", hex(addr))
                    return addr
                except:
                    pass

        return None

    def is_available(self):
        return self.address is not None

    def read_register(self, reg):
        if not self.is_available():
            return None

        try:
            data = self.i2c.readfrom_mem(self.address, reg, 2)
            return (data[0] << 8) | data[1]
        except:
            return None

    def read_bus_voltage(self, channel):
        if channel not in self.BUS_VOLTAGE_REGISTERS:
            return None

        raw = self.read_register(self.BUS_VOLTAGE_REGISTERS[channel])

        if raw is None:
            return None

        # LSB = 8 mV
        voltage = (raw >> 3) * 0.008
        return voltage

    def read_all_voltages(self):
        return (
            self.read_bus_voltage(1),
            self.read_bus_voltage(2),
            self.read_bus_voltage(3)
        )


# =========================
# Application principale
# =========================
class TrackerApp:
    def __init__(self):
        self.lora = LoRaWAN(
            uart_id=1,
            baudrate=9600,
            tx=43,
            rx=44,
            appkey="333D6E1042EAE4AF0E1EEC2EF2A3F401"
        )

        self.i2c = I2C(
            0,
            scl=Pin(4),
            sda=Pin(5),
            freq=100000
        )

        self.gps = GravityGNSS(self.i2c, address=0x66)
        self.ina3221 = INA3221(self.i2c)

    def start(self):
        if not self.lora.join():
            while True:
                time.sleep(5)

        print("LoRa connecte")

        while True:
            self.loop()
            time.sleep(10)

    def loop(self):
        lat, lon, sat = self.gps.get_position()
        v1, v2, v3 = self.ina3221.read_all_voltages()

        print("Lat:", lat, "Lon:", lon, "Sat:", sat)
        print("Voltages:", v1, v2, v3)

        if lat is not None and lon is not None:
            batterie = v1 if v1 is not None else 0

            payload = (
                "GPS:{:.5f};{:.5f}, "
                "batterie:{:.2f}V, "
                "temperature: C, "
                "humidite: %, "
                "pression: hPa, "
                "vitesse d'air/ de l'avion: , "
            ).format(lat, lon, batterie)

            self.lora.send_message(payload)

        print("-" * 40)


# =========================
# Lancement
# =========================
app = TrackerApp()
app.start()