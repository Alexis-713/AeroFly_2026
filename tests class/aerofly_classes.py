try:
    from machine import I2C, Pin
except ImportError:
    I2C = None
    Pin = None

import time


class GravityGNSS:
    GPS_ADDR = 0x66

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

    SIGN_LON = -1

    def __init__(self, i2c, address=GPS_ADDR):
        self.i2c = i2c
        self.address = address

    def read_reg(self, reg, length):
        try:
            self.i2c.writeto(self.address, bytes([reg]))
            data = self.i2c.readfrom(self.address, length)
            return list(data)
        except Exception:
            return None

    def get_lat(self):
        data = self.read_reg(self.REG_LAT_1, 6)

        if data:
            sign = -1 if (data[0] & 0x80) else 1
            dd = data[0] & 0x7F
            mm = data[1]
            mmmmm = (data[2] << 16) | (data[3] << 8) | data[4]
            lat = dd + (mm + mmmmm / 100000.0) / 60.0
            return lat * sign

        return None

    def get_lon(self):
        data = self.read_reg(self.REG_LON_1, 6)

        if data:
            ddd = data[0]
            mm = data[1]
            mmmmm = (data[2] << 16) | (data[3] << 8) | data[4]
            lon = ddd + (mm + mmmmm / 100000.0) / 60.0
            return lon * self.SIGN_LON

        return None

    def get_satellites(self):
        data = self.read_reg(self.REG_USE_STAR, 1)

        if data:
            return data[0]

        return 0

    def get_altitude(self):
        data = self.read_reg(self.REG_ALT_H, 3)

        if data:
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
            print("INA3221 detecte a :", hex(self.address))

    def detect(self):
        devices = self.i2c.scan()
        print("I2C detectes :", [hex(d) for d in devices])

        for addr in self.POSSIBLE_ADDRESSES:
            if addr in devices:
                try:
                    self.i2c.readfrom_mem(addr, 0x00, 2)
                    return addr
                except Exception:
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
        except Exception:
            return None

    def read_bus_voltage(self, channel):
        if channel not in self.BUS_VOLTAGE_REGISTERS:
            return None

        raw = self.read_register(self.BUS_VOLTAGE_REGISTERS[channel])

        if raw is None:
            return None

        voltage = (raw >> 3) * 0.008
        return voltage

    def read_all_voltages(self):
        return (
            self.read_bus_voltage(1),
            self.read_bus_voltage(2),
            self.read_bus_voltage(3)
        )


class GPSFilter:
    def __init__(self, alpha=0.2):
        self.alpha = alpha
        self.lat_f = None
        self.lon_f = None

    def update(self, lat, lon):
        if lat is None or lon is None:
            return self.lat_f, self.lon_f

        if self.lat_f is None:
            self.lat_f = lat
            self.lon_f = lon
        else:
            self.lat_f = self.alpha * lat + (1 - self.alpha) * self.lat_f
            self.lon_f = self.alpha * lon + (1 - self.alpha) * self.lon_f

        return self.lat_f, self.lon_f


class TrackerApp:
    def __init__(self):
        self.i2c = I2C(
            0,
            scl=Pin(4),
            sda=Pin(5),
            freq=100000
        )

        self.gps = GravityGNSS(self.i2c)
        self.ina3221 = INA3221(self.i2c)
        self.gps_filter = GPSFilter(alpha=0.2)

    def start(self):
        while True:
            self.loop()
            time.sleep(2)

    def loop(self):
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
        gps_ok = satellites >= 6

        print("Satellites:", satellites)

        if not gps_ok:
            print("GPS faible")

        v1, v2, v3 = self.ina3221.read_all_voltages()

        print("Voltages:")
        self.print_voltage("Ch1", v1)
        self.print_voltage("Ch2", v2)
        self.print_voltage("Ch3", v3)

        print("===================")

    def print_voltage(self, label, voltage):
        if voltage is None:
            print("  {}: non disponible".format(label))
        else:
            print("  {}: {:.3f} V".format(label, voltage))
