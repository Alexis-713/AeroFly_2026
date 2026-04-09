from machine import Pin, SPI
import time

# Configuration Heltec V4 (ESP32-S3)
SCK_PIN  = 40
MISO_PIN = 41
MOSI_PIN = 42
CS_PIN   = 39

# On baisse un peu la vitesse pour le test initial (1MHz est plus sûr)
spi = SPI(2, baudrate=100000, polarity=0, phase=2, 
          sck=Pin(SCK_PIN), mosi=Pin(MOSI_PIN), miso=Pin(MISO_PIN))

cs = Pin(CS_PIN, Pin.OUT)
cs.value(1)

def ardu_write_reg(reg, val):
    cs.value(0)
    # Bit 7 à 1 pour l'écriture
    spi.write(bytearray([reg | 0x80, val]))
    cs.value(1)

def ardu_read_reg(reg):
    cs.value(0)
    # On envoie l'adresse (Bit 7 à 0)
    spi.write(bytearray([reg & 0x7F]))
    # On lit la réponse immédiatement sans relâcher CS
    data = spi.read(1)
    cs.value(1)
    return data[0]
    #spi.write(bytearray([reg & 0x7F]))
    #data = spi.read(2) # On lit deux fois
    #return data[1]     # On prend le deuxième octet

def test_mega():
    print("--- Diagnostic Arducam Mega ---")
    time.sleep(1)
    
    # 1. Test du registre d'ID (0x40)
    # Note : Sur certains modèles Mega, le registre ID est 0x00 ou 0x40
    chip_id = ardu_read_reg(0x40)
    print(f"ID du Chip détecté (Reg 0x40) : {hex(chip_id)}")
    
    # 2. Test de stabilité d'écriture
    test_val = 0x55
    ardu_write_reg(0x00, test_val)
    time.sleep(0.01)
    read_val = ardu_read_reg(0x00)
    print(f"Test Registre 0x00 : Écrit {hex(test_val)} -> Lu {hex(read_val)}")

    if read_val == test_val:
        print("✅ COMMUNICATION SPI PARFAITE !")
    elif read_val == 0x82 or read_val == 0x00:
        print("⚠️ Caméra détectée mais données mal lues. Tentative de changement de phase SPI...")
        # Si ça persiste, on peut tester polarity=1, phase=1 dans la config SPI
    else:
        print("❌ Échec total : Vérifiez les branchements (MISO/MOSI) et l'alimentation.")

test_mega()