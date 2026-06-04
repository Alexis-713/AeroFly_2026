from machine import I2C, Pin
import time


# =========================
# Gravity GNSS GPS BeiDou
# =========================
class GravityGNSS:
    # Adresse I2c du gravity GNSS GPS BeiDou
    GPS_ADDR = 0x66

    # Registres internes du module GPS pour la date et l'heure.
    REG_YEAR_H = 0
    REG_MONTH = 2
    REG_DATE = 3
    REG_HOUR = 4
    REG_MINUTE = 5
    REG_SECOND = 6

    REG_LAT_1 = 7
    REG_LON_1 = 13
    REG_USE_STAR = 19
    REG_ALT_H = 20

    # Forcer en négatif car il n'y a pas de gestion pour le Ouest/Est(negatif/positif)
    SIGN_LON = -1  # Cholet/Chemille = Ouest
    
    REG_GNSS_MODE = 34
    REG_SLEEP_MODE = 35
    REG_RGB_MODE = 36

    def write_reg(self, reg, values):
        try:
            self.i2c.writeto(self.address, bytes([reg]) + bytes(values))
            time.sleep_ms(50)
            return True
        except:
            return False

    def enable_power(self):
        return self.write_reg(self.REG_SLEEP_MODE, [0])

    def set_gnss_all(self):
        # 7 = GPS + BeiDou + GLONASS d'apres la lib DFRobot
        return self.write_reg(self.REG_GNSS_MODE, [7])

    def set_rgb_on(self):
        return self.write_reg(self.REG_RGB_MODE, [0x05])

    def begin(self):
        self.enable_power()
        self.set_gnss_all()
        self.set_rgb_on()

    def __init__(self, i2c, address=GPS_ADDR):
        #Bus partager entre le GPS et le capteur INA3221
        self.i2c = i2c
        self.address = address

    def read_reg(self, reg, length):
        #Envoie l'adresse du registre puis lit le nombre d'octet demander
        try:
            self.i2c.writeto(self.address, bytes([reg]))
            data = self.i2c.readfrom(self.address, length)
            return list(data)
        except:
            return None

    def get_lat(self):
        data = self.read_reg(self.REG_LAT_1, 6)

        if data:
            # Le bit 7 du premier octet indique le signe de la latitude
            sign = -1 if (data[0] & 0x80) else 1

            # Le GPS fournit la latitude en degres + minutes decimales
            dd = data[0] & 0x7F
            mm = data[1]
            mmmmm = (data[2] << 16) | (data[3] << 8) | data[4]

            # Conversion vers des degres decimauux, plus simple a exploiter
            lat = dd + (mm + mmmmm / 100000.0) / 60.0
            return lat * sign

        return None

    def get_lon(self):
        data = self.read_reg(self.REG_LON_1, 6)

        if data:
            # Le GPS fournit la longitude en degres + minutes decimales
            ddd = data[0]
            mm = data[1]
            mmmmm = (data[2] << 16) | (data[3] << 8) | data[4]

            # Conversion en degres decimaux, avec signe negatif pour l'ouest
            lon = ddd + (mm + mmmmm / 100000.0) / 60.0
            return lon * self.SIGN_LON

        return None

    def get_satellites(self):
        data = self.read_reg(self.REG_USE_STAR, 1)

        if data:
            # Nombre de sattelites actuellement utiliser pour le calcul GPS
            return data[0]

        return 0

    def get_altitude(self):
        data = self.read_reg(self.REG_ALT_H, 3)

        if data:
            # Altitude en metres, avec deux chiffres après la virgule
            alt = ((data[0] & 0x7F) << 8 | data[1]) + data[2] / 100.0
            return alt

        return None

    def get_position(self):
        return self.get_lat(), self.get_lon()

    def get_raw_position(self):
        return (
            self.read_reg(self.REG_LAT_1, 6),
            self.read_reg(self.REG_LON_1, 6)
        )


# =========================
# INA3221
# =========================
class INA3221:
    # Adresses I2c possible pour le capteur INA3221
    POSSIBLE_ADDRESSES = [0x40, 0x41, 0x42, 0x43]

    # Registres de tension bus pour les trois canaux de mesure
    BUS_VOLTAGE_REGISTERS = {
        1: 0x02,
        2: 0x04,
        3: 0x06
    }

    def __init__(self, i2c, address=None):
        self.i2c = i2c
        self.address = address

        # Si aucune adresse n'est fournie, on cherche automatiquement le capteur
        if self.address is None:
            self.address = self.detect()

        if self.address is None:
            print("INA3221 non detecte")
        else:
            print("INA3221 detecte a :", hex(self.address))

    def detect(self):
        # Scan du bus I2c pour trouver tous les peripheriques brancher
        devices = self.i2c.scan()
        print("I2C detectes :", [hex(d) for d in devices])

        for addr in self.POSSIBLE_ADDRESSES:
            if addr in devices:
                try:
                    # Lecture du registre de configuration pour verifier l'adresse
                    self.i2c.readfrom_mem(addr, 0x00, 2)
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
            # Les registres INA3221 sont coder sur 16 bits
            data = self.i2c.readfrom_mem(self.address, reg, 2)
            return (data[0] << 8) | data[1]
        except:
            return None

    def read_bus_voltage(self, channel):
        # Evite une lecture si le canal demander n'existe pas
        if channel not in self.BUS_VOLTAGE_REGISTERS:
            return None

        raw = self.read_register(self.BUS_VOLTAGE_REGISTERS[channel])

        if raw is None:
            return None

        # La valeur brute est décaler de 3 bits et 1 LSB vaut 8 mV
        voltage = (raw >> 3) * 0.008
        return voltage

    def read_all_voltages(self):
        return (
            self.read_bus_voltage(1),
            self.read_bus_voltage(2),
            self.read_bus_voltage(3)
        )


# =========================
# Lissage GPS
# =========================
class GPSFilter:
    def __init__(self, alpha=0.2):
        # Alpha faible = filtrage plus doux, alpha fort = reaction plus rapide
        self.alpha = alpha
        self.lat_f = None
        self.lon_f = None

    def update(self, lat, lon):
        # Si la position est absante, on garde la derniere position filtrer
        if lat is None or lon is None:
            return self.lat_f, self.lon_f

        if self.lat_f is None:
            # Premiere mesure : pas encore de moyenne, on initialise le filtre
            self.lat_f = lat
            self.lon_f = lon
        else:
            # Filtre exponentiel pour reduire les petites variations du GPS
            self.lat_f = self.alpha * lat + (1 - self.alpha) * self.lat_f
            self.lon_f = self.alpha * lon + (1 - self.alpha) * self.lon_f

        return self.lat_f, self.lon_f


# =========================
# Application principale
# =========================
class TrackerApp:
    def __init__(self):
        # Initialisation du bus I2c de l'ESP32
        self.i2c = I2C(
            0,
            scl=Pin(4),
            sda=Pin(5),
            freq=100000
        )

        self.gps = GravityGNSS(self.i2c)
        self.gps.begin()
        self.ina3221 = INA3221(self.i2c)
        self.gps_filter = GPSFilter(alpha=0.2)

    def start(self):
        # Boucle principale : une mesure complete toutes les 2 secondes
        while True:
            self.loop()
            time.sleep(2)

    def loop(self):
        # Lecture de la position convertie et des donnees brutes pour debug
        lat, lon = self.gps.get_position()
        raw_lat, raw_lon = self.gps.get_raw_position()

        print("LAT RAW:", raw_lat)
        print("LON RAW:", raw_lon)

        if lat is not None and lon is not None:
            print("Latitude :", lat)
            print("Longitude:", lon)

            lat_f, lon_f = self.gps_filter.update(lat, lon)
            print("Latitude filtree :", lat_f)
            print("Longitude filtree:", lon_f)
        else:
            print("Position non disponible")

        satellites = self.gps.get_satellites()
        # On considere le GPS fiable a partir de 6 satellites
        gps_ok = satellites >= 6

        print("Satellites:", satellites)

        if not gps_ok:
            print("GPS faible")

        # Lecture des tensions mesurer sur les trois canaux INA3221
        v1, v2, v3 = self.ina3221.read_all_voltages()

        print("Voltages:")
        self.print_voltage("Ch1", v1)
        self.print_voltage("Ch2", v2)
        self.print_voltage("Ch3", v3)

        print("===================")

    def print_voltage(self, label, voltage):
        # Affichage propre meme si le capteur ou le canal ne repond pas
        if voltage is None:
            print("  {}: non disponible".format(label))
        else:
            print("  {}: {:.3f} V".format(label, voltage))


# =========================
# Lancement
# =========================
app = TrackerApp()
app.start()