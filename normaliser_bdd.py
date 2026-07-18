import json

def enrichir_tags_thematiques(chemin_entree, chemin_sortie):
    # L'utilisation du bloc 'with' garantit la fermeture sécurisée du fichier après sa lecture.
    with open(chemin_entree, 'r', encoding='utf-8') as fichier:
        donnees = json.load(fichier)

    for nom_station, attributs in donnees.items():
        # La récupération de la liste existante permet d'éviter l'écrasement des tags déjà présents.
        tags = attributs.get("tags", [])

        # Règle 1 : Catégorisation de l'architecture ferroviaire
        if nom_station.startswith("Gare "):
            if "Architecture urbaine : Les grandes gares" not in tags:
                tags.append("Architecture urbaine : Les grandes gares")
            if "Topographie et Urbanisme" not in tags:
                tags.append("Topographie et Urbanisme")

        # Règle 2 : Identification du patrimoine cultuel
        # La liste 'mots_religieux' définit les marqueurs lexicaux de l'architecture sacrée.
        mots_religieux = ["Église", "Temple", "Basilique", "Notre-Dame", "Abbesses", "Trinité"]
        # La fonction 'any()' parcourt la liste de mots et renvoie True si au moins un mot est trouvé dans le nom de la station.
        if any(mot in nom_station for mot in mots_religieux) or nom_station.startswith("Saint-"):
            if "L'architecture religieuse" not in tags:
                tags.append("L'architecture religieuse")
            if "Monuments et Lieux Emblématiques" not in tags:
                tags.append("Monuments et Lieux Emblématiques")

        # Règle 3 : Classification des institutions administratives et politiques
        mots_institutionnels = ["Mairie", "Hôtel de Ville", "Assemblée Nationale", "Palais"]
        if any(mot in nom_station for mot in mots_institutionnels):
            if "Histoire et Politique" not in tags:
                tags.append("Histoire et Politique")

        # Règle 4 : Détection des infrastructures civiles historiques
        if "Pont " in nom_station:
            if "Topographie et Urbanisme" not in tags:
                tags.append("Topographie et Urbanisme")

        # Règle 5 : Recensement du patrimoine palatial
        if "Château" in nom_station:
            if "Le patrimoine palatial et institutionnel" not in tags:
                tags.append("Le patrimoine palatial et institutionnel")
            if "Monuments et Lieux Emblématiques" not in tags:
                tags.append("Monuments et Lieux Emblématiques")

        # Enregistrement des modifications dans le dictionnaire de la station courante
        attributs["tags"] = tags

    # La sérialisation transforme le dictionnaire Python en une chaîne de caractères formatée au standard JSON.
    with open(chemin_sortie, 'w', encoding='utf-8') as fichier:
        json.dump(donnees, fichier, ensure_ascii=False, indent=4)

# Déclenchement de la procédure de traitement
enrichir_tags_thematiques('data.json', 'data.json')