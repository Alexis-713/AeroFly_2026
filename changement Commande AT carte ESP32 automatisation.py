from machine import UART
import time

wio = UART(1, baudrate=9600, tx=43, rx=44)

def send_cmd(cmd, wait=2):
    print(">>", cmd)
    wio.write((cmd + "\r\n").encode())
    time.sleep(wait)
    response = ""
    # Lecture avec timeout progressif
    deadline = time.time() + 3  # 3s de lecture max après le wait
    while time.time() < deadline:
        if wio.any():
            try:
                response += wio.read(wio.any()).decode()
            except:
                pass
            deadline = time.time() + 1  # reset si on reçoit des données
    print("<<", response)
    return response

# Réinitialisation propre
send_cmd("AT+RESET", 3)

# Vérification de la région
send_cmd("AT+DR=EU868")

# Configuration des IDs
send_cmd('AT+ID=DEVEUI')
send_cmd('AT+ID=APPEUI')
send_cmd('AT+KEY=APPKEY,"333D6E1042EAE4AF0E1EEC2EF2A3F401"')

send_cmd("AT+MODE=LWOTAA")
send_cmd("AT+CLASS=A")

# Tentatives de JOIN avec retry
for attempt in range(3):
    print(f"Tentative JOIN {attempt + 1}/3")
    join = send_cmd("AT+JOIN", 10)
    if "JOINED" in join or "Join Success" in join:
        print("✓ Connecté au réseau LoRaWAN AWS")
        break
    print(f"✗ Echec tentative {attempt + 1}")
    time.sleep(10)
else:
    print("JOIN impossible — vérifier les clés et la gateway AWS")