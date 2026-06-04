from machine import UART, I2C, Pin
import time

# =========================
# LoRaWAN Wio-E5
# =========================
class LoRaWAN:
    def __init__(self, uart_id=1, baudrate=9600, tx=43, rx=44, appkey=""):
        # Initialisation de la liaison serie UART avec le module Wio-E5
        self.uart = UART(uart_id, baudrate=baudrate, tx=tx, rx=rx)
        self.appkey = appkey

    def send_cmd(self, cmd, wait=1):
        # Envoie une commande AT au module LoRaWAN et attend sa reponse
        print(">>", cmd)
        self.uart.write(cmd + "\r\n")
        time.sleep(wait)

        response = ""
        while self.uart.any():
            try:
                # Lecture et conversion de la reponse recue en texte
                response += self.uart.read().decode()
            except:
                # Ignore les caracteres illisibles pour ne pas bloquer le programme
                pass

        print(response)
        return response

    def join(self):
        # Configuration du module en mode LoRaWAN OTAA
        self.send_cmd("AT+MODE=LWOTAA")
        self.send_cmd("AT+ID=DevEui")
        self.send_cmd("AT+ID=AppEui")
        self.send_cmd('AT+KEY=APPKEY,"{}"'.format(self.appkey))

        # Demande de connexion au reseau LoRaWAN
        join_response = self.send_cmd("AT+JOIN", 5)

        # Le module peut renvoyer differents messages selon son firmware
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
        # Envoie le message sous forme de texte avec la commande AT+MSG
        cmd = 'AT+MSG="{}"'.format(payload)
        return self.send_cmd(cmd, 2)

# =========================
# Gravity GNSS GPS BeiDou
# =========================
class GravityGNSS:
    def __init__(self, i2c, address=0x66):
        # Adresse I2C par defaut du module GPS Gravity GNSS
        self.i2c = i2c
        self.address = address

    def read_reg(self, reg, length):
        # Selectionne un registre puis lit le nombre d'octets demande
        try:
            self.i2c.writeto(self.address, bytes([reg]))
            return list(self.i2c.readfrom(self.address, length))
        except:
            return None

    def get_lat(self):
        # Registre 7 : debut des donnees de latitude
        data = self.read_reg(7, 6)

        if data:
            # Le GPS donne la latitude en degres + minutes decimales
            dd = data[0]
            mm = data[1]
            mmmmm = (data[2] << 16) | (data[3] << 8) | data[4]

            # Conversion en degres decimaux
            lat = dd + (mm + mmmmm / 100000.0) / 60.0
            return abs(lat)  # France = Nord

        return None

    def get_lon(self):
        # Registre 13 : debut des donnees de longitude
        data = self.read_reg(13, 6)

        if data:
            # Le GPS donne la longitude en degres + minutes decimales
            ddd = data[0]
            mm = data[1]
            mmmmm = (data[2] << 16) | (data[3] << 8) | data[4]

            # Conversion en degres decimaux, avec signe negatif pour l'ouest
            lon = ddd + (mm + mmmmm / 100000.0) / 60.0
            return -abs(lon)  # France = Ouest

        return None

    def get_sat(self):
        # Registre 19 : nombre de satellites utiliser
        data = self.read_reg(19, 1)
        return data[0] if data else 0

    def get_position(self):
        # Renvoie la position GPS complete : latitude, longitude, satellites
        return self.get_lat(), self.get_lon(), self.get_sat()

# =========================
# INA3221
# =========================
class INA3221:
    # Adresses I2C possibles du capteur
    POSSIBLE_ADDRESSES = [0x40, 0x41, 0x42, 0x43]

    # Registres contenant la tension bus de chaque canal
    BUS_VOLTAGE_REGISTERS = {
        1: 0x02,
        2: 0x04,
        3: 0x06
    }

    def __init__(self, i2c, address=None):
        self.i2c = i2c
        self.address = address

        # Detection automatique si aucune adresse n'est indiquer
        if self.address is None:
            self.address = self.detect()

        if self.address is None:
            print("INA3221 non detecte")
        else:
            print("INA3221 pret a l'adresse :", hex(self.address))

    def detect(self):
        # Scan du bus I2C pour lister les modules connecter
        devices = self.i2c.scan()
        print("I2C detectes :", [hex(d) for d in devices])

        for addr in self.POSSIBLE_ADDRESSES:
            if addr in devices:
                try:
                    # Test de lecture du registre de configuration du capteur
                    self.i2c.readfrom_mem(addr, 0x00, 2)
                    print("INA3221 detecte a :", hex(addr))
                    return addr
                except:
                    pass

        return None

    def is_available(self):
        # Le capteur est disponible si une adresse valide a ete trouver
        return self.address is not None

    def read_register(self, reg):
        if not self.is_available():
            return None

        try:
            # Lecture d'un registre 16 bits : octet fort puis octet faible
            data = self.i2c.readfrom_mem(self.address, reg, 2)
            return (data[0] << 8) | data[1]
        except:
            return None

    def read_bus_voltage(self, channel):
        # Verifie que le canal demande existe bien
        if channel not in self.BUS_VOLTAGE_REGISTERS:
            return None

        raw = self.read_register(self.BUS_VOLTAGE_REGISTERS[channel])

        if raw is None:
            return None

        # La valeur brute est decalee de 3 bits et 1 LSB vaut 8 mV
        voltage = (raw >> 3) * 0.008
        return voltage

    def read_all_voltages(self):
        # Lecture des trois entrees de tension du capteur
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
        # Creation de l'objet LoRaWAN avec les broches UART du module
        self.lora = LoRaWAN(
            uart_id=1,
            baudrate=9600,
            tx=43,
            rx=44,
            appkey="333D6E1042EAE4AF0E1EEC2EF2A3F401"
        )

        # Initialisation du bus I2C utilise par le GPS et l'INA3221
        self.i2c = I2C(
            0,
            scl=Pin(4),
            sda=Pin(5),
            freq=100000
        )

        # Creation des objets pour communiquer avec les capteurs
        self.gps = GravityGNSS(self.i2c, address=0x66)
        self.ina3221 = INA3221(self.i2c)

    def start(self):
        # Tant que la connexion LoRaWAN echoue, le programme attend
        if not self.lora.join():
            while True:
                time.sleep(5)

        print("LoRa connecte")

        # Une mesure et un envoi toutes les 10 secondes
        while True:
            self.loop()
            time.sleep(10)

    def loop(self):
        # Lecture des donnees GPS et des tensions d'alimentation
        lat, lon, sat = self.gps.get_position()
        v1, v2, v3 = self.ina3221.read_all_voltages()

        print("Lat:", lat, "Lon:", lon, "Sat:", sat)
        print("Voltages:", v1, v2, v3)

        if lat is not None and lon is not None:
            # Si la tension batterie est absente, on envoie 0 V par defaut
            batterie = v1 if v1 is not None else 0

            # Construction du message envoyer sur le reseau LoRaWAN
            payload = (
                "GPS: {:.5f};{:.5f}, "
                "bat:{:.2f}V, "
                "temp: {:.2f}, "
                "hum: {:.2f}, "
                "pres: {:.2f}hPa, "
                "vit: {:.2f}"
            ).format(lat, lon, batterie)
            # {:.5f} signifie 5 chiffres après la virgule, {:.2f} signifie 2 chiffres après la virgule
            # on récupère la latitude, longitude, etc avec la ligne .format(lat, lon, batterie

            self.lora.send_message(payload)

        print("-" * 40)

# =========================
# Lancement
# =========================
app = TrackerApp()
app.start()