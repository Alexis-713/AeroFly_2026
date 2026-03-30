import time
import random
from machine import deepsleep
from sx1262 import SX1262
from LoRaWAN import LoRaWAN_OTAA
from cayenneLPP import CayenneLPP

print("Initialisation radio SX1262")

radio = SX1262(1, 9, 10, 11, 8, 14, 12, 13)

state = radio.begin(
    freq=868.0,       # MHz
    bw=125.0,         # kHz
    sf=7,
    cr=5,
    power=14,
    blocking=True
)
if state != 0:
    print("Erreur init radio, code:", state)

print("Paramètres LoRaWAN OTAA")

APP_EUI = "A840410000000101"
APP_KEY = "0C609A2029C6EAD3001FCB09604E8C51"

lora = LoRaWAN_OTAA(radio, app_eui=APP_EUI, app_key=APP_KEY)

print("Tentative de join OTAA...")
lora.join()

timeout = 60  # secondes max
elapsed = 0
while not lora.is_joined() and elapsed < timeout:
    print("En attente de join OTAA...")
    time.sleep(2)
    elapsed += 2

if not lora.is_joined():
    print("Join OTAA échoué après", timeout, "s — nouvelle tentative au prochain réveil.")
    deepsleep(60000)

print("Connecté au réseau LoRaWAN !")

lpp = CayenneLPP()

latitude    = round(random.uniform(48.80, 48.90), 6)
longitude   = round(random.uniform(2.30,  2.40),  6)
temperature = round(random.uniform(18.0,  30.0),  1)

lpp.reset()
lpp.add_gps(1, latitude, longitude, 0)  # canal 1
lpp.add_temperature(2, temperature)     # canal 2

payload = lpp.get_buffer()
print("Envoi payload LPP:", payload)

try:
    lora.send(payload)
    print("Message envoyé")
except Exception as e:
    print("Erreur envoi:", e)
    
time.sleep(1)
deepsleep(60000)
