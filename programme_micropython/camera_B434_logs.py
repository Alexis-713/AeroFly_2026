from machine import Pin, SPI
import time

# Configuration Heltec V4
SCK_PIN, MISO_PIN, MOSI_PIN, CS_PIN = 40, 41, 42, 39
spi = SPI(2, baudrate=10000, polarity=0, phase=0, 
          sck=Pin(SCK_PIN), mosi=Pin(MOSI_PIN), miso=Pin(MISO_PIN))
cs = Pin(CS_PIN, Pin.OUT, value=1)

def write_reg(reg, val):
    cs.value(0)
    spi.write(bytearray([reg | 0x80, val]))
    cs.value(1)

def read_reg(reg):
    cs.value(0)
    spi.write(bytearray([reg & 0x7F]))
    data = spi.read(1)[0]
    cs.value(1)
    return data

def capture_et_repare(filename="photo_avion_fix.jpg"):
    print("⚙️ Initialisation...")
    write_reg(0x07, 0x80)
    time.sleep(0.1)
    write_reg(0x07, 0x00)
    
    print("📸 Déclenchement...")
    write_reg(0x04, 0x01) 
    time.sleep(0.5) # On laisse le temps à la capture
    
    # Lecture Taille (on répare le décalage immédiatement)
    l1, l2, l3 = read_reg(0x42), read_reg(0x43), read_reg(0x44)
    raw_length = (l3 << 16) | (l2 << 8) | l1
    real_length = raw_length >> 1 
    print(f"📦 Taille réelle détectée : {real_length} octets")

    try:
        with open(filename, "wb") as f:
            cs.value(0)
            spi.write(bytearray([0x3D])) # Burst read
            
            # L'octet DUMMY contient le tout premier bit de l'image (le bit 7 du FF)
            prev_raw = spi.read(1)[0]
            
            remaining = real_length
            print("💾 Réparation du flux JPEG en cours...")
            
            while remaining > 0:
                chunk = spi.read(min(remaining, 512))
                corrected = bytearray(len(chunk))
                
                for i in range(len(chunk)):
                    # RECONSTRUCTION : 
                    # On décale l'octet actuel à droite
                    # On récupère le bit de poids faible de l'octet précédent pour en faire le bit 7
                    current_raw = chunk[i]
                    corrected[i] = (current_raw >> 1) | ((prev_raw & 0x01) << 7)
                    prev_raw = current_raw
                
                f.write(corrected)
                remaining -= len(chunk)
            
            cs.value(1)
        print(f"✅ Terminé ! Le fichier {filename} devrait être parfaitement lisible.")
    except Exception as e:
        print(f"❌ Erreur : {e}")
        cs.value(1)

# Lancement
capture_et_repare()