from machine import Pin, SPI
import time

# --- Configuration ---
SCK_PIN, MISO_PIN, MOSI_PIN, CS_PIN = 40, 41, 42, 39

# On garde le réglage qui a permis de passer le Timeout !
spi = SPI(2, baudrate=5000000, polarity=0, phase=1, 
          sck=Pin(SCK_PIN), mosi=Pin(MOSI_PIN), miso=Pin(MISO_PIN))
cs = Pin(CS_PIN, Pin.OUT, value=1)

def write_reg(reg, val):
    cs.value(0)
    spi.write(bytearray([reg | 0x80, val]))
    cs.value(1)

def read_reg(reg):
    cs.value(0)
    spi.write(bytearray([reg & 0x7F]))
    # RETOUR À LA NORMALE : On lit 1 seul octet pour les registres
    data = spi.read(1)
    cs.value(1)
    return data[0]

# def read_reg_fixed(reg):
#     cs.value(0)
#     spi.write(bytearray([reg & 0x7F]))
#     data = spi.read(1)[0]
#     cs.value(1)
#     
#     # Si on détecte le décalage 0x82, on corrige tout
#     if data == 0x82:
#         return data >> 1 # On décale à droite pour retrouver 0x41
#     return data

def init_camera():
    print("⚙️ Initialisation du capteur...")
    write_reg(0x07, 0x80) # Reset
    time.sleep(0.2)
    write_reg(0x07, 0x00)
    time.sleep(0.2)
    
    vid = read_reg(0x40)
    print(f"ID détecté : {hex(vid)}")
    
    write_reg(0x20, 0x01) # Mode JPEG
    write_reg(0x21, 0x00) # Résolution
    print("✅ Configuration envoyée.")

def capture_photo(filename="avion_vol_1.jpg"):
    print("📸 Déclenchement...")
    write_reg(0x04, 0x01) 
    
    # Attente de la capture
    success = False
    for i in range(20): 
        status = read_reg(0x41)
        if status & 0x08: # Bit 3 indique que l'image est prête
            success = True
            break
        time.sleep(0.2)
    
    if not success:
        print("❌ Timeout : La caméra n'a pas verrouillé l'image.")
        return

    # Lire la vraie taille de l'image
    l1 = read_reg(0x42)
    l2 = read_reg(0x43)
    l3 = read_reg(0x44)
    length = (l3 << 16) | (l2 << 8) | l1
    print(f"📦 Image trouvée ! Taille réelle : {length} octets")

    # Sécurité : une photo Arducam fait généralement entre 10 000 et 150 000 octets
    if length == 0 or length > 400000: 
        print("❌ Taille d'image invalide (problème SPI), abandon.")
        return

    # Téléchargement de l'image
    try:
            with open(filename, "wb") as f:
                cs.value(0)
                spi.write(bytearray([0x3D])) # Commande burst
                
                # 1. Lire le dummy byte de la commande Burst et l'ignorer
                dummy = spi.read(1)
                
                # 2. Lire les 20 premiers octets pour debug
                debug_bytes = spi.read(20)
                print("Premiers octets reçus (HEX) :", [hex(b) for b in debug_bytes])
                
                # 3. Vérifier si FF D8 est là (même décalé)
                f.write(debug_bytes)
                
                # On cherche le header JPEG (0xFF 0xD8) dans les premiers octets
                found_header = False
                for _ in range(10): # On teste sur les 10 premiers octets
                    byte = spi.read(1)[0]
                    if byte == 0xFF:
                        next_byte = spi.read(1)[0]
                        if next_byte == 0xD8:
                            f.write(bytearray([0xFF, 0xD8]))
                            found_header = True
                            break
                
                if not found_header:
                    print("❌ Erreur : Header JPEG (FF D8) non trouvé. L'image sera illisible.")
                    cs.value(1)
                    return

                # Lecture du reste
                remaining = length - 2 
                while remaining > 0:
                    chunk_size = min(remaining, 512)
                    f.write(spi.read(chunk_size))
                    remaining -= chunk_size
                cs.value(1)
                
            print(f"💾 Fichier sauvegardé. Essaye de l'ouvrir !")
    except Exception as e:
        print(f"❌ Erreur écriture : {e}")
        cs.value(1)

# --- Exécution ---
init_camera()
capture_photo()