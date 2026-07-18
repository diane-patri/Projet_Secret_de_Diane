# -*- coding: utf-8 -*-
"""Enrichissement batch Wikipedia des stations de metro, version 2."""

import html, json, re, time, unicodedata
from pathlib import Path
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# CONFIGURATION
FICHIER_ENTREE = "export_arrets_ratp.json"
FICHIER_SORTIE = "stations_enrichies_batch_v2.json"
FICHIER_CACHE = "cache_wikipedia_batch_v2.json"
TAILLE_LOT = 40
DELAI_REQUETES = 0.01
LIMITE_STATIONS = None
STATION_UNIQUE = None
RECOMMENCER = True
DEBUG = False
RETENTER_INCOMPLETS = True

API = "https://fr.wikipedia.org/w/api.php"
UA = "MetroParisBatchProject/2.1 (educational project)"


def norm(value):
    value = unicodedata.normalize("NFD", str(value or ""))
    value = "".join(c for c in value if unicodedata.category(c) != "Mn").lower()
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def clean(value):
    if value is None:
        return None
    value = html.unescape(str(value)).replace("\xa0", " ")
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip() or None


def short(text, count=3, limit=1000):
    text = clean(text)
    if not text:
        return None
    output = []
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        if output and len(" ".join(output + [sentence])) > limit:
            break
        output.append(sentence)
        if len(output) >= count:
            break
    return " ".join(output)


def chunks(values, size):
    for start in range(0, len(values), size):
        yield values[start : start + size]


def read_json(path, default=None):
    path = Path(path)
    if not path.exists() and default is not None:
        return default
    with path.open(encoding="utf-8-sig") as file:
        return json.load(file)


def save_json(path, data):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(data, ensure_ascii=False, indent=4) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def station_names(data):
    names = []
    if isinstance(data, dict):
        names.extend(data.keys())
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, str):
                names.append(item)
            elif isinstance(item, dict):
                mode = str(item.get("mode") or "").casefold()
                if mode and mode not in {"metro", "métro"}:
                    continue
                name = (
                    item.get("stop_name")
                    or item.get("station")
                    or item.get("nom_station")
                )
                if name:
                    names.append(name)
    unique = {}
    for name in names:
        if str(name).strip():
            unique.setdefault(norm(name), str(name).strip())
    return sorted(unique.values(), key=str.casefold)


def make_session():
    session = requests.Session()
    retry = Retry(
        total=5,
        connect=5,
        read=5,
        status=5,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=frozenset(["GET"]),
        respect_retry_after_header=True,
    )
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.headers.update(
        {"User-Agent": UA, "Accept": "application/json", "Accept-Language": "fr"}
    )
    return session


SESSION = make_session()
CACHE = (
    {"pages": {}, "search": {}}
    if RECOMMENCER
    else read_json(FICHIER_CACHE, {"pages": {}, "search": {}})
)
CACHE.setdefault("pages", {})
CACHE.setdefault("search", {})


def api(params):
    parameters = dict(params, format="json", formatversion=2, utf8=1)
    if DEBUG:
        print("[DEBUG]", parameters)
    response = SESSION.get(API, params=parameters, timeout=45)
    response.raise_for_status()
    data = response.json()
    if "error" in data:
        raise RuntimeError(data["error"])
    if DELAI_REQUETES:
        time.sleep(DELAI_REQUETES)
    return data


def revision_text(page):
    revisions = page.get("revisions") or []
    if not revisions:
        return ""
    return ((revisions[0].get("slots") or {}).get("main") or {}).get("content") or ""


def batch_pages(titles):
    titles = list(dict.fromkeys(title for title in titles if title))
    missing = [title for title in titles if title not in CACHE["pages"]]
    for lot in chunks(missing, TAILLE_LOT):
        data = api(
            {
                "action": "query",
                "prop": "extracts|categories|info|revisions",
                "titles": "|".join(lot),
                "exintro": 1,
                "explaintext": 1,
                "cllimit": "max",
                "inprop": "url",
                "rvprop": "content",
                "rvslots": "main",
                "redirects": 1,
            }
        )
        query = data.get("query", {})
        normalized = {x.get("from"): x.get("to") for x in query.get("normalized", [])}
        redirects = {x.get("from"): x.get("to") for x in query.get("redirects", [])}
        pages = {}
        for page in query.get("pages", []):
            pages[page.get("title")] = {
                "titre": page.get("title"),
                "missing": bool(page.get("missing")),
                "url": page.get("fullurl"),
                "resume": clean(page.get("extract")),
                "wikitext": revision_text(page),
                "categories": [
                    c.get("title", "").replace("Catégorie:", "")
                    for c in page.get("categories", [])
                ],
            }
        for requested in lot:
            normalized_title = normalized.get(requested, requested)
            final = redirects.get(normalized_title, normalized_title)
            CACHE["pages"][requested] = pages.get(
                final,
                {
                    "titre": final,
                    "missing": True,
                    "url": None,
                    "resume": None,
                    "wikitext": "",
                    "categories": [],
                },
            )
    return {title: CACHE["pages"].get(title) for title in titles}


def search_station(name):
    cache_key = "station::" + name
    if cache_key in CACHE["search"]:
        return CACHE["search"][cache_key]
    data = api(
        {
            "action": "query",
            "list": "search",
            "srsearch": f'"{name}" "métro de Paris"',
            "srlimit": 5,
        }
    )
    candidates = []
    for item in data.get("query", {}).get("search", []):
        title = item.get("title", "")
        score = 150 if "metro de paris" in norm(title) else 0
        score += 50 if norm(title).startswith(norm(name)) else 0
        candidates.append((score, title))
    title = max(candidates)[1] if candidates and max(candidates)[0] >= 50 else None
    CACHE["search"][cache_key] = title
    return title


def resolve_station_pages(names):
    direct = {name: f"{name} (métro de Paris)" for name in names}
    pages = batch_pages(list(direct.values()))
    mapping = {}
    failures = []
    for name, title in direct.items():
        if pages.get(title) and not pages[title]["missing"]:
            mapping[name] = title
        else:
            failures.append(name)
    print(f"Titres directs : {len(mapping)}/{len(names)}")
    for name in failures:
        title = search_station(name)
        if title:
            mapping[name] = title
    batch_pages(list(mapping.values()))
    return mapping


def origin_section(wikitext):
    if not wikitext:
        return None
    match = re.search(
        r"^==+\s*(Origine du nom|Toponymie|Dénomination|Nom)\s*==+\s*$",
        wikitext,
        re.I | re.M,
    )
    if not match:
        return None
    start = match.end()
    following = re.search(r"^==+\s*[^=].*?==+\s*$", wikitext[start:], re.M)
    return (
        wikitext[start : start + following.start()].strip()
        if following
        else wikitext[start:].strip()
    )


def wiki_links(text):
    links = []
    seen = set()
    for target, label in re.findall(
        r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|([^\]]+))?\]\]", text or ""
    ):
        if target.startswith(("Fichier:", "Catégorie:", "Modèle:")):
            continue
        key = norm(target)
        if key not in seen:
            seen.add(key)
            links.append((target.strip(), clean(label or target)))
    return links


def plain_wiki(text):
    text = re.sub(
        r"<ref\b[^>/]*>.*?</ref>|<ref\b[^>]*/>", " ", text or "", flags=re.I | re.S
    )
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.S)
    for _ in range(5):
        text = re.sub(r"\{\{[^{}]*\}\}", " ", text)
    text = re.sub(r"\[\[([^\]|]+)\|([^\]]+)\]\]", r"\2", text)
    text = re.sub(r"\[\[([^\]]+)\]\]", r"\1", text)
    return clean(text.replace("'''", "").replace("''", ""))


NAME_PATTERNS = [
    "doit son nom",
    "tient son nom",
    "tire son nom",
    "porte le nom",
    "rend hommage",
    "en hommage",
    "nommee d apres",
    "nomme d apres",
    "fait reference",
    "baptisee",
    "baptise",
]


def naming_sentence_raw(text):
    for sentence in re.split(r"(?<=[.!?])\s+", plain_wiki(text) or ""):
        if any(pattern in norm(sentence) for pattern in NAME_PATTERNS):
            return sentence
    return None


def explanation(text):
    plain = plain_wiki(text)
    sentences = re.split(r"(?<=[.!?])\s+", plain or "")
    for index, sentence in enumerate(sentences):
        if any(pattern in norm(sentence) for pattern in NAME_PATTERNS):
            result = sentence
            if index + 1 < len(sentences) and len(sentences[index + 1]) < 400:
                result += " " + sentences[index + 1]
            return clean(result)
    return short(plain, 2, 700)


def choose_origin(name, links, raw_context):
    full_context = norm(plain_wiki(raw_context))
    naming = norm(naming_sentence_raw(raw_context))
    station_name = norm(name)
    scored = []
    for position, (title, label) in enumerate(links):
        title_n = norm(title)
        label_n = norm(label)
        if any(
            x in title_n
            for x in [
                "metro de paris",
                "ratp",
                "arrondissement de paris",
                "ligne du metro",
            ]
        ):
            continue
        score = 0
        if title_n == station_name:
            score += 180
        if label_n == station_name:
            score += 180
        if station_name and station_name in title_n:
            score += 70
        if title_n and title_n in naming:
            score += 160
        if label_n and label_n in naming:
            score += 130
        if title_n and title_n in full_context:
            score += 20
        if position < 3:
            score += 10 - position
        scored.append((score, title))
    return max(scored)[1] if scored and max(scored)[0] >= 30 else name


PERSON_WORDS = [
    "personnalite",
    "ecrivain",
    "ecrivaine",
    "romancier",
    "romanciere",
    "poete",
    "dramaturge",
    "scientifique",
    "physicien",
    "chimiste",
    "mathematicien",
    "militaire",
    "general",
    "marechal",
    "amiral",
    "homme politique",
    "femme politique",
    "ministre",
    "depute",
    "senateur",
    "maire",
    "peintre",
    "sculpteur",
    "artiste",
    "compositeur",
    "musicien",
    "medecin",
    "ingenieur",
    "inventeur",
    "architecte",
    "resistant",
    "resistante",
    "acteur",
    "actrice",
    "philosophe",
    "explorateur",
]

SUBTHEMES = [
    (
        "Résistant",
        [
            "resistant",
            "resistante",
            "resistance francaise",
            "compagnon de la liberation",
        ],
    ),
    (
        "Auteur",
        [
            "ecrivain",
            "ecrivaine",
            "romancier",
            "romanciere",
            "poete",
            "dramaturge",
            "essayiste",
        ],
    ),
    (
        "Scientifique",
        [
            "scientifique",
            "physicien",
            "chimiste",
            "mathematicien",
            "biologiste",
            "astronome",
        ],
    ),
    ("Médecin", ["medecin", "chirurgien", "pharmacien"]),
    (
        "Militaire",
        ["militaire", "general", "marechal", "amiral", "officier", "colonel"],
    ),
    (
        "Personnalité politique",
        [
            "homme politique",
            "femme politique",
            "ministre",
            "president",
            "depute",
            "senateur",
            "maire",
        ],
    ),
    (
        "Artiste",
        ["peintre", "sculpteur", "dessinateur", "artiste", "acteur", "actrice"],
    ),
    ("Musicien", ["compositeur", "musicien", "chanteur", "chanteuse"]),
    ("Ingénieur ou inventeur", ["ingenieur", "inventeur", "architecte"]),
    ("Religieux", ["saint", "sainte", "eveque", "pretre", "abbe", "cardinal"]),
]


def is_person(resume, categories):
    corpus = norm((resume or "") + " " + " ".join(categories or []))
    category_signals = [
        "naissance en ",
        "deces en ",
        "personnalite ",
        "personne du ",
        "homme du ",
        "femme du ",
        "personnalite politique",
    ]
    date_signal = bool(re.search(r"\b(?:ne|nee)\b.{0,140}\b\d{3,4}\b", corpus))
    death_signal = bool(
        re.search(r"\b(?:mort|morte|decede|decedee)\b.{0,140}\b\d{3,4}\b", corpus)
    )
    profession_signal = any(word in corpus for word in PERSON_WORDS)
    return (
        profession_signal
        or date_signal
        or death_signal
        or any(x in corpus for x in category_signals)
    )


def classify(resume, categories):
    corpus = norm((resume or "") + " " + " ".join(categories or []))
    if is_person(resume, categories):
        for subtype, words in SUBTHEMES:
            if any(word in corpus for word in words):
                return "Personne", subtype
        return "Personne", "Personnalité"
    if any(x in corpus for x in ["bataille", "combat", "offensive", "siege de"]):
        return "Événement historique", "Bataille"
    if any(x in corpus for x in ["revolution", "insurrection", "soulevement"]):
        return "Événement historique", "Révolution ou insurrection"
    if "capitale" in corpus:
        return "Lieu géographique", "Capitale"
    if any(x in corpus for x in ["ville", "commune", "village"]):
        return "Lieu géographique", "Ville ou commune"
    if any(x in corpus for x in ["quartier de paris", "quartier administratif"]):
        return "Lieu géographique", "Quartier"
    if "musee" in corpus:
        return "Monument ou institution", "Musée"
    if any(
        x in corpus for x in ["monument", "palais", "eglise", "cathedrale", "chateau"]
    ):
        return "Monument ou institution", "Monument"
    return "Autre", "À vérifier"


MONTHS = "janvier|fevrier|mars|avril|mai|juin|juillet|aout|septembre|octobre|novembre|decembre"


def years(text):
    if not text:
        return None, None
    normalized = norm(text)
    born = re.search(
        rf"\b(?:ne|nee)\b.{0, 100}?\b(?:{MONTHS})?\s*(\d{{3,4}})\b", normalized
    )
    died = re.search(
        rf"\b(?:mort|morte|decede|decedee)\b.{0, 100}?\b(?:{MONTHS})?\s*(\d{{3,4}})\b",
        normalized,
    )
    if born or died:
        return (
            int(born.group(1)) if born else None,
            int(died.group(1)) if died else None,
        )
    parenthetical = re.search(r"\((\d{3,4})\s*[–-]\s*(\d{3,4})\)", text)
    if parenthetical:
        return int(parenthetical.group(1)), int(parenthetical.group(2))
    found = re.findall(r"\b(1[0-9]{3}|20[0-9]{2})\b", text[:700])
    return (int(found[0]), int(found[1])) if len(found) >= 2 else (None, None)


def roman(number):
    values = [
        (1000, "M"),
        (900, "CM"),
        (500, "D"),
        (400, "CD"),
        (100, "C"),
        (90, "XC"),
        (50, "L"),
        (40, "XL"),
        (10, "X"),
        (9, "IX"),
        (5, "V"),
        (4, "IV"),
        (1, "I"),
    ]
    output = ""
    for value, symbol in values:
        while number >= value:
            output += symbol
            number -= value
    return output


def centuries(birth, death):
    if not birth and not death:
        return []
    start, end = birth or death, death or birth
    return [
        f"{roman(i)}e siècle"
        for i in range((start - 1) // 100 + 1, (end - 1) // 100 + 2)
    ]


def complete(result):
    if not isinstance(result, dict):
        return False
    if not RETENTER_INCOMPLETS:
        return bool(result.get("station"))
    return bool(
        result.get("source_station")
        and result.get("theme") not in {None, "À vérifier"}
        and result.get("informations")
    )


def analyze_batch(names, mapping):
    prepared, origins = {}, []
    for name in names:
        station_page = CACHE["pages"].get(mapping.get(name))
        result = {
            "station": name,
            "theme": None,
            "sous_theme": None,
            "pourquoi_ce_nom": None,
            "informations": None,
            "personne": None,
            "source_station": None,
        }
        if not station_page or station_page["missing"]:
            prepared[name] = (result, None)
            continue
        result["source_station"] = {
            "titre": station_page["titre"],
            "url": station_page["url"],
            "resume": short(station_page["resume"], 3, 800),
        }
        raw = origin_section(station_page["wikitext"]) or station_page["wikitext"]
        result["pourquoi_ce_nom"] = explanation(raw)
        origin = choose_origin(name, wiki_links(raw), raw)
        origins.append(origin)
        prepared[name] = (result, origin)

    batch_pages(origins)
    output = []
    for name in names:
        result, origin = prepared[name]
        page = CACHE["pages"].get(origin) if origin else None
        if not page or page["missing"]:
            result["theme"] = result["sous_theme"] = "À vérifier"
            output.append(result)
            continue
        result["informations"] = short(page["resume"], 3, 1000)
        result["theme"], result["sous_theme"] = classify(
            page["resume"], page["categories"]
        )
        if result["theme"] == "Personne":
            birth, death = years(page["resume"])
            result["personne"] = {
                "nom": page["titre"],
                "annee_naissance": birth,
                "annee_deces": death,
                "siecles_vecus": centuries(birth, death),
            }
        output.append(result)
    return output


def main():
    if not 1 <= TAILLE_LOT <= 50:
        raise ValueError("TAILLE_LOT doit etre entre 1 et 50")
    names = station_names(read_json(FICHIER_ENTREE))
    if STATION_UNIQUE:
        names = [name for name in names if norm(name) == norm(STATION_UNIQUE)]
    if LIMITE_STATIONS is not None:
        names = names[:LIMITE_STATIONS]
    previous = (
        {}
        if RECOMMENCER
        else {
            norm(item.get("station")): item
            for item in read_json(FICHIER_SORTIE, [])
            if isinstance(item, dict)
        }
    )
    todo = [name for name in names if not complete(previous.get(norm(name)))]
    print(
        f"Stations : {len(names)}, completes : {len(names) - len(todo)}, a traiter : {len(todo)}"
    )
    if not todo:
        return
    mapping = resolve_station_pages(todo)
    save_json(FICHIER_CACHE, CACHE)
    lots = list(chunks(todo, TAILLE_LOT))
    try:
        for index, lot in enumerate(lots, 1):
            print(f"Lot {index}/{len(lots)} : {len(lot)} stations")
            for result in analyze_batch(lot, mapping):
                previous[norm(result["station"])] = result
                print(
                    f"  {result['station']} : {result['theme']} / {result['sous_theme']}"
                )
            save_json(
                FICHIER_SORTIE,
                sorted(previous.values(), key=lambda x: norm(x.get("station"))),
            )
            save_json(FICHIER_CACHE, CACHE)
    finally:
        save_json(
            FICHIER_SORTIE,
            sorted(previous.values(), key=lambda x: norm(x.get("station"))),
        )
        save_json(FICHIER_CACHE, CACHE)
    print("Termine :", Path(FICHIER_SORTIE).resolve())


if __name__ == "__main__":
    main()
