import json

# Chemins de fichiers
data_file = r"C:\Users\patri_d\Documents\projet_git\Projet_Secret_de_Diane\data.json"
missing_file = r"C:\Users\patri_d\Documents\projet_git\Projet_Secret_de_Diane\arrets_manquants.json"


def fusionner_manquants():
    # 1. Charger la base existante
    with open(data_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 2. Charger les manquants
    with open(missing_file, "r", encoding="utf-8") as f:
        manquants = json.load(f)

    print(f"Stations avant fusion : {len(data)}")

    # 3. Ajouter les manquants à la base (sans écraser les existants)
    for nom, contenu in manquants.items():
        if nom not in data:
            data[nom] = contenu

    # 4. Sauvegarder la base mise à jour
    with open(data_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    print(f"Fusion terminée. Stations après fusion : {len(data)}")


fusionner_manquants()
