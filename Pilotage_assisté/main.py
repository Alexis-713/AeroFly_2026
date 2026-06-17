# Import des fonctions et classes nécessaires
from lib.configuration.reduire_conso_energie import reduire_conso_energie
from lib.configuration.configuration import configuration
from lib.moteur.IBusServoController import IBusServoController
from lib.configuration.AircraftSelector import AircraftSelector
import time
time.sleep(5)
# Active un mode basse consommation
reduire_conso_energie()

# Base de données des immatriculations :
# associe chaque avion à son modèle
db_immatriculations = {
    "F-GKXA": "Apprentice-STS",
    "F-HNRL": "NR718Y"
}

# Création d'un sélecteur d'avion
# - configuration : paramètres globaux
# - db_immatriculations : correspondance immatriculation -> modèle
# - default_model : modèle utilisé si l'immatriculation est inconnue
selector = AircraftSelector(
    configuration,
    db_immatriculations,
    default_model="Apprentice-STS"  # modèle par défaut
)

# Génère la configuration finale à partir de l'immatriculation choisie
# Ici on sélectionne l'avion "F-GKXA"
config_finale = selector.get_config_from_immat("F-GKXA")

# Création du contrôleur de servos utilisant le protocole IBus
# avec la configuration calculée précédemment
controller = IBusServoController(config_finale)

# Lance le contrôleur (boucle principale du programme)
try:
    controller = IBusServoController(config)
    controller.run()
except Exception as e:
    print("ERREUR:", e)