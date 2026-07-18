# -*- coding: utf-8 -*-
"""Analyse Wikipedia d'une station. Compatible avec plusieurs threads."""

import html, re, threading, time, unicodedata
from html.parser import HTMLParser
from urllib.parse import unquote
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

API_URL = "https://fr.wikipedia.org/w/api.php"
USER_AGENT = "MetroParisProject/1.0 (projet pedagogique)"
TIMEOUT = 30
DEBUG = False
_LOCAL = threading.local()
_CACHE = {}
_CACHE_LOCK = threading.Lock()


def norm(s):
    s = unicodedata.normalize("NFD", str(s or ""))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn").lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def clean(s):
    if s is None:
        return None
    s = html.unescape(str(s)).replace("\xa0", " ")
    return re.sub(r"\s+", " ", re.sub(r"\[\s*\d+\s*\]", "", s)).strip() or None


def sentences(s, n=3, maxlen=1000):
    s = clean(s)
    if not s:
        return None
    out = []
    for p in re.split(r"(?<=[.!?])\s+", s):
        if out and len(" ".join(out + [p])) > maxlen:
            break
        out.append(p)
        if len(out) >= n:
            break
    return " ".join(out)


def session():
    if not hasattr(_LOCAL, "s"):
        s = requests.Session()
        r = Retry(
            total=5,
            connect=5,
            read=5,
            status=5,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=frozenset(["GET"]),
            respect_retry_after_header=True,
        )
        a = HTTPAdapter(max_retries=r)
        s.mount("https://", a)
        s.headers.update(
            {
                "User-Agent": USER_AGENT,
                "Accept": "application/json",
                "Accept-Language": "fr",
            }
        )
        _LOCAL.s = s
    return _LOCAL.s


def api(params):
    key = tuple(sorted((str(k), str(v)) for k, v in params.items()))
    with _CACHE_LOCK:
        if key in _CACHE:
            return _CACHE[key]
    p = dict(params, format="json", formatversion=2, utf8=1)
    if DEBUG:
        print("[DEBUG]", p)
    r = session().get(API_URL, params=p, timeout=TIMEOUT)
    r.raise_for_status()
    data = r.json()
    if "error" in data:
        raise RuntimeError(data["error"])
    with _CACHE_LOCK:
        _CACHE[key] = data
    return data


def search(q, n=10):
    return (
        api(
            {
                "action": "query",
                "list": "search",
                "srsearch": q,
                "srnamespace": 0,
                "srlimit": n,
            }
        )
        .get("query", {})
        .get("search", [])
    )


def station_title(name):
    cand = {}
    for q in [f'"{name}" "métro de Paris"', f"{name} métro Paris"]:
        for x in search(q):
            t = x.get("title", "")
            z = norm(t)
            sn = norm(re.sub("<[^>]+>", " ", x.get("snippet", "")))
            n = norm(name)
            score = 0
            if z.startswith(n):
                score += 40
            if "metro de paris" in z:
                score += 150
            if "station du metro de paris" in sn:
                score += 80
            if "tramway" in z:
                score -= 100
            cand[t] = max(score, cand.get(t, -999))
    return max(cand, key=cand.get) if cand and max(cand.values()) >= 50 else None


def page(title, intro=False):
    p = {
        "action": "query",
        "prop": "extracts|categories|info",
        "titles": title,
        "explaintext": 1,
        "redirects": 1,
        "cllimit": "max",
        "inprop": "url",
    }
    if intro:
        p["exintro"] = 1
    pages = api(p).get("query", {}).get("pages", [])
    if not pages or pages[0].get("missing"):
        return None
    x = pages[0]
    return {
        "titre": x.get("title"),
        "texte": clean(x.get("extract")),
        "url": x.get("fullurl"),
        "categories": [
            c.get("title", "").replace("Catégorie:", "")
            for c in x.get("categories", [])
        ],
    }


class Parser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.txt = []
        self.links = []
        self.href = None
        self.title = None
        self.label = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag in {"script", "style", "sup", "table"}:
            self.skip += 1
        elif not self.skip and tag == "a" and d.get("href", "").startswith("/wiki/"):
            self.href = d["href"]
            self.title = d.get("title")
            self.label = []

    def handle_endtag(self, tag):
        if tag in {"script", "style", "sup", "table"} and self.skip:
            self.skip -= 1
        elif not self.skip and tag == "a" and self.href:
            t = self.title or unquote(self.href[6:]).replace("_", " ")
            if not t.startswith(
                ("Aide:", "Fichier:", "Catégorie:", "Wikipédia:", "Modèle:")
            ):
                self.links.append({"titre": t, "libelle": clean(" ".join(self.label))})
            self.href = None

    def handle_data(self, d):
        if not self.skip:
            self.txt.append(d)
            self.label.append(d) if self.href else None


def origin_section(title):
    secs = (
        api({"action": "parse", "page": title, "prop": "sections", "redirects": 1})
        .get("parse", {})
        .get("sections", [])
    )
    scored = []
    for s in secs:
        z = norm(s.get("line"))
        score = (
            100
            if "origine du nom" in z
            else 90
            if "toponymie" in z
            else 80
            if "denomination" in z
            else 0
        )
        if score:
            scored.append((score, s.get("index")))
    if not scored:
        return None
    idx = max(scored)[1]
    raw = (
        api(
            {
                "action": "parse",
                "page": title,
                "section": idx,
                "prop": "text",
                "redirects": 1,
            }
        )
        .get("parse", {})
        .get("text", "")
    )
    p = Parser()
    p.feed(raw)
    return {"texte": clean(" ".join(p.txt)), "liens": p.links}


def explanation(text):
    pats = [
        "doit son nom",
        "tient son nom",
        "tire son nom",
        "porte le nom",
        "rend hommage",
        "en hommage",
        "nommee d apres",
        "fait reference",
    ]
    ps = re.split(r"(?<=[.!?])\s+", text or "")
    for i, p in enumerate(ps):
        if any(x in norm(p) for x in pats):
            return clean(
                p
                + (" " + ps[i + 1] if i + 1 < len(ps) and len(ps[i + 1]) < 400 else "")
            )
    return sentences(text, 2, 700)


def origin_page(name, text, links):
    n = norm(name)
    context = norm(text)
    ranked = []
    for l in links:
        t = norm(l.get("titre"))
        lab = norm(l.get("libelle"))
        score = 0
        if any(x in t for x in ["metro de paris", "ratp", "arrondissement de paris"]):
            continue
        if t == n:
            score += 150
        if lab == n:
            score += 150
        if t and t in context:
            score += 30
        ranked.append((score, l.get("titre")))
    for score, t in sorted(ranked, reverse=True):
        if score < 10:
            continue
        i = page(t, True)
        c = page(t)
        if i and c and i["texte"]:
            c["resume"] = i["texte"]
            return c
    for x in search(f'"{name}"'):
        t = x.get("title", "")
        z = norm(t)
        if z == n and "metro de paris" not in z:
            i = page(t, True)
            c = page(t)
            if i and c:
                c["resume"] = i["texte"]
                return c
    return None


def classify(resume, cats):
    c = norm((resume or "") + " " + " ".join(cats or []))
    people = [
        ("Résistant", ["resistant"]),
        ("Auteur", ["ecrivain", "romancier", "poete", "dramaturge"]),
        ("Scientifique", ["scientifique", "physicien", "chimiste", "mathematicien"]),
        ("Militaire", ["militaire", "general", "marechal"]),
        ("Personnalité politique", ["homme politique", "ministre", "president"]),
        ("Artiste", ["peintre", "sculpteur", "artiste"]),
        ("Musicien", ["compositeur", "musicien"]),
    ]
    human = any(
        x in c
        for x in [
            " ne le ",
            " nee le ",
            " mort le ",
            "personnalite",
            "ecrivain",
            "militaire",
            "artiste",
        ]
    )
    if human:
        for sub, keys in people:
            if any(k in c for k in keys):
                return "Personne", sub
        return "Personne", "Personnalité"
    if "bataille" in c:
        return "Événement historique", "Bataille"
    if "capitale" in c:
        return "Lieu géographique", "Capitale"
    if any(x in c for x in ["ville", "commune"]):
        return "Lieu géographique", "Ville ou commune"
    if "musee" in c:
        return "Monument ou institution", "Musée"
    if any(x in c for x in ["monument", "palais", "eglise", "cathedrale"]):
        return "Monument ou institution", "Monument"
    return "Autre", "À vérifier"


def years(text):
    m = re.search(r"\((\d{3,4})\s*[–-]\s*(\d{3,4})\)", text or "")
    if m:
        return int(m.group(1)), int(m.group(2))
    a = re.findall(r"\b(1[0-9]{3}|20[0-9]{2})\b", (text or "")[:600])
    return (int(a[0]), int(a[1])) if len(a) >= 2 else (None, None)


def roman(n):
    vals = [
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
    o = ""
    for v, s in vals:
        while n >= v:
            o += s
            n -= v
    return o


def centuries(a, b):
    if not a and not b:
        return []
    x, y = a or b, b or a
    return [
        f"{roman(i)}e siècle" for i in range((x - 1) // 100 + 1, (y - 1) // 100 + 2)
    ]


def analyser_station(name):
    out = {
        "station": name,
        "theme": None,
        "sous_theme": None,
        "pourquoi_ce_nom": None,
        "informations": None,
        "personne": None,
        "source_station": None,
    }
    title = station_title(name)
    if not title:
        return out
    full = page(title)
    intro = page(title, True)
    if not full:
        return out
    out["source_station"] = {
        "titre": full["titre"],
        "url": full["url"],
        "resume": sentences((intro or {}).get("texte"), 3, 800),
    }
    sec = origin_section(title)
    text = (sec or {}).get("texte") or full.get("texte")
    links = (sec or {}).get("liens", [])
    out["pourquoi_ce_nom"] = explanation(text)
    origin = origin_page(name, text, links)
    if not origin:
        out["theme"] = out["sous_theme"] = "À vérifier"
        return out
    out["informations"] = sentences(origin.get("resume"), 3, 1000)
    out["theme"], out["sous_theme"] = classify(
        origin.get("resume"), origin.get("categories")
    )
    if out["theme"] == "Personne":
        a, b = years(origin.get("resume"))
        out["personne"] = {
            "nom": origin["titre"],
            "annee_naissance": a,
            "annee_deces": b,
            "siecles_vecus": centuries(a, b),
        }
    return out
