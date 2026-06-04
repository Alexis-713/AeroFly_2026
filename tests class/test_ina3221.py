from aerofly_classes import INA3221


class FakeI2C:
    def __init__(self, scan_devices=None, readfrom_mem_data=None):
        self.scan_devices = scan_devices or []
        self.readfrom_mem_data = readfrom_mem_data or {}

    def scan(self):
        return self.scan_devices

    def readfrom_mem(self, address, register, length):
        key = (address, register, length)
        value = self.readfrom_mem_data[key]
        if isinstance(value, Exception):
            raise value
        return bytes(value)


def assert_equal(value, expected, message):
    if value != expected:
        raise AssertionError(message + " valeur=" + str(value))


def assert_almost_equal(value, expected, precision, message):
    if abs(value - expected) > precision:
        raise AssertionError(message + " valeur=" + str(value))


def assert_tuple_almost_equal(value, expected, precision, message):
    if len(value) != len(expected):
        raise AssertionError(message + " longueur=" + str(len(value)))

    for index in range(len(value)):
        if abs(value[index] - expected[index]) > precision:
            raise AssertionError(message + " valeur=" + str(value))


def test_detect():
    i2c = FakeI2C(
        scan_devices=[0x28, 0x41, 0x66],
        readfrom_mem_data={(0x41, 0x00, 2): [0x71, 0x27]},
    )

    ina = INA3221(i2c)

    assert_equal(ina.address, 0x41, "adresse INA3221 incorrecte")
    assert_equal(ina.is_available(), True, "INA3221 doit etre disponible")


def test_detect_absent():
    i2c = FakeI2C(scan_devices=[0x28, 0x66])
    ina = INA3221(i2c)

    assert_equal(ina.address, None, "adresse doit etre None si le capteur est absent")
    assert_equal(ina.is_available(), False, "INA3221 ne doit pas etre disponible")


def test_read_bus_voltage():
    i2c = FakeI2C(readfrom_mem_data={(0x41, 0x02, 2): [0x2E, 0xE0]})
    ina = INA3221(i2c, address=0x41)

    assert_almost_equal(ina.read_bus_voltage(1), 12.0, 0.001, "tension incorrecte")


def test_canal_invalide():
    ina = INA3221(FakeI2C(), address=0x41)

    assert_equal(ina.read_bus_voltage(4), None, "un canal invalide doit retourner None")


def test_read_all_voltages():
    i2c = FakeI2C(
        readfrom_mem_data={
            (0x41, 0x02, 2): [0x2E, 0xE0],
            (0x41, 0x04, 2): [0x17, 0x70],
            (0x41, 0x06, 2): [0x0B, 0xB8],
        }
    )
    ina = INA3221(i2c, address=0x41)

    assert_tuple_almost_equal(
        ina.read_all_voltages(),
        (12.0, 6.0, 3.0),
        0.001,
        "les trois tensions sont incorrectes"
    )


print("Tests INA3221")
test_detect()
test_detect_absent()
test_read_bus_voltage()
test_canal_invalide()
test_read_all_voltages()
print("OK - INA3221")
