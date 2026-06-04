from aerofly_classes import GravityGNSS


class FakeI2C:
    def __init__(self, readfrom_data=None, fail=False):
        self.readfrom_data = readfrom_data or {}
        self.fail = fail
        self.writes = []
        self.last_register = None

    def writeto(self, address, data):
        if self.fail:
            raise OSError("bus i2c indisponible")
        self.writes.append((address, data))
        self.last_register = data[0]

    def readfrom(self, address, length):
        key = (address, self.last_register, length)
        return bytes(self.readfrom_data[key])


def assert_equal(value, expected, message):
    if value != expected:
        raise AssertionError(message + " valeur=" + str(value))


def assert_almost_equal(value, expected, precision, message):
    if abs(value - expected) > precision:
        raise AssertionError(message + " valeur=" + str(value))


def test_read_reg():
    i2c = FakeI2C({(0x66, 7, 6): [47, 13, 1, 134, 160, 0]})
    gps = GravityGNSS(i2c)

    data = gps.read_reg(7, 6)

    assert_equal(data, [47, 13, 1, 134, 160, 0], "read_reg doit lire les octets")
    assert_equal(i2c.writes, [(0x66, bytes([7]))], "read_reg doit selectionner le registre")


def test_get_lat():
    i2c = FakeI2C({(0x66, 7, 6): [47, 13, 1, 134, 160, 0]})
    gps = GravityGNSS(i2c)

    assert_almost_equal(gps.get_lat(), 47.233333, 0.00001, "latitude incorrecte")


def test_get_lon():
    i2c = FakeI2C({(0x66, 13, 6): [0, 44, 0, 0, 0, 0]})
    gps = GravityGNSS(i2c)

    assert_almost_equal(gps.get_lon(), -0.733333, 0.00001, "longitude incorrecte")


def test_get_satellites():
    i2c = FakeI2C({(0x66, 19, 1): [8]})
    gps = GravityGNSS(i2c)

    assert_equal(gps.get_satellites(), 8, "nombre de satellites incorrect")


def test_erreur_i2c():
    gps = GravityGNSS(FakeI2C(fail=True))

    assert_equal(gps.read_reg(7, 6), None, "read_reg doit retourner None si I2C echoue")
    assert_equal(gps.get_lat(), None, "get_lat doit retourner None si I2C echoue")


print("Tests GravityGNSS")
test_read_reg()
test_get_lat()
test_get_lon()
test_get_satellites()
test_erreur_i2c()
print("OK - GravityGNSS")
