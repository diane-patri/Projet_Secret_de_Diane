import json

CURRENT_DIRECTORY = "creer_data"

INPUT_FILE = f"{CURRENT_DIRECTORY}/export_arrets_ratp.json"
OUTPUT_FILE = f"{CURRENT_DIRECTORY}/stations_base.json"

with open(INPUT_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

stations = {}

for row in data:
    if row.get("mode") != "Metro":
        continue

    nom_station = row["stop_name"].strip()
    ligne = str(row["route_long_name"]).strip()

    if nom_station not in stations:
        stations[nom_station] = {
            "lignes": [],
            "commune": row.get("nom_commune"),
            "code_insee": row.get("code_insee"),
            "latitude": float(row["stop_lat"]),
            "longitude": float(row["stop_lon"]),
            "theme": None,
            "sous_theme": None,
            "siecle": None,
            "description": None,
        }

    if ligne not in stations[nom_station]["lignes"]:
        stations[nom_station]["lignes"].append(ligne)

# tri des lignes
for station in stations.values():
    station["lignes"].sort()

# tri alphabétique des stations
stations = dict(sorted(stations.items()))

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(stations, f, ensure_ascii=False, indent=4)

print(f"{len(stations)} stations trouvées")
print(f"Fichier créé : {OUTPUT_FILE}")
