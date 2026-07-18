import json

# Simulation du fichier ou script externe contenant le corpus documentaire
# Dans une architecture modulaire, cette variable proviendrait d'un 'import corpus_externe'
donnees_externes_importees = {
    "Bastille": {
        "description": "La place de la Bastille est un nœud majeur de la circulation parisienne.",
        "pourquoi_ce_nom": "La station tire son nom de l'ancienne forteresse de la Bastille, détruite lors de la Révolution française en 1789."
    },
    "Louvre - Rivoli": {
        "description": "Cette station dessert l'hypercentre touristique et culturel de la capitale.",
        "pourquoi_ce_nom": "Le toponyme associe le palais des rois de France à la rue de Rivoli, percée sous le Premier Empire pour célébrer une victoire militaire."
    }
}

def restructurer_base_donnees(chemin_fichier_entree, chemin_fichier_sortie, source_externe):
    # Le mode d'ouverture 'r' charge le fichier en mémoire pour analyse
    with open(chemin_fichier_entree, 'r', encoding='utf-8') as fichier:
        base_donnees = json.load(fichier)

    # L'itération sur items() permet d'accéder simultanément à l'identifiant de la station et à ses attributs
    for nom_station, contenu in base_donnees.items():
        
        # La sécurisation de l'arborescence prévient les erreurs d'accès aux clés inexistantes
        if "histoire" not in contenu:
            contenu["histoire"] = {}
            
        histoire = contenu["histoire"]

        # Phase 1 : Vérification de la présence de la station dans le nouveau corpus externe
        if nom_station in source_externe:
            donnees_enrichies = source_externe[nom_station]
            
            # Injection des données externes vers la nouvelle nomenclature
            # La méthode get() évite l'arrêt du script si la clé est absente, en renvoyant une chaîne vide par défaut
            histoire["description courte"] = donnees_enrichies.get("description", "")
            histoire["description longue"] = donnees_enrichies.get("pourquoi_ce_nom", "")
            
            # Suppression explicite des anciennes clés pour assainir le dictionnaire
            histoire.pop("description", None)
            histoire.pop("pourquoi_ce_nom", None)
            
        else:
            # Phase 2 : Traitement de secours pour les stations absentes du script externe
            # La fonction pop(clé, valeur_par_défaut) capture l'ancienne donnée et efface l'ancienne étiquette
            ancienne_description = histoire.pop("description", "")
            ancien_pourquoi = histoire.pop("pourquoi_ce_nom", "")
            
            # Transfert des valeurs conservées vers le nouveau format structurel
            histoire["description courte"] = ancienne_description
            histoire["description longue"] = ancien_pourquoi

    # La sérialisation transforme l'objet Python en chaîne de caractères formatée pour l'exportation
    with open(chemin_fichier_sortie, 'w', encoding='utf-8') as fichier_export:
        # Le paramètre ensure_ascii=False garantit la préservation des accents et caractères typographiques français
        json.dump(base_donnees, fichier_export, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    # L'exécution de la fonction déclenche la lecture, la mutation en mémoire, puis l'écriture du nouveau fichier
    restructurer_base_donnees("data.json", "data_restructuree.json", donnees_externes_importees)