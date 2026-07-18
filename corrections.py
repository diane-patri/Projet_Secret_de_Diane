import json

def update_station_tags(input_filepath, output_filepath):
    # Chargement des données JSON
    with open(input_filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Définition des règles de fusion et de renommage des étiquettes
    tag_replacements = {
        "Les Portes de Paris (Nord et Est)": "Les Portes de Paris",
        "Les Portes de Paris (Sud et Ouest)": "Les Portes de Paris",
        "Mathématiques, Physique et Biologie": "Sciences, Médecine et Techniques",
        "Sciences et Techniques": "Sciences, Médecine et Techniques",
        "Le patrimoine palatial et institutionnel": "Châteaux et Palais historiques"
    }

    # Définition des stations nécessitant l'étiquette "Institutions Civiques et Politiques"
    # Cela permet de scinder l'ancienne catégorie institutionnelle/palatiale
    civic_institutions = [
        "Assemblée Nationale", 
        "Hôtel de Ville", 
        "Mairie d'Aubervilliers", 
        "Mairie d'Issy", 
        "Mairie d'Ivry", 
        "Mairie de Clichy", 
        "Mairie de Montreuil", 
        "Mairie de Montrouge", 
        "Mairie de Saint-Ouen", 
        "Mairie des Lilas"
    ]

    # Définition des ajouts spécifiques par thématique
    specific_additions = {
        "Les victoires et batailles militaires": [
            "Tolbiac", "Trocadéro"
        ],
        "Monuments et Lieux Emblématiques": [
            "Tuileries", "Père Lachaise"
        ],
        "Châteaux et Palais historiques": [
            "Tuileries"
        ],
        "Histoire et Politique": [
            "George V"
        ],
        "Géographie et International": [
            "Rome", "Liège", "Argentine", "Europe", "Danube", "Crimée", "Pyrénées"
        ],
        "Espaces Verts et Nature": [
            "Buttes Chaumont", "Ranelagh", "Pointe du Lac", "Pré-Saint-Gervais"
        ],
        "Anciens Villages et Hameaux": [
            "Passy", "Belleville", "Charonne", "Ménilmontant", "La Chapelle", 
            "Église d'Auteuil", "Porte d'Auteuil", "Michel-Ange - Auteuil"
        ]
    }

    # Inversion du dictionnaire pour un accès direct par nom de station
    additions_by_station = {}
    for tag, stations in specific_additions.items():
        for station in stations:
            if station not in additions_by_station:
                additions_by_station[station] = []
            additions_by_station[station].append(tag)

    # Parcours et mise à jour de chaque station
    for station_name, station_info in data.items():
        current_tags = station_info.get("tags", [])
        new_tags = set()

        # Application des fusions et remplacements
        for tag in current_tags:
            if tag in tag_replacements:
                # Gestion de la scission Palatial / Institutionnel
                if tag == "Le patrimoine palatial et institutionnel" and station_name in civic_institutions:
                    new_tags.add("Institutions Civiques et Politiques")
                else:
                    new_tags.add(tag_replacements[tag])
            else:
                new_tags.add(tag)

        # Application des ajouts spécifiques
        if station_name in additions_by_station:
            for new_tag in additions_by_station[station_name]:
                new_tags.add(new_tag)

        # Mise à jour de la liste des étiquettes (triée par ordre alphabétique pour la cohérence)
        station_info["tags"] = sorted(list(new_tags))

    # Sauvegarde des données mises à jour
    with open(output_filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# Exécution du script (à adapter selon les noms exacts de vos fichiers)
update_station_tags('data.json', 'data.json')