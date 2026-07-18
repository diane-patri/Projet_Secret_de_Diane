import requests

nom = "Victor Hugo"

url = "https://www.wikidata.org/w/api.php"

params = {
    "action": "wbsearchentities",
    "search": nom,
    "language": "fr",
    "format": "json",
    "limit": 20,
}

headers = {"User-Agent": "MetroParisBot/1.0"}

r = requests.get(url, params=params, headers=headers, timeout=20)

data = r.json()

station_qid = None
origine_qid = None

mots_station = ["station", "métro", "metro", "tram", "gare"]

for result in data["search"]:
    qid = result["id"]

    description = (result.get("description") or "").lower()

    print(f"{qid} -> {description}")

    # candidat station
    if any(mot in description for mot in mots_station):
        if station_qid is None:
            station_qid = qid

        continue

    # candidat origine du nom
    if origine_qid is None:
        origine_qid = qid

print()
print("Station :", station_qid)
print("Origine :", origine_qid)
