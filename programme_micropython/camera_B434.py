from machine import Pin, SPI
import time

# --- CONFIGURATION ---
SCK_PIN, MISO_PIN, MOSI_PIN, CS_PIN = 40, 41, 42, 39
FILENAME = "photo_avion.jpg"

# Initialisation SPI à 100kHz comme testé
spi = SPI(1, baudrate=10000, polarity=0, phase=0, 
          sck=Pin(SCK_PIN), mosi=Pin(MOSI_PIN), miso=Pin(MISO_PIN))

cs = Pin(CS_PIN, Pin.OUT)
cs.value(1)

# --- FONCTIONS DE BAS NIVEAU ---
def write_reg(reg, val):
    cs.value(0)
    spi.write(bytes([reg | 0x80, val]))
    cs.value(1)

def read_reg(reg):
    cs.value(0)
    spi.write(bytes([reg & 0x7F]))
    data = spi.read(1)
    cs.value(1)
    return data[0]

# --- LOGIQUE DE CAPTURE ---
def capture_image():
    print("Démarrage de la capture...")
    
    # 1. Effacer le flag de fin de capture précédent
    write_reg(0x04, 0x01) 
    
    # 2. Lancer la capture
    write_reg(0x04, 0x02)
    
    # 3. Attendre que la capture soit terminée (Bit 3 du registre 0x41)
    timeout = 50 # 5 secondes max
    while timeout > 0:
        status = read_reg(0x41)
        if status & 0x08:
            break
        time.sleep(0.1)
        timeout -= 1
    
    if timeout == 0:
        print("Erreur : Timeout de capture.")
        return

    # 4. Lire la taille du FIFO (mémoire de la caméra)
    len1 = read_reg(0x42)
    len2 = read_reg(0x43)
    len3 = read_reg(0x44) & 0x7F
    total_len = (len3 << 16) | (len2 << 8) | len1
    print(f"Image prête ! Taille : {total_len} octets")

    # 5. Lecture et écriture dans le fichier
    try:
        with open(FILENAME, "wb") as f:
            cs.value(0)
            spi.write(bytes([0x3D])) # Commande de lecture en rafale (Burst Read)
            
            # On lit par blocs de 128 octets pour ménager la RAM de l'ESP32
            remaining = total_len
            while remaining > 0:
                chunk_size = min(remaining, 128)
                data = spi.read(chunk_size)
                f.write(data)
                remaining -= chunk_size
                
            cs.value(1)
        print(f"Image sauvegardée sous : {FILENAME}")
    except Exception as e:
        print(f"Erreur lors de l'écriture : {e}")
        cs.value(1)

# --- EXÉCUTION ---
capture_image()