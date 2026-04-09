from machine import Pin, SPI
import time

# Configuration Heltec V4 (SPI)
SCK_PIN, MISO_PIN, MOSI_PIN, CS_PIN = 40, 41, 42, 39

# Baudrate à 100000 comme dans ton script fonctionnel
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

def test_connection():
    vid = read_reg(0x40) 
    print(f"🔍 Test de connexion SPI : ID reçu = {hex(vid)}")
    if vid == 0x00 or vid == 0xFF:
        print("❌ La caméra ne répond pas sur le bus SPI. Vérifiez le câblage.")
    else:
        print("✅ La communication SPI semble fonctionnelle.")

def capture_photo(filename="photo.jpg", apply_bitshift=False):
    print(f"\n⚙️ --- Démarrage Capture : {filename} ---")
    
    # 1. Reset de la puce mémoire (Logique stricte du script fonctionnel)
    write_reg(0x07, 0x80)
    time.sleep(0.1)
    write_reg(0x07, 0x00)
    
    # 2. Déclenchement de la capture
    print("📸 Clic ! Prise de la photo...")
    write_reg(0x04, 0x01) 
    
    # 3. Attente stricte (Pas de boucle "while" problématique)
    print("⏳ Traitement de l'image (0.5s)...")
    time.sleep(0.5) 

    # 4. Récupération de la taille de l'image
    l1, l2, l3 = read_reg(0x42), read_reg(0x43), read_reg(0x44)
    raw_length = (l3 << 16) | (l2 << 8) | l1
    
    # Si on applique le hack de décalage, la vraie taille est divisée par 2
    real_length = raw_length >> 1 if apply_bitshift else raw_length
    print(f"📦 Taille détectée : {real_length} octets (Taille brute: {raw_length})")

    if real_length == 0 or real_length > 2000000:
        print("❌ Erreur : Taille de fichier absurde (0 ou trop grande).")
        return

    # 5. Téléchargement via SPI
    print(f"💾 Téléchargement en cours (Mode Décalage : {apply_bitshift})...")
    try:
        with open(filename, "wb") as f:
            cs.value(0)
            spi.write(bytearray([0x3D])) # Commande de lecture en rafale (Burst read)
            
            if apply_bitshift:
                # VERSION AVEC RECONSTRUCTION DES BITS (Ton correctif indispensable)
                prev_raw = spi.read(1)[0]
                remaining = real_length
                
                while remaining > 0:
                    chunk_size = min(remaining, 512)
                    chunk = spi.read(chunk_size)
                    corrected = bytearray(chunk_size)
                    
                    for i in range(chunk_size):
                        current_raw = chunk[i]
                        # On décale à droite et on réinjecte le bit perdu de l'octet précédent
                        corrected[i] = (current_raw >> 1) | ((prev_raw & 0x01) << 7)
                        prev_raw = current_raw
                    
                    f.write(corrected)
                    remaining -= chunk_size
            else:
                # VERSION CLASSIQUE (SANS MODIFICATION)
                remaining = raw_length # On utilise la taille brute ici car pas de division
                while remaining > 0:
                    chunk_size = min(remaining, 1024)
                    chunk = spi.read(chunk_size)
                    f.write(chunk)
                    remaining -= chunk_size
            
            cs.value(1)
        print(f"✅ Terminé ! Le fichier {filename} est sauvegardé.")
        
    except Exception as e:
        print(f"❌ Erreur lors de l'écriture du fichier : {e}")
        cs.value(1)

# ==========================================
# EXÉCUTION DU PROGRAMME
# ==========================================

# Test de communication initial
test_connection()

# Test 1 : Lecture classique (Normale, sans le décalage)
capture_photo("photo_classique.jpg", apply_bitshift=False)

# On laisse un peu de temps à la mémoire de l'ESP32
time.sleep(1)

# Test 2 : Lecture avec ton correctif de décalage de bits
capture_photo("photo_decalee.jpg", apply_bitshift=True)