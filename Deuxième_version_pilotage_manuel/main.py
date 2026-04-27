from lib.configuration.reduire_conso_energie import reduire_conso_energie
from lib.moteur.IBusServoController import IBusServoController
from lib.configuration.configuration import configuration
reduire_conso_energie()
from machine import Pin
import time
led = Pin(35, Pin.OUT)
i = 0
while i < 5:
    i+=1
    led.value(1)
    time.sleep(1)
    led.value(0)
    time.sleep(1)
time.sleep(5)
print("Lancement")
controller = IBusServoController(configuration)
controller.run()
