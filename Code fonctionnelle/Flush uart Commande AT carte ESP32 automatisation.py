from machine import UART
import time

wio = UART(1, baudrate=9600, tx=43, rx=44)
print("Connexion Wio-E5 prête")

def flush_uart(wait=1):
    time.sleep(wait)
    while wio.any():
        wio.read()

def send_cmd(cmd, wait=1):
    print(">>", cmd)
    wio.write(cmd + "\r\n")
    time.sleep(wait)
    raw = bytearray()
    while wio.any():
        chunk = wio.read()
        if chunk:
            raw.extend(chunk)
    print("RAW:", raw)
    filtered = bytearray(b for b in raw if b < 128)
    response = filtered.decode("utf-8")
    print(response)
    return response

send_cmd("AT+MODE=LWOTAA")
send_cmd("AT+DR=EU868")
send_cmd("AT+CH=NUM,0-2")
send_cmd('AT+ID=DEVEUI,"2C:F7:F1:20:64:10:40:09"')
send_cmd('AT+ID=APPEUI,"52:69:73:69:6E:67:48:46"')
send_cmd('AT+KEY=APPKEY,"333D6E1042EAE4AF0E1EEC2EF2A3F401"')
send_cmd("AT+ID")  # vérification


send_cmd("AT+RESET", 3)   # reset propre du module
send_cmd("AT+MODE=LWOTAA")
send_cmd("AT+DR=EU868")
send_cmd("AT+CH=NUM,0-2")
send_cmd('AT+ID=DEVEUI,"2C:F7:F1:20:64:10:40:09"')
send_cmd('AT+ID=APPEUI,"52:69:73:69:6E:67:48:46"')
send_cmd('AT+KEY=APPKEY,"333D6E1042EAE4AF0E1EEC2EF2A3F401"')
join = send_cmd("AT+JOIN", 15)


if "JOINED" in join or "Join Success" in join or "NORMAL" in join:
    print("Connecté au réseau LoRaWAN")
else:
    print("Erreur JOIN")
    while True:
        time.sleep(5)