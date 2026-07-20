import json
import time
import logging
import os
from google import genai
from google.genai import errors

# Configuration du système de journalisation (Logging)
# Le niveau DEBUG permet de voir le détail des opérations. Changez en INFO pour réduire le texte affiché.
logging.basicConfig(
    level=logging.DEBUG, 
    format="%(asctime)s - %(levelname)s - %(message)s"
)

FICHIER_ENTREE = "data.json"
FICHIER_SORTIE = "data_enrichi_tags.json"
FICHIER_CLE = ".venv/cle.txt"

TAGS_AUTORISES = [
    "Arts et Culture",
    "Écrivains et Philosophes",
    "Géographie et International",
    "Institutions Civiques et Politiques",
    "Les Femmes Illustres",
    "Les figures de la Résistance",
    "Révolution et République",
    "Sciences, Médecine et Techniques",
    "Les victoires et batailles militaires",
    "Châteaux et Palais historiques",
    "Architecture urbaine : Les grandes gares",
    "L'architecture religieuse",
    "Monuments et Lieux Emblématiques",
    "Anciens Villages et Hameaux",
    "Espaces Verts et Nature",
    "Les Portes de Paris",
    "Topographie et Urbanisme"
]

def initialiser_client():
    """Lit la clé API locale avec vérification de l'existence du fichier."""
    logging.debug(f"Tentative de lecture de la clé API depuis {FICHIER_CLE}")
    try:
        with open(FICHIER_CLE, "r", encoding="utf-8") as fichier:
            cle_api = fichier.read().strip()
            if not cle_api:
                raise ValueError("Le fichier de la clé API est vide.")
        logging.info("Client Google GenAI initialisé avec succès.")
        return genai.Client(api_key=cle_api)
    except FileNotFoundError:
        logging.critical(f"Fichier introuvable : {FICHIER_CLE}. Veuillez vérifier le chemin.")
        raise
    except Exception as e:
        logging.critical(f"Erreur inattendue lors de la lecture de la clé : {e}")
        raise

def charger_donnees(chemin_fichier):
    """Charge le contenu du fichier JSON avec vérification de l'intégrité."""
    logging.debug(f"Chargement des données depuis {chemin_fichier}")
    try:
        with open(chemin_fichier, "r", encoding="utf-8") as f:
            donnees = json.load(f)
            logging.info(f"{len(donnees)} stations chargées depuis {chemin_fichier}.")
            return donnees
    except FileNotFoundError:
        logging.critical(f"Le fichier source {chemin_fichier} n'existe pas.")
        raise
    except json.JSONDecodeError as e:
        logging.critical(f"Le fichier {chemin_fichier} contient du JSON invalide. Détail : {e}")
        raise

def sauvegarder_donnees(chemin_fichier, donnees):
    """Écrit le dictionnaire Python en sécurisant l'opération d'écriture."""
    logging.debug(f"Sauvegarde en cours vers {chemin_fichier}...")
    try:
        with open(chemin_fichier, "w", encoding="utf-8") as f:
            json.dump(donnees, f, indent=4, ensure_ascii=False)
        logging.debug("Sauvegarde réussie.")
    except IOError as e:
        logging.error(f"Impossible d'écrire dans le fichier {chemin_fichier}. Détail : {e}")

def generer_enrichissement(client, nom_station):
    """Interroge l'API, nettoie la réponse et valide la structure des données."""
    tags_string = ", ".join(f"'{tag}'" for tag in TAGS_AUTORISES)
    
    prompt = f"""
    Agis comme un historien spécialiste du métro parisien et un expert en classification de données.
    Analyse le nom de la station de métro '{nom_station}'. Fais particulièrement attention aux noms composés.
    
    Fournis les éléments suivants :
    "description courte" : 25 mots maximum expliquant l'origine du nom.
    "description longue" : contexte historique complet et anecdotes.
    "tags" : Un tableau contenant entre 1 et 3 tags maximum, choisis STRICTEMENT parmi : [{tags_string}].
    "ambiguite" : Un booléen (true ou false). Mets true si l'origine est incertaine ou complexe. Sinon false.

    Retourne le résultat obligatoirement sous forme de code JSON avec les clés exactes "description courte", "description longue", "tags" et "ambiguite". N'ajoute aucun texte autour.
    """
    
    logging.debug(f"Envoi de la requête à l'API pour la station : {nom_station}")
    
    # Appel de l'API (les erreurs réseau seront gérées dans la fonction appelante)
    reponse = client.models.generate_content(
        model='gemini-flash-lite-latest',
        contents=prompt
    )
    
    if not reponse.text:
        raise ValueError("L'API a retourné une réponse vide.")

    # Nettoyage robuste pour extraire uniquement le JSON
    texte_brut = reponse.text.strip()
    if texte_brut.startswith('```json'):
        texte_brut = texte_brut.removeprefix('```json')
    elif texte_brut.startswith('```'):
        texte_brut = texte_brut.removeprefix('```')
    texte_brut = texte_brut.removesuffix('```').strip()
    
    logging.debug(f"Texte brut nettoyé reçu de l'API : {texte_brut}")
    
    # Vérification de l'intégrité du JSON renvoyé par l'IA
    try:
        donnees_json = json.loads(texte_brut)
    except json.JSONDecodeError as e:
        logging.error(f"L'IA n'a pas renvoyé un JSON valide pour {nom_station}. Brut : {texte_brut}")
        raise ValueError("Format JSON invalide généré par le modèle.") from e

    return donnees_json

def charger_donnees_enrichies(chemin_fichier):
    """Charge le fichier de sortie s'il existe, sinon initialise un dictionnaire vide."""
    logging.debug(f"Vérification de l'existence du fichier cible : {chemin_fichier}")
    try:
        with open(chemin_fichier, "r", encoding="utf-8") as f:
            donnees = json.load(f)
            logging.info(f"Reprise du travail : {len(donnees)} stations déjà enrichies trouvées.")
            return donnees
    except FileNotFoundError:
        logging.info("Aucun fichier enrichi existant. Création d'une nouvelle base de données en mémoire.")
        return {}
    except json.JSONDecodeError:
        logging.warning(f"Le fichier {chemin_fichier} est corrompu. Démarrage avec un dictionnaire vide.")
        return {}

def traiter_base_de_donnees():
    """Orchestre la logique globale avec séparation stricte entre source et destination."""
    try:
        client = initialiser_client()
        stations_sources = charger_donnees(FICHIER_ENTREE)
        # Nouveau : chargement des données déjà traitées
        stations_enrichies = charger_donnees_enrichies(FICHIER_SORTIE)
    except Exception:
        logging.critical("Arrêt du script suite à un échec d'initialisation.")
        return

    compteur_succes = 0
    compteur_erreurs = 0
    
    for nom_station, attributs_source in stations_sources.items():
        
        # Nouvelle condition : on vérifie la présence dans le fichier de destination
        if nom_station in stations_enrichies:
            logging.debug(f"Station ignorée (déjà présente dans data_enrichi_tags.json) : {nom_station}")
            continue
            
        logging.info(f"Traitement de la station : {nom_station}")
        
        try:
            donnees_generees = generer_enrichissement(client, nom_station)
            
            # Création d'une copie pour ne pas altérer les données en mémoire du fichier source
            nouvelle_station = attributs_source.copy()
            
            nouvelle_station["description courte"] = str(donnees_generees.get("description courte", ""))
            nouvelle_station["description longue"] = str(donnees_generees.get("description longue", ""))
            
            tags_recus = donnees_generees.get("tags", [])
            nouvelle_station["tags"] = tags_recus if isinstance(tags_recus, list) else []
            nouvelle_station["ambiguite"] = bool(donnees_generees.get("ambiguite", False))
            
            # Nettoyage des anciennes métadonnées obsolètes issues du fichier source
            nouvelle_station.pop("description", None)
            nouvelle_station.pop("pourquoi_ce_nom", None)
            nouvelle_station.pop("tags", None) # Par précaution, supprime un éventuel vieux tag mal formaté
            nouvelle_station["tags"] = tags_recus # Réinjection propre des nouveaux tags
            
            # Ajout de la station propre dans le dictionnaire de destination
            stations_enrichies[nom_station] = nouvelle_station
            
            # Sauvegarde intégrale du dictionnaire de destination
            sauvegarder_donnees(FICHIER_SORTIE, stations_enrichies)
            compteur_succes += 1
            
            logging.info(f"Succès pour {nom_station}. Pause de 5 secondes.")
            time.sleep(5)
            
        except ValueError as ve:
            logging.warning(f"Problème de données pour {nom_station} : {ve}")
            compteur_erreurs += 1
            continue
            
        except errors.APIError as api_err:
            logging.error(f"Erreur API (réseau/quota) pour {nom_station}. Détail : {api_err}")
            logging.info("Mise en pause de 60 secondes pour réinitialisation du quota...")
            time.sleep(60)
            
        except Exception as e:
            logging.error(f"Erreur inattendue lors du traitement de {nom_station} : {e}")
            logging.info("Mise en pause de 60 secondes par précaution...")
            time.sleep(60)

    logging.info(f"Traitement terminé. Succès lors de cette session : {compteur_succes}. Erreurs ignorées : {compteur_erreurs}.")

if __name__ == "__main__":
    traiter_base_de_donnees()
