import json


FICHIER_ENTREE = "stations_enrichies_batch_v2.json"
FICHIER_SORTIE = "stations_sans_sources.json"


# Chargement du fichier d'origine
with open(FICHIER_ENTREE, "r", encoding="utf-8-sig") as fichier:
    stations = json.load(fichier)


# Vérification de la structure du JSON
if not isinstance(stations, list):
    raise ValueError("Le fichier JSON doit contenir une liste de stations.")


# Suppression de source_station pour chaque station
for station in stations:
    if isinstance(station, dict):
        station.pop("source_station", None)


# Création du nouveau fichier JSON
with open(FICHIER_SORTIE, "w", encoding="utf-8") as fichier:
    json.dump(
        stations,
        fichier,
        ensure_ascii=False,
        indent=4,
    )


print(f"{len(stations)} stations traitées.")
print(f"Fichier créé : {FICHIER_SORTIE}")
