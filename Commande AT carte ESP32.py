from machine import UART
import time

wio = UART(1, baudrate=9600, tx=43, rx=44)

print("Connexion Wio-E5 prête")

while True:
    
    cmd = input("Commande AT: ")
    
    wio.write(cmd + "\r\n")
    
    time.sleep(0.5)
    
    while wio.any():
        print(wio.read().decode(), end="")