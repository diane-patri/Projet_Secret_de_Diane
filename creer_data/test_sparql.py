import requests

qid = "Q535"

query = f"""
SELECT ?itemLabel ?itemDescription WHERE {{
    VALUES ?item {{ wd:{qid} }}

    SERVICE wikibase:label {{
        bd:serviceParam wikibase:language "fr,en".
    }}
}}
"""

url = "https://query.wikidata.org/sparql"

headers = {"User-Agent": "MetroParisBot/1.0"}

r = requests.get(
    url, params={"query": query, "format": "json"}, headers=headers, timeout=30
)

print("STATUS :", r.status_code)

print("\nREPONSE :")
print(r.text[:1000])

try:
    data = r.json()
    print("\nJSON OK")
except Exception as e:
    print("\nErreur JSON :", e)
