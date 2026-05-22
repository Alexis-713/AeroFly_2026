# Fichier : lib/moteur/configuration.py

# Dictionnaire principal de configuration
configuration = {

    # Paramètres de connexion IBUS (UART)
    "connexion": {
        "baudrate": 115200,  # vitesse de communication
        "bits": 8,           # taille des données
        "parity": None,      # pas de parité
        "stop": 1,           # bit de stop
        "pin_rx": 7         # pin de réception
    },
    # Configuration des capteurs
    "capteurs" : {"Pitot" : {"i2c_id":0,"SDA" : 43, "SCL" : 44}, "BME280" : {"i2c_bus" : 1,"SDA" : 47, "SCL" : 48}},
    # Configuration de la caméra
    "camera" : {"SPI" : 2,"SCK":40, "MISO":41,"MOSI":42, "CS":39, "baudrate" : 1000000},
    
    # Configuration des différents modèles d’avion
    "Modele": {

        # =========================
        # Modèle NR718Y
        # =========================
        "NR718Y": {
            "moteur": {

                # ESC (moteur principal)
                "moteur_gaz": {
                    "pin": 3,
                    "frequence": 50,
                    "etat_actif_min": 1000,
                    "etat_actif_max": 2000,
                    "centre": 1500,
                    "channel": 3,   # canal radio
                    "type": "esc"
                },

                # Servo profondeur (pitch)
                "servo_profondeur": {
                    "pin": 2,
                    "frequence": 50,
                    "etat_actif_min": 1000,
                    "etat_actif_max": 2000,
                    "centre": 1500,
                    "channel": 2,
                    "type": "servo",
                    "reverse":True
                },

                # Servos ailerons (roll)
                "servo_ailerons1": {
                    "pin": 4,
                    "frequence": 50,
                    "etat_actif_min": 1000,
                    "etat_actif_max": 2000,
                    "centre": 1500,
                    "channel": 1,
                    "type": "servo",
                    "reverse":False
                },
                "servo_ailerons2": {
                    "pin": 5,
                    "frequence": 50,
                    "etat_actif_min": 1000,
                    "etat_actif_max": 2000,
                    "centre": 1500,
                    "channel": 1,
                    "type": "servo",
                    "reverse":False
                },

                # Servo direction (yaw)
                "servo_direction": {
                    "pin": 1,
                    "frequence": 50,
                    "etat_actif_min": 1100,
                    "etat_actif_max": 1900,
                    "centre": 1500,
                    "channel": 4,
                    "type": "servo",
                    "reverse":False
                }
            }
        },

        # =========================
        # Modèle Apprentice-STS
        # =========================
        "Apprentice-STS": {
            "moteur": {

                # ESC (gaz)
                "moteur_gaz": {
                    "pin": 3,
                    "frequence": 50,
                    "etat_actif_min": 1000,
                    "etat_actif_max": 2000,
                    "centre": 1500,
                    "channel": 3,
                    "type": "esc"
                },

                # Servo profondeur
                "servo_profondeur": {
                    "pin": 2,
                    "frequence": 50,
                    "etat_actif_min": 1100,
                    "etat_actif_max": 1900,
                    "centre": 1500,
                    "channel": 2,
                    "type": "servo",
                    "reverse":False
                },

                # Servos ailerons
                "servo_ailerons1": {
                    "pin": 4,
                    "frequence": 50,
                    "etat_actif_min": 1100,
                    "etat_actif_max": 1900,
                    "centre": 1500,
                    "channel": 1,
                    "type": "servo",
                    "reverse":False
                },
                "servo_ailerons2": {
                    "pin": 5,
                    "frequence": 50,
                    "etat_actif_min": 1100,
                    "etat_actif_max": 1900,
                    "centre": 1500,
                    "channel": 1,
                    "type": "servo",
                    "reverse":False
                },

                # Servo direction
                "servo_direction": {
                    "pin": 1,
                    "frequence": 50,
                    "etat_actif_min": 1100,
                    "etat_actif_max": 1900,
                    "centre": 1500,
                    "channel": 4,
                    "type": "servo",
                    "reverse":True
                }
            }
        }
    }
}