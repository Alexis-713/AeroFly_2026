from machine import I2C, Pin
import time

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

# --- REGISTRES ---
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

# --- FONCTIONS BAS NIVEAU ---
def read_reg(reg, length):
    try:
        i2c.writeto(GPS_ADDR, bytes([reg]))
        data = i2c.readfrom(GPS_ADDR, length)
        return list(data)
    except:
        return None

# --- FONCTIONS GPS ---
def get_lat():
    data = read_reg(REG_LAT_1, 6)
    if data:
        sign = -1 if (data[0] & 0x80) else 1
        
        dd = data[0] & 0x7F
        mm = data[1]
        mmmmm = (data[2] << 16) | (data[3] << 8) | data[4]

        lat = dd + (mm + mmmmm / 100000.0) / 60.0
        
        return lat * sign
    return None


SIGN_LON = -1  # Cholet/Chemillé = Ouest

def get_lon():
    data = read_reg(REG_LON_1, 6)
    if data:
        ddd = data[0]
        mm = data[1]
        mmmmm = (data[2] << 16) | (data[3] << 8) | data[4]

        lon = ddd + (mm + mmmmm / 100000.0) / 60.0

        return lon * SIGN_LON
    return None

def get_satellites():
    data = read_reg(REG_USE_STAR, 1)
    if data:
        return data[0]
    return 0

def get_altitude():
    data = read_reg(REG_ALT_H, 3)
    if data:
        alt = ((data[0] & 0x7F) << 8 | data[1]) + data[2] / 100.0
        return alt
    return None

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


# =========================
# LISSAGE GPS
# =========================
lat_f = None
lon_f = None
alpha = 0.2

def filter_gps(lat, lon):
    global lat_f, lon_f

    if lat_f is None:
        lat_f = lat
        lon_f = lon
    else:
        lat_f = alpha * lat + (1 - alpha) * lat_f
        lon_f = alpha * lon + (1 - alpha) * lon_f

    return lat_f, lon_f

# =========================
# BOUCLE PRINCIPALE
# =========================
while True:
    lat = get_lat()
    lon = get_lon()
    
    print("LAT RAW:", read_reg(REG_LAT_1, 6))
    print("LON RAW:", read_reg(REG_LON_1, 6))
    
    if lat and lon:
        print("Latitude :", lat)
        print("Longitude:", lon)
    else:
        print("Position non disponible")

    print("Satellites:", get_satellites())
    sat = get_satellites()

    gps_ok = sat >= 6

    if not gps_ok:
        print("⚠️ GPS faible")
    print("Altitude:", get_altitude(), "m")

    v1 = read_bus_voltage(1)
    v2 = read_bus_voltage(2)
    v3 = read_bus_voltage(3)

    print("Voltages:")
    print("  Ch1: {:.3f} V".format(v1))
    print("  Ch2: {:.3f} V".format(v2))
    print("  Ch3: {:.3f} V".format(v3))

    print("===================")

    time.sleep(2)