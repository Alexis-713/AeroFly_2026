from machine import Pin, I2C, PWM
import time

# ==========================================
# PARTIE 1 : CONFIGURATION DU CÂBLAGE (OV5640)
# D'après ton image fournie.
# ==========================================

print("🚀 Démarrage du programme de diagnostic caméra OV5640...")

# 1. Bus de Contrôle (I2C) - SCL (SIOC) / SDA (SIOD)
I2C_SCL_PIN = 41
I2C_SDA_PIN = 42
# Adresse I2C par défaut de l'OV5640 (souvent 0x3C ou 0x3D)
OV5640_I2C_ADDR = 0x3C 

# 2. Signaux de Synchronisation (Clocks & Sync)
PIN_PCLK  = 47
PIN_XCLK  = 48
PIN_VSYNC = 21
PIN_HREF  = 33 # Aussi noté HS

# 3. Signaux de Contrôle
PIN_RESET = 46
# PWDN (Power Down) est relié au GND d'après ton tableau.

# 4. Bus de Données (D2-D9)
# Note : C'est un bus de 8 bits, mais noté D2-D9 dans ton tableau.
DATA_PINS = [1, 2, 3, 4, 5, 6, 7, 45] # D2 -> D9

def wake_up_camera():
    print("🧠 Tentative de réveil de l'OV5640...")

    # 1. Activer l'horloge XCLK (Indispensable pour l'I2C)
    # On génère un signal carré à 20MHz sur le GPIO 48
    print("[HW] Génération du signal XCLK sur GPIO 48 (20MHz)...")
    xclk = PWM(Pin(PIN_XCLK), freq=20000000, duty=512) 

    # 2. Reset Matériel
    res = Pin(PIN_RESET, Pin.OUT)
    res.value(0)
    time.sleep(0.1)
    res.value(1)
    time.sleep(0.1)

    # 3. Initialisation I2C avec Pull-ups internes
    # L'ESP32-S3 a des pull-ups, mais ils sont parfois faibles.
    print("[I2C] Scan du bus...")
    i2c = I2C(0, scl=Pin(I2C_SCL_PIN), sda=Pin(I2C_SDA_PIN), freq=100000)
    
    devices = i2c.scan()
    
    if not devices:
        print("❌ Toujours rien. Tentons d'inverser SDA et SCL au cas où...")
        i2c = I2C(0, scl=Pin(I2C_SDA_PIN), sda=Pin(I2C_SCL_PIN), freq=100000)
        devices = i2c.scan()

    if devices:
        print(f"✅ TROUVÉ ! Périphériques détectés : {[hex(d) for d in devices]}")
        # L'adresse attendue est 0x3C
    else:
        print("❌ Échec total. Vérifiez si vous avez des résistances de 4.7k ohms sur SDA/SCL.")

wake_up_camera()


# ==========================================
# PARTIE 2 : FONCTIONS DE BASE ET DEBUG I2C
# ==========================================

# Initialisation de l'I2C
try:
    print(f"[I2C] Initialisation sur SCL={I2C_SCL_PIN}, SDA={I2C_SDA_PIN}...")
    i2c = I2C(0, scl=Pin(I2C_SCL_PIN), sda=Pin(I2C_SDA_PIN), freq=400000)
    print("[I2C] ✅ Initialisation réussie.")
except Exception as e:
    print(f"[I2C] ❌ Échec critique : {e}")
    raise SystemExit

def print_log(level, msg):
    print(f"[{level}] {msg}")

def ov5640_write_reg(reg, val):
    # OV5640 utilise des adresses de registres sur 16 bits
    data = bytearray([reg >> 8, reg & 0xFF, val])
    try:
        i2c.writeto(OV5640_I2C_ADDR, data)
    except Exception as e:
        print_log("I2C_ERR", f"Impossible d'écrire sur Reg {hex(reg)}: {e}")

def ov5640_read_reg(reg):
    # OV5640 utilise des adresses de registres sur 16 bits
    addr = bytearray([reg >> 8, reg & 0xFF])
    try:
        i2c.writeto(OV5640_I2C_ADDR, addr, False)
        return i2c.readfrom(OV5640_I2C_ADDR, 1)[0]
    except Exception as e:
        print_log("I2C_ERR", f"Impossible de lire Reg {hex(reg)}: {e}")
        return None


# ==========================================
# PARTIE 3 : SÉQUENCE D'INITIALISATION MATÉRIELLE
# ==========================================

def init_hardware_camera():
    print_log("HW", "Démarrage de la séquence de Reset matériel...")
    
    # Configuration des pins de contrôle
    reset_pin = Pin(PIN_RESET, Pin.OUT)
    
    # 1. Reset cycle : Mettre à 0, attendre, mettre à 1
    print_log("HW", " -> Reset Pin à 0 (RESET actif)")
    reset_pin.value(0)
    time.sleep(0.1)
    print_log("HW", " -> Reset Pin à 1 (Caméra active)")
    reset_pin.value(1)
    time.sleep(0.2) # Laisser le temps à la caméra de se stabiliser
    
    print_log("HW", "Séquence de Reset matériel terminée.")


def init_software_camera():
    print_log("SW", "Démarrage du diagnostic logiciel (I2C)...")
    
    # 1. Scan I2C pour vérifier la présence
    print_log("SW", " -> Scan du bus I2C...")
    devices = i2c.scan()
    if not devices:
        print_log("SW", " ❌ ALERTE : Aucun périphérique I2C détecté !")
        print_log("SW", "    -> Vérifie l'alimentation 3.3V, le GND, SCL (41) et SDA (42).")
        return False
    else:
        print_log("SW", f" -> Périphériques I2C détectés : {[hex(d) for d in devices]}")
    
    if OV5640_I2C_ADDR not in devices:
        print_log("SW", f" ❌ ALERTE : La caméra (adresse {hex(OV5640_I2C_ADDR)}) n'est pas détectée !")
        print_log("SW", "    -> L'adresse I2C de ton module est peut-être différente.")
        return False
    else:
        print_log("SW", " ✅ Caméra détectée sur le bus I2C.")

    # 2. Vérification de l'ID du capteur (Registres CHIP_ID)
    print_log("SW", " -> Lecture de l'ID du capteur (Reg 0x300A/0x300B)...")
    chip_id_h = ov5640_read_reg(0x300A)
    chip_id_l = ov5640_read_reg(0x300B)
    
    if chip_id_h is not None and chip_id_l is not None:
        chip_id = (chip_id_h << 8) | chip_id_l
        print_log("SW", f" -> CHIP ID détecté : {hex(chip_id)} (Attendu: 0x5640)")
        if chip_id == 0x5640:
            print_log("SW", " ✅ CHIP ID correct !")
        else:
            print_log("SW", " ⚠️ CHIP ID incorrect ! Problème de communication.")
            return False
    else:
        print_log("SW", " ❌ Impossible de lire le CHIP ID.")
        return False

    # 3. Soft Reset Logiciel
    print_log("SW", " -> Envoi du Soft Reset (System Control Reg 0x3008)...")
    # Registre 0x3008 : Mettre le bit 7 à 1 pour le Reset, puis à 0
    ov5640_write_reg(0x3008, 0x82)
    time.sleep(0.1)
    ov5640_write_reg(0x3008, 0x02) # Normal operation
    print_log("SW", " -> Soft Reset terminé.")

    # 4. Configuration Minimale (TRES SIMPLIFIÉE)
    print_log("SW", " -> Configuration minimale des horloges...")
    # C'est ici qu'on devrait envoyer des centaines de registres.
    # On se contente d'essayer d'activer l'horloge système (SCK).
    # Ces valeurs sont des exemples et dépendent de ton module précis.
    # ov5640_write_reg(0x3103, 0x03) # Exemple: System clock output
    
    print_log("SW", "Initialisation logiciel terminée.")
    return True


# ==========================================
# PARTIE 4 : LA CAPTURE D'IMAGE (LE DÉFI DVP)
# ==========================================

# Configuration des pins de données et de synchronisation
# Note : Le DVP nécessite des interrupts ou du DMA en C, impossible en Python simple.
# Ce code est un "sondage" (polling) qui sera très lent.

def configure_dvp_pins():
    print_log("DVP", "Configuration des broches DVP...")
    # Synchronisation
    Pin(PIN_PCLK, Pin.IN)
    vsync_pin = Pin(PIN_VSYNC, Pin.IN)
    Pin(PIN_HREF, Pin.IN)
    # Données
    data_pin_objs = []
    for pin_num in DATA_PINS:
        data_pin_objs.append(Pin(pin_num, Pin.IN))
    print_log("DVP", " ✅ Broches DVP configurées en entrée.")
    return vsync_pin, data_pin_objs


    

def capture_photo_polling(vsync_pin, data_pin_objs, filename="photo.raw"):
    # ATTENTION : Ce code est une preuve de concept et sera EXTRÊMEMENT lent.
    # Il ne produira probablement pas de JPEG lisible sans pilote DMA native.
    # Il enregistre des données brutes (RAW) que tu pourrais essayer d'analyser.
    
    print_log("CAP", " --- DÉBUT DE LA SÉQUENCE DE CAPTURE (Polling) ---")
    
    # 1. Attente de la synchronisation verticale (VSYNC)
    print_log("CAP", " -> Attente de VSYNC actif (début d'image)...")
    # OV5640 : VSYNC est souvent actif bas.
    timeout = 100000
    while vsync_pin.value() == 1 and timeout > 0:
        timeout -= 1
    if timeout <= 0:
        print_log("CAP", " ❌ Timeout : VSYNC n'est jamais passé à 0.")
        return

    # 2. Capture de données (Simplifiée à l'extrême pour le débug)
    # On va capturer un petit bloc de données brutes.
    print_log("CAP", " -> VSYNC détecté ! Lecture de données brutes...")
    buffer_raw = bytearray(1024 * 4) # 4 Ko de test
    
    # C'est ici que ça coince : MicroPython est trop lent pour le PCLK.
    start_time = time.ticks_ms()
    for i in range(len(buffer_raw)):
        # Sondage de PCLK (horloge pixel)
        # Mais VSYNC et HREF peuvent changer entre temps...
        byte = 0
        # On lit les 8 bits de données à la volée.
        for bit_pos, pin_obj in enumerate(data_pin_objs):
            if pin_obj.value() == 1:
                byte |= (1 << bit_pos)
        buffer_raw[i] = byte
    end_time = time.ticks_ms()

    duration = time.ticks_diff(end_time, start_time)
    print_log("CAP", f" ✅ Capture terminée en {duration} ms.")
    print_log("CAP", f" -> Données capturées : {buffer_raw[:32].hex().upper()}...")

    # 3. Stockage sur l'ESP32
    print_log("CAP", f" -> Sauvegarde de {len(buffer_raw)} octets sous {filename}...")
    try:
        with open(filename, "wb") as f:
            f.write(buffer_raw)
        print_log("CAP", " ✅ Fichier sauvegardé réussie.")
    except Exception as e:
        print_log("CAP", f" ❌ Échec de la sauvegarde : {e}")


# ==========================================
# PARTIE 5 : EXÉCUTION DU PROGRAMME
# ==========================================

print("\n=== Lancement du diagnostic complet ===\n")

# 1. Matériel
init_hardware_camera()

# 2. Logiciel (I2C)
if init_software_camera():
    
    # 3. Préparation DVP
    vsync_pin, data_pins = configure_dvp_pins()
    
    # 4. Tentative de capture
    print("\n⚠️ Avertissement : La capture DVP en Python est TRES lente et peu fiable.")
    print("⚠️ Si tu obtiens un fichier, ce seront des données brutes (RAW) difficiles à lire.")
    capture_photo_polling(vsync_pin, data_pins, "test_brut.raw")

else:
    print_log("GLOBAL", "❌ Impossible d'initialiser la caméra via I2C. Arrêt.")

print("\n=== Diagnostic terminé ===")