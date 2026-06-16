from lib.configuration.reduire_conso_energie import reduire_conso_energie
from lib.moteur.IBusServoController import IBusServoController
from lib.configuration.configuration import configuration
reduire_conso_energie()
print("Lancement")
controller = IBusServoController(configuration)
controller.run()
