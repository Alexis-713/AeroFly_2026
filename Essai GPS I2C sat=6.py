from machine import I2C, Pin
import time

# --- CONFIG I2C ---
i2c = I2C(0, scl=Pin(4), sda=Pin(5))
GPS_ADDR = 0x66

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

    print("-" * 40)
    time.sleep(1)