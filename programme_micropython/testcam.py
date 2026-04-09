from machine import Pin, SPI
import time

# --- Configuration Hardware ---
SCK_PIN, MISO_PIN, MOSI_PIN, CS_PIN = 40, 41, 42, 39

spi = SPI(2, baudrate=10000, polarity=0, phase=2, 
          sck=Pin(SCK_PIN), mosi=Pin(MOSI_PIN), miso=Pin(MISO_PIN))
cs = Pin(CS_PIN, Pin.OUT, value=1)

# --- Fonctions de base corrigées (Dummy Byte inclus) ---
def write_reg(reg, val):
    cs.value(0)
    spi.write(bytearray([reg | 0x80, val]))
    cs.value(1)

def read_reg(reg):
    cs.value(0)
    spi.write(bytearray([reg & 0x7F]))
    data = spi.read(1) # Lecture de 2 octets pour le dummy byte
    cs.value(1)
    return data[0]

# --- Fonctions de capture ---
def capture_photo(filename="photo.jpg"):
    print("📸 Préparation de la capture...")
    
    # 1. Déclencher la capture (Commande standard Arducam Mega)
    write_reg(0x04, 0x01) # Trigger capture
    
    # 2. Attendre que la capture soit terminée
    timeout = 50 # 5 secondes max
    while timeout > 0:
        status = read_reg(0x41)
        if status & 0x08: # Le bit 3 indique que le JPEG est prêt dans le buffer
            break
        time.sleep(0.1)
        timeout -= 1
    
    if timeout <= 0:
        print("❌ Erreur : Temps d'attente dépassé (Timeout)")
        return

    # 3. Lire la taille du fichier (3 registres pour le Mega)
    l1 = read_reg(0x42)
    l2 = read_reg(0x43)
    l3 = read_reg(0x44)
    length = (l3 << 16) | (l2 << 8) | l1
    print(f"✅ Photo prête ! Taille : {length} octets")

    # 4. Lecture du buffer et écriture sur la mémoire Flash
    try:
        with open(filename, "wb") as f:
            cs.value(0)
            spi.write(bytearray([0x3D])) # Commande pour lire le burst FIFO
            spi.read(1) # Ignorer le dummy byte du burst
            
            remaining = length
            chunk_size = 256 # On lit par petits blocs pour économiser la RAM
            while remaining > 0:
                to_read = min(remaining, chunk_size)
                f.write(spi.read(to_read))
                remaining -= to_read
            
            cs.value(1)
        print(f"💾 Image enregistrée sous : {filename}")
    except Exception as e:
        print(f"❌ Erreur d'écriture : {e}")

# --- Test ---
def setup_camera():
    # Reset de la caméra
    write_reg(0x07, 0x80) 
    time.sleep(0.2)
    write_reg(0x07, 0x00)
    time.sleep(0.2)
    print("🚀 Caméra initialisée.")

setup_camera()
capture_photo("test_vol_1.jpg")
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