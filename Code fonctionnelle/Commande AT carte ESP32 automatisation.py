from machine import UART
import time

wio = UART(1, baudrate=9600, tx=43, rx=44)

def send_cmd(cmd, wait=1):
    print(">>", cmd)
    wio.write(cmd + "\r\n")
    time.sleep(wait)
    response = ""
    while wio.any():
        response += wio.read().decode()
        
    print(response)
    return response

send_cmd("AT+MODE=LWOTAA")

# France / Europe : EU868
send_cmd("AT+DR=EU868")
send_cmd("AT+CH=NUM,0-2")

# Valeur enregistrées dans AWS
send_cmd('AT+ID=DEVEUI')
send_cmd('AT+ID=APPEUI')
send_cmd('AT+KEY=APPKEY,"333D6E1042EAE4AF0E1EEC2EF2A3F401"')

send_cmd("AT+ID")      # vérification

join = send_cmd("AT+JOIN", 15)

if "JOINED" in join or "Join Success" in join or "NORMAL" in join:
    print("Connecté au réseau LoRaWAN")

else:
    print("Erreur JOIN")
    while True:
        time.sleep(5)