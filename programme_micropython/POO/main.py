from machine import Pin, SPI
import time

# Importation de vos classes
from Telemetrie.camera import FileManager, Camera
from Telemetrie.pitot_sensor import PitotSensor
from Telemetrie.BME280_comp import CapteurBME280, FiltreLissage

'''
#################### PINOUT SYSTEME ####################
--- Caméra (SPI 2) ---
VCC : 5V (rouge)  | GND : GND (noir)
SCK : GP40 (blanc)| MISO : GP41 (marron) | MOSI : GP42 (jaune) | CS : GP39 (orange)

--- Pitot (I2C 0) ---
SDA : GP43        | SCL : GP44 | VCC : 3.3V

--- BME280 (I2C 1) ---
SDA : GP47        | SCL : GP48 | VCC : 5V
'''

def initialiser_systeme():
    print("=== INITIALISATION DU SYSTEME ===")
    capteurs = {}

    # 1. Initialisation BME280 (Attention : i2c_bus=1 pour éviter le conflit avec le Pitot)
    try:
        print("[1/3] Démarrage BME280...")
        bme = CapteurBME280(sda_pin=47, scl_pin=48, i2c_bus=1)
        capteurs['bme'] = bme
        capteurs['filtre_alt'] = FiltreLissage(alpha=0.1)
    except Exception as e:
        print(f"Erreur BME280: {e}")
        capteurs['bme'] = None

    # 2. Initialisation Capteur Pitot
    try:
        print("[2/3] Démarrage Capteur Pitot...")
        pitot = PitotSensor(sda_pin=43, scl_pin=44, i2c_id=0, debug=False)
        pitot.calibrate()
        capteurs['pitot'] = pitot
    except Exception as e:
        print(f"Erreur Pitot: {e}")
        capteurs['pitot'] = None

    # 3. Initialisation Caméra
    try:
        print("[3/3] Démarrage Caméra...")
        fm = FileManager()
        spi = SPI(2, sck=Pin(40), miso=Pin(41), mosi=Pin(42), baudrate=1000000)
        cs = Pin(39, Pin.OUT)
        cam = Camera(spi, cs, debug_text_enabled=False)
        cam.resolution = '1600X1200'
        cam.set_brightness_level(cam.BRIGHTNESS_PLUS_4)
        cam.set_contrast(cam.CONTRAST_MINUS_3)
        capteurs['cam'] = cam
        capteurs['fm'] = fm
    except Exception as e:
        print(f"Erreur Caméra: {e}")
        capteurs['cam'] = None

    print("=== INITIALISATION TERMINEE ===\n")
    return capteurs

def main():
    systeme = initialiser_systeme()
    
    bme = systeme.get('bme')
    filtre_alt = systeme.get('filtre_alt')
    pitot = systeme.get('pitot')
    cam = systeme.get('cam')
    fm = systeme.get('fm')

    boucle_count = 0

    print("Démarrage de la boucle principale (Ctrl+C pour stopper)...")
    try:
        while True:
            print("-" * 50)
            
            # --- Lecture Environnement (BME280) ---
            if bme and bme.est_connecte():
                temp = bme.lire_temperature()
                press = bme.lire_pression()
                alt_brute = bme.lire_altitude()
                if alt_brute is not None:
                    alt = filtre_alt.mettre_a_jour(alt_brute)
                    print(f"[BME280] Temp: {temp:.1f}°C | Pression: {press:.1f} hPa | Alt: {alt:.1f} m")

            # --- Lecture Vitesse (Pitot) ---
            if pitot:
                p_data = pitot.read()
                if p_data:
                    print(f"[PITOT]  Vitesse: {p_data['speed_kmh']:.2f} km/h (Pression: {p_data['pressure_pa']:.2f} Pa)")

            # --- Gestion Caméra ---
            # Pour ne pas spammer la mémoire, on prend une photo toutes les 10 itérations (ici toutes les ~10 secondes)
            if cam and (boucle_count % 10 == 0):
                print("[CAMERA] Capture en cours...")
                nom_photo = fm.new_jpg_fn('vol_image')
                cam.capture_jpg()
                time.sleep(0.05) # Court délai nécessaire au capteur
                cam.saveJPG(nom_photo, progress_bar=False)
                print(f"[CAMERA] Image enregistrée : {nom_photo}")
            
            boucle_count += 1
            time.sleep(1) # Rythme de la boucle principale à 1Hz

    except KeyboardInterrupt:
        print("\nArrêt du programme principal demandé par l'utilisateur.")

if __name__ == "__main__":
    main()
