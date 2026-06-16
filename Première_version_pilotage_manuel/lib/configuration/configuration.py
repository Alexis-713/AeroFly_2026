# lib/moteur/configuration.py

configuration = {
    "connexion": {
        "baudrate": 115200,
        "bits": 8,
        "parity": None,
        "stop": 1,
        "pin_rx": 47
    },
    "moteur": {
        # Hélice / ESC
        "moteur_gaz": {
            "pin": 3,
            "frequence": 50,
            "etat_actif_min": 1000,
            "etat_actif_max": 2000,
            "centre": 1500,
            "channel": 3,
            "type": "esc"
        },
        # Servos
        "servo_profondeur": {
            "pin": 2,
            "frequence": 50,
            "etat_actif_min": 1000,
            "etat_actif_max": 2000,
            "centre": 1500,
            "channel": 2,
            "type": "servo"
        },
        "servo_ailerons1": {
            "pin": 4,
            "frequence": 50,
            "etat_actif_min": 1000,
            "etat_actif_max": 2000,
            "centre": 1500,
            "channel": 1,
            "type": "servo"
        },
        "servo_ailerons2": {
            "pin": 5,
            "frequence": 50,
            "etat_actif_min": 1000,
            "etat_actif_max": 2000,
            "centre": 1500,
            "channel": 1,
            "type": "servo"
        },
        "servo_direction": {
            "pin": 1,
            "frequence": 50,
            "etat_actif_min": 1100,
            "etat_actif_max": 1900,
            "centre": 1500,
            "channel": 4,
            "type": "servo"
        }
    }
}