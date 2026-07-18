import json

def optimiser_base_donnees(chemin_entree, chemin_sortie):
    with open(chemin_entree, 'r', encoding='utf-8') as fichier:
        donnees_brutes = json.load(fichier)

    base_optimisee = {}

    for nom_station, attributs in donnees_brutes.items():
        # Centralisation des thèmes dans une liste de tags unifiée
        tags_jeu = []
        if attributs.get("theme"):
            tags_jeu.extend(attributs["theme"])
        if attributs.get("sous_theme"):
            tags_jeu.extend(attributs["sous_theme"])

        # Uniformisation du champ siècle qui peut être nul ou une liste
        siecles = attributs.get("siecle")
        if siecles is None:
            siecles = []
        elif isinstance(siecles, str):
            siecles = [siecles]

        # Construction de la nouvelle arborescence stricte
        base_optimisee[nom_station] = {
            "geographie": {
                "lignes": attributs.get("lignes", []),
                "commune": attributs.get("commune"),
                "code_insee": attributs.get("code_insee"),
                "latitude": attributs.get("latitude"),
                "longitude": attributs.get("longitude")
            },
            "histoire": {
                "type_origine": attributs.get("type_origine"),
                "sous_type_origine": attributs.get("sous_type_origine"),
                "siecles": siecles,
                "description": attributs.get("description"),
                "pourquoi_ce_nom": attributs.get("pourquoi_ce_nom"),
                "details_personne": attributs.get("personne")
            },
            # Suppression des doublons potentiels et tri alphabétique des tags
            "tags": sorted(list(set(tags_jeu)))
        }

    with open(chemin_sortie, 'w', encoding='utf-8') as fichier_sortie:
        json.dump(base_optimisee, fichier_sortie, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    optimiser_base_donnees('stations_finales.json', 'stations_optimisees.json')