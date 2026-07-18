import json

def extraire_valeur_par_chemin(donnees, chemin):
    """
    Parcourt un dictionnaire imbriqué en suivant un chemin défini par des points.
    Retourne la valeur finale ou None si le chemin est invalide.
    """
    cles = chemin.split('.')
    valeur_actuelle = donnees
    
    for cle in cles:
        if isinstance(valeur_actuelle, dict) and cle in valeur_actuelle:
            valeur_actuelle = valeur_actuelle[cle]
        else:
            return None
            
    return valeur_actuelle

def compiler_listes_stations():
    """
    Charge les configurations et les stations, applique les filtres
    et génère un nouveau fichier JSON contenant les résultats.
    """
    # Chargement des bases de données
    with open("data.json", "r", encoding="utf-8") as fichier_data:
        toutes_stations = json.load(fichier_data)

    with open("sessions_config.json", "r", encoding="utf-8") as fichier_config:
        configuration_sessions = json.load(fichier_config)

    dictionnaire_resultat = {}

    # Parcours systématique des catégories et de leurs sessions
    for nom_categorie, sessions in configuration_sessions.items():
        dictionnaire_resultat[nom_categorie] = {}
        
        for nom_session, parametres in sessions.items():
            chemin = parametres.get("chemin_donnee")
            valeur_recherchee = parametres.get("valeur_recherchee")
            type_recherche = parametres.get("type_recherche")
            
            stations_valides = []

            # Évaluation de chaque station face aux critères de la session
            for nom_station, donnees_station in toutes_stations.items():
                valeur_extraite = extraire_valeur_par_chemin(donnees_station, chemin)
                
                if valeur_extraite is not None:
                    if type_recherche == "inclusion" and isinstance(valeur_extraite, (list, str)):
                        if valeur_recherchee in valeur_extraite:
                            stations_valides.append(nom_station)
                            
                    elif type_recherche == "exact":
                        if valeur_extraite == valeur_recherchee:
                            stations_valides.append(nom_station)
                            
                    elif type_recherche == "different":
                        if valeur_extraite != valeur_recherchee:
                            stations_valides.append(nom_station)

            # Assignation de la liste triée par ordre alphabétique pour plus de clarté
            dictionnaire_resultat[nom_categorie][nom_session] = sorted(stations_valides)

    # Exportation du résultat final
    with open("export_sessions_stations.json", "w", encoding="utf-8") as fichier_export:
        json.dump(dictionnaire_resultat, fichier_export, ensure_ascii=False, indent=4)
        
    print("La compilation est terminée. Fichier généré : export_sessions_stations.json")

if __name__ == "__main__":
    compiler_listes_stations()