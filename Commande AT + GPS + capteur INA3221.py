from machine import UART, I2C, Pin
import time

# =========================
# UART LoRa
# =========================
lora = UART(1, baudrate=9600, tx=43, rx=44)

def send_cmd(cmd, wait=1):
    print(">>", cmd)
    lora.write(cmd + "\r\n")
    time.sleep(wait)

    response = ""
    while lora.any():
        response += lora.read().decode()

    print(response)
    return response

# =========================
# INIT LoRaWAN
# =========================
send_cmd("AT+MODE=LWOTAA")
send_cmd('AT+ID=DevEui')
send_cmd('AT+ID=AppEui')
send_cmd('AT+KEY=APPKEY,"333D6E1042EAE4AF0E1EEC2EF2A3F401"')

join = send_cmd("AT+JOIN", 5)

if "JOINED" in join or "Join Success" in join or "NORMAL" in join:
    print("Connecté au réseau LoRaWAN")

else:
    print("Erreur JOIN")
    while True:
        time.sleep(5)

print("LoRa connecté")

# =========================
# I2C (GPS + INA3221)
# =========================
i2c = I2C(0, scl=Pin(4), sda=Pin(5), freq=100000)

GPS_ADDR = 0x66
# =========================
# DETECTION INA3221
# =========================

INA3221_ADDR = None

def detect_ina3221():

    possible_addresses = [0x40, 0x41, 0x42, 0x43]

    devices = i2c.scan()

    print("I2C detectes :", [hex(d) for d in devices])

    for addr in possible_addresses:

        if addr in devices:

            try:
                i2c.readfrom_mem(addr, 0x00, 2)

                print("INA3221 detecte a :", hex(addr))

                return addr

            except:
                pass

    return None


INA3221_ADDR = detect_ina3221()

# =========================
# GPS FUNCTIONS
# =========================
def read_reg(reg, length):
    try:
        i2c.writeto(GPS_ADDR, bytes([reg]))
        return list(i2c.readfrom(GPS_ADDR, length))
    except:
        return None

def get_lat():
    data = read_reg(7, 6)
    if data:
        dd = data[0]
        mm = data[1]
        mmmmm = (data[2]<<16) | (data[3]<<8) | data[4]
        lat = dd + (mm + mmmmm/100000.0)/60.0
        return abs(lat)  # France = Nord
    return None

def get_lon():
    data = read_reg(13, 6)
    if data:
        ddd = data[0]
        mm = data[1]
        mmmmm = (data[2]<<16) | (data[3]<<8) | data[4]
        lon = ddd + (mm + mmmmm/100000.0)/60.0
        return -abs(lon)  # France = Ouest
    return None

def get_sat():
    data = read_reg(19, 1)
    return data[0] if data else 0

# =========================
# INA3221 FUNCTIONS
# =========================
def read_register(reg):
    data = i2c.readfrom_mem(INA3221_ADDR, reg, 2)
    return (data[0] << 8) | data[1]

def read_bus_voltage(channel):
    # registres bus voltage :
    reg_map = {
        1: 0x02,
        2: 0x04,
        3: 0x06
    }
    
    raw = read_register(reg_map[channel])
    
    # conversion (LSB = 8mV)
    voltage = (raw >> 3) * 0.008
    return voltage

while True:
    lat = get_lat()
    lon = get_lon()

    v1 = read_bus_voltage(1)
    v2 = read_bus_voltage(2)
    v3 = read_bus_voltage(3)

    print("Lat:", lat, "Lon:", lon)
    print("Voltages:", v1, v2, v3)

    # =========================
    # ENVOI LORA
    # =========================
    if lat and lon:
        time.sleep(5)
        payload = "GPS:{:.5f};{:.5f}, batterie:{:.2f}V, température: °C, humidité: %, pression: hPa, vitesse d'air/ de l'avion: , ".format(lat, lon, v1)

        cmd = 'AT+MSG="{}"'.format(payload)
        send_cmd(cmd, 2)

    print("-"*40)
    time.sleep(10)