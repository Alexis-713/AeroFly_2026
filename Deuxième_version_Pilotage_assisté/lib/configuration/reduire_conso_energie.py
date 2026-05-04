import network
import bluetooth
import machine
from machine import Pin

def reduire_conso_energie():
    # ecran off
    led_power = Pin(2, Pin.OUT)
    led_power.value(0)

    # wifi off
    network.WLAN(network.STA_IF).active(False)
    network.WLAN(network.AP_IF).active(False)

    # bluetooth off
    bluetooth.BLE().active(False)

    # cpu plus lent
    machine.freq(80000000)
