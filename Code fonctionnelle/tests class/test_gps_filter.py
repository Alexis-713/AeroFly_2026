from aerofly_classes import GPSFilter


def assert_equal(value, expected, message):
    if value != expected:
        raise AssertionError(message + " valeur=" + str(value))


def assert_almost_equal(value, expected, precision, message):
    if abs(value - expected) > precision:
        raise AssertionError(message + " valeur=" + str(value))


def test_premiere_mesure():
    gps_filter = GPSFilter(alpha=0.2)
    lat_f, lon_f = gps_filter.update(47.0, -0.5)

    assert_equal(lat_f, 47.0, "la premiere latitude doit initialiser le filtre")
    assert_equal(lon_f, -0.5, "la premiere longitude doit initialiser le filtre")


def test_lissage():
    gps_filter = GPSFilter(alpha=0.2)
    gps_filter.update(47.0, -0.5)
    lat_f, lon_f = gps_filter.update(48.0, -1.0)

    assert_almost_equal(lat_f, 47.2, 0.00001, "latitude filtree incorrecte")
    assert_almost_equal(lon_f, -0.6, 0.00001, "longitude filtree incorrecte")


def test_position_absente():
    gps_filter = GPSFilter(alpha=0.2)
    gps_filter.update(47.0, -0.5)
    lat_f, lon_f = gps_filter.update(None, None)

    assert_equal(lat_f, 47.0, "la latitude filtree doit rester identique")
    assert_equal(lon_f, -0.5, "la longitude filtree doit rester identique")


print("Tests GPSFilter")
test_premiere_mesure()
test_lissage()
test_position_absente()
print("OK - GPSFilter")
