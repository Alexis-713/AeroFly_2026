from machine import UART, I2C, Pin
import time
import random


# =========================
# CLASSE LoRa
# =========================
class LoRa:
    def __init__(self, uart_id=1, baudrate=9600, tx=43, rx=44):
        self.uart = UART(uart_id, baudrate=baudrate, tx=tx, rx=rx)

    def send_cmd(self, cmd, wait=1):
        print(">>", cmd)
        self.uart.write(cmd + "\r\n")
        time.sleep(wait)
        response = ""
        while self.uart.any():
            response += self.uart.read().decode()
        print(response)
        return response

    def init(self, app_key):
        self.send_cmd("AT+MODE=LWOTAA")
        self.send_cmd("AT+DR=EU868")
        self.send_cmd("AT+CH=NUM,0-2")
        self.send_cmd("AT+ID=DEVEUI")
        self.send_cmd("AT+ID=APPEUI")
        self.send_cmd(f'AT+KEY=APPKEY,"{app_key}"')
        self.send_cmd("AT+ID")  # vérification

    def join(self):
        response = self.send_cmd("AT+JOIN", 15)
        success = any(kw in response for kw in ("JOINED", "Join Success", "NORMAL"))
        if success:
            print("Connecté au réseau LoRaWAN")
        else:
            print("Erreur JOIN")
        return success

    def send(self, payload, wait=2):
        cmd = f'AT+MSG="{payload}"'
        return self.send_cmd(cmd, wait)


# =========================
# CLASSE GPS
# =========================
class GPS:
    ADDR = 0x66

    def __init__(self, i2c):
        self.i2c = i2c

    def _read_reg(self, reg, length):
        try:
            self.i2c.writeto(self.ADDR, bytes([reg]))
            return list(self.i2c.readfrom(self.ADDR, length))
        except Exception:
            return None

    def get_lat(self):
        data = self._read_reg(7, 6)
        if data:
            dd = data[0]
            mm = data[1]
            mmmmm = (data[2] << 16) | (data[3] << 8) | data[4]
            lat = dd + (mm + mmmmm / 100000.0) / 60.0
            return abs(lat)  # France = Nord
        return None

    def get_lon(self):
        data = self._read_reg(13, 6)
        if data:
            ddd = data[0]
            mm = data[1]
            mmmmm = (data[2] << 16) | (data[3] << 8) | data[4]
            lon = ddd + (mm + mmmmm / 100000.0) / 60.0
            return -abs(lon)  # France = Ouest
        return None

    def get_sat(self):
        data = self._read_reg(19, 1)
        return data[0] if data else 0

    def get_position(self):
        return self.get_lat(), self.get_lon()


# =========================
# CLASSE INA3221
# =========================
class INA3221:
    POSSIBLE_ADDRESSES = [0x40, 0x41, 0x42, 0x43]
    BUS_VOLTAGE_REGS = {1: 0x02, 2: 0x04, 3: 0x06}

    def __init__(self, i2c):
        self.i2c = i2c
        self.addr = self._detect()

    def _detect(self):
        devices = self.i2c.scan()
        print("I2C détectés :", [hex(d) for d in devices])
        for addr in self.POSSIBLE_ADDRESSES:
            if addr in devices:
                try:
                    self.i2c.readfrom_mem(addr, 0x00, 2)
                    print("INA3221 détecté à :", hex(addr))
                    return addr
                except Exception:
                    pass
        return None

    def _read_register(self, reg):
        if self.addr is None:
            self.addr = self._detect()
            if self.addr is None:
                return 0
        try:
            data = self.i2c.readfrom_mem(self.addr, reg, 2)
            return (data[0] << 8) | data[1]
        except Exception as e:
            print("Erreur INA3221:", e)
            self.addr = None  # Force re-détection
            return 0

    def read_bus_voltage(self, channel):
        reg = self.BUS_VOLTAGE_REGS.get(channel)
        if reg is None:
            return 0.0
        raw = self._read_register(reg)
        if raw == 0:
            return 0.0
        return (raw >> 3) * 0.008

    def read_all_voltages(self):
        return {ch: self.read_bus_voltage(ch) for ch in self.BUS_VOLTAGE_REGS}


# =========================
# CLASSE CAPTEURS SIMULÉS
# =========================
class SimulatedSensors:
    def get_temperature(self):
        """Température entre -40 et +85 °C"""
        return round(random.uniform(-40, 85), 2)

    def get_humidity(self):
        """Humidité entre 0 et 100 %"""
        return round(random.uniform(0, 100), 2)

    def get_pressure(self):
        """Pression atmosphérique entre 300 et 1100 hPa"""
        return round(random.uniform(300, 1100), 2)

    def get_air_speed(self):
        """Vitesse d'air simulée (drone/avion) entre 0 et 250 km/h"""
        return round(random.uniform(0, 250), 2)

    def read_all(self):
        return {
            "temperature": self.get_temperature(),
            "humidity":    self.get_humidity(),
            "pressure":    self.get_pressure(),
            "air_speed":   self.get_air_speed(),
        }


# =========================
# INIT
# =========================
lora = LoRa(uart_id=1, baudrate=9600, tx=43, rx=44)
lora.init(app_key="333D6E1042EAE4AF0E1EEC2EF2A3F401")

if not lora.join():
    while True:
        time.sleep(5)

print("LoRa connecté")

i2c = I2C(0, scl=Pin(4), sda=Pin(5), freq=100000)

gps     = GPS(i2c)
ina     = INA3221(i2c)
sensors = SimulatedSensors()

# =========================
# BOUCLE PRINCIPALE
# =========================
while True:
    lat, lon = gps.get_position()
    voltages = ina.read_all_voltages()
    batterie = voltages[1]

    print("Lat:", lat, "Lon:", lon)
    print("Voltages:", voltages)

    if lat and lon:
        time.sleep(5)
        data = sensors.read_all()

        payload = "{:.5f};{:.5f};{:.2f}V;{:.0f}C;{:.0f}%;{:.0f}hPa;{:.0f}km/h".format(
            lat, lon, batterie,
            data["temperature"], data["humidity"],
            data["pressure"],    data["air_speed"],
        )

        lora.send(payload)

    print("-" * 40)
    time.sleep(10)