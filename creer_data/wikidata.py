import json
import requests
from datetime import datetime

CURRENT_DIRECTORY = "creer_data"


INPUT_FILE = f"{CURRENT_DIRECTORY}/stations_base.json"
OUTPUT_FILE = f"{CURRENT_DIRECTORY}/stations_enrichies.json"


def calcul_siecle(annee):
    if not annee:
        return None

    annee = int(annee)
    siecle = (annee - 1) // 100 + 1

    suffixes = {
        1: "Ier",
        2: "IIe",
        3: "IIIe",
        4: "IVe",
        5: "Ve",
        6: "VIe",
        7: "VIIe",
        8: "VIIIe",
        9: "IXe",
        10: "Xe",
        11: "XIe",
        12: "XIIe",
        13: "XIIIe",
        14: "XIVe",
        15: "XVe",
        16: "XVIe",
        17: "XVIIe",
        18: "XVIIIe",
        19: "XIXe",
        20: "XXe",
        21: "XXIe",
    }

    return suffixes.get(siecle)


import requests
import traceback


def recherche_wikidata(nom):

    url = "https://www.wikidata.org/w/api.php"

    params = {
        "action": "wbsearchentities",
        "search": nom,
        "language": "fr",
        "format": "json",
    }

    headers = {"User-Agent": "MetroParisBot/1.0"}

    print("\n" + "=" * 80)
    print(f"RECHERCHE : {nom}")
    print("=" * 80)

    try:
        r = requests.get(url, params=params, headers=headers, timeout=15)

        print(f"Status code : {r.status_code}")
        print(f"URL appelée : {r.url}")
        print(f"Content-Type : {r.headers.get('Content-Type')}")

        # Affiche le début de la réponse
        print("\nDébut réponse :")
        print(r.text[:500])

        r.raise_for_status()

        try:
            data = r.json()

        except Exception as e:
            print("\nERREUR JSON")
            print(e)

            print("\nContenu complet reçu :")
            print(r.text[:2000])

            return None

        if "search" not in data:
            print("\nChamp 'search' absent")
            print(data)

            return None

        if len(data["search"]) == 0:
            print("\nAucun résultat trouvé")

            return None

        print("\nRésultats trouvés :")
        print(f"Nombre : {len(data['search'])}")

        premier = data["search"][0]

        print("\nPremier résultat :")
        print(f"ID : {premier.get('id')}")
        print(f"Label : {premier.get('label')}")
        print(f"Description : {premier.get('description')}")

        return premier["id"]

    except requests.exceptions.Timeout:
        print("\nTIMEOUT")

        return None

    except requests.exceptions.ConnectionError:
        print("\nERREUR DE CONNEXION")

        return None

    except requests.exceptions.HTTPError as e:
        print("\nERREUR HTTP")

        print(e)

        try:
            print(r.text[:2000])
        except:
            pass

        return None

    except Exception as e:
        print("\nERREUR INATTENDUE")

        print(type(e))
        print(e)

        traceback.print_exc()

        return None


import requests
import traceback


def get_infos_wikidata(qid):

    query = f"""
    SELECT ?itemLabel ?itemDescription ?birth ?occupationLabel WHERE {{
      VALUES ?item {{ wd:{qid} }}

      OPTIONAL {{ ?item wdt:P569 ?birth . }}
      OPTIONAL {{ ?item wdt:P106 ?occupation . }}

      SERVICE wikibase:label {{
        bd:serviceParam wikibase:language "fr,en".
      }}
    }}
    LIMIT 1
    """

    url = "https://query.wikidata.org/sparql"

    headers = {"User-Agent": "MetroParisBot/1.0"}

    print("\n" + "=" * 80)
    print(f"REQUÊTE SPARQL POUR {qid}")
    print("=" * 80)

    print("Query :")
    print(query)

    try:
        r = requests.get(
            url, params={"query": query, "format": "json"}, headers=headers, timeout=30
        )

        print(f"Status code : {r.status_code}")
        print(f"Content-Type : {r.headers.get('Content-Type')}")
        print(f"URL finale : {r.url}")

        print("\nDébut de réponse :")
        print(r.text[:500])

        if r.status_code != 200:
            print(f"\nERREUR HTTP {r.status_code}")

            try:
                print(r.text[:2000])
            except:
                pass

            return None

        try:
            data = r.json()

        except Exception as e:
            print("\nERREUR DE PARSING JSON")
            print(e)

            with open(f"debug_wikidata_{qid}.html", "w", encoding="utf-8") as f:
                f.write(r.text)

            print(f"Réponse sauvegardée dans debug_wikidata_{qid}.html")

            return None

        print("\nClés JSON reçues :")
        print(data.keys())

        if "results" not in data:
            print("\nLa clé 'results' est absente")
            print(data)

            return None

        results = data["results"]["bindings"]

        print(f"\nNombre de résultats : {len(results)}")

        if not results:
            print("Aucun résultat")

            return None

        result = results[0]

        print("\nPremier résultat brut :")
        print(result)

        description = result.get("itemDescription", {}).get("value")

        occupation = result.get("occupationLabel", {}).get("value")

        naissance = None
        siecle = None

        if "birth" in result:
            naissance = result["birth"]["value"][:4]

            try:
                siecle = calcul_siecle(int(naissance))
            except Exception as e:
                print("Erreur calcul siècle :", e)

        enrichissement = {
            "description_wikidata": description,
            "occupation": occupation,
            "annee_naissance": naissance,
            "siecle": siecle,
        }

        print("\nInformations extraites :")
        print(enrichissement)

        return enrichissement

    except requests.exceptions.Timeout:
        print("\nTIMEOUT")
        return None

    except requests.exceptions.ConnectionError:
        print("\nERREUR DE CONNEXION")
        return None

    except Exception as e:
        print("\nERREUR INATTENDUE")
        print(type(e))
        print(e)

        traceback.print_exc()

        return None


with open(INPUT_FILE, "r", encoding="utf-8") as f:
    stations = json.load(f)

compteur = 0

for nom_station, infos in stations.items():
    qid = recherche_wikidata(nom_station)

    if not qid:
        continue

    wikidata = get_infos_wikidata(qid)

    if not wikidata:
        continue

    occupation = wikidata.get("occupation")

    if occupation:
        infos["theme"] = "Personne"
        infos["sous_theme"] = occupation
        infos["siecle"] = wikidata["siecle"]
        infos["description"] = wikidata["description_wikidata"]

        compteur += 1
        print(f"✓ {nom_station}")

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(stations, f, ensure_ascii=False, indent=4)

print()
print(f"{compteur} stations enrichies")
