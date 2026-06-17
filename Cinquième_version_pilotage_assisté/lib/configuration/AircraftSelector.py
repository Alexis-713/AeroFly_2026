# Classe permettant de sélectionner automatiquement
# un modèle d’avion à partir de son immatriculation
class AircraftSelector:

    def __init__(self, configuration, database, default_model=None):
        # Configuration globale (fichier config)
        self.configuration = configuration
        # Base de données immatriculation → modèle
        self.database = database
        # Modèle par défaut si immatriculation inconnue
        self.default_model = default_model

    def get_model_from_immat(self, immat):
        """ Recherche du modèle associé à l'immatriculation"""
        modele = self.database.get(immat)

        if modele:
            print(f"[INFO] Immatriculation reconnue : {immat}")
            print(f"[INFO] Modèle associé : {modele}")
            return modele

        # Si non trouvé
        print(f"[WARN] Immatriculation inconnue : {immat}")

        # Utilise un modèle par défaut si défini
        if self.default_model:
            print(f"[INFO] Utilisation du modèle par défaut : {self.default_model}")
            return self.default_model

        # Sinon erreur
        raise ValueError("Aucun modèle trouvé et pas de fallback défini")

    def build_config(self, modele):
        # Vérifie que le modèle existe dans la configuration
        if modele not in self.configuration["Modele"]:
            raise ValueError(f"Modèle absent de la configuration : {modele}")

        # Construit la configuration finale
        return {
            "connexion": self.configuration["connexion"],
            "moteur": self.configuration["Modele"][modele]["moteur"]
        }

    def get_config_from_immat(self, immat):
        # Fonction principale :
        # 1. Trouve le modèle via l’immatriculation
        modele = self.get_model_from_immat(immat)

        # 2. Génère la configuration associée
        return self.build_config(modele)