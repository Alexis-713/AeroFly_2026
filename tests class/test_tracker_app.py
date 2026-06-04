from aerofly_classes import TrackerApp


class FakeGPS:
    def __init__(self, lat, lon, raw_lat, raw_lon, satellites):
        self.lat = lat
        self.lon = lon
        self.raw_lat = raw_lat
        self.raw_lon = raw_lon
        self.satellites = satellites

    def get_position(self):
        return self.lat, self.lon

    def get_raw_position(self):
        return self.raw_lat, self.raw_lon

    def get_satellites(self):
        return self.satellites


class FakeINA3221:
    def __init__(self, voltages):
        self.voltages = voltages

    def read_all_voltages(self):
        return self.voltages


class FakeGPSFilter:
    def __init__(self):
        self.last_update = None

    def update(self, lat, lon):
        self.last_update = (lat, lon)
        return lat, lon


class TestableTrackerApp(TrackerApp):
    def __init__(self):
        pass


def assert_equal(value, expected, message):
    if value != expected:
        raise AssertionError(message + " valeur=" + str(value))


def make_app(lat, lon, raw_lat, raw_lon, satellites, voltages):
    app = TestableTrackerApp()
    app.gps = FakeGPS(lat, lon, raw_lat, raw_lon, satellites)
    app.ina3221 = FakeINA3221(voltages)
    app.gps_filter = FakeGPSFilter()
    return app


def test_loop_position_valide():
    app = make_app(
        47.233333,
        -0.733333,
        [47, 13, 1, 134, 160, 0],
        [0, 44, 0, 0, 0, 0],
        8,
        (12.0, 6.0, 3.0),
    )

    app.loop()

    assert_equal(app.gps_filter.last_update, (47.233333, -0.733333), "le filtre GPS doit recevoir la position")


def test_loop_gps_faible():
    app = make_app(
        0.0,
        -0.0,
        [0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0],
        0,
        (11.976, 11.976, 11.976),
    )

    app.loop()

    assert_equal(app.gps.get_satellites(), 0, "le test doit simuler zero satellite")


def test_print_voltage_none():
    app = TestableTrackerApp()
    app.print_voltage("Ch1", None)


print("Tests TrackerApp")
test_loop_position_valide()
test_loop_gps_faible()
test_print_voltage_none()
print("OK - TrackerApp")
