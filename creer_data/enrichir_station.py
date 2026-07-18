# -*- coding: utf-8 -*-
"""Reglez les options ci-dessous puis lancez : python enrichir_stations_rapide.py"""

import json, time, traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import station_wikipedia as analyser

# CONFIGURATION
FICHIER_ENTREE = "export_arrets_ratp.json"
FICHIER_SORTIE = "stations_enrichies.json"
NOMBRE_WORKERS = 4  # 3 ou 4 conseille
DELAI_PAR_STATION = 0.0  # mettre 0.2 en cas d'erreurs 429
RECOMMENCER_DEPUIS_ZERO = False
AFFICHER_DEBUG = False
LIMITE_STATIONS = 98  # mettre 10 pour tester, puis None
STATION_UNIQUE = None  # exemple "Victor Hugo", sinon None
RETENTER_INCOMPLETS = False
SAUVEGARDE_CHAQUE_N = 8


def load(p):
    with Path(p).open(encoding="utf-8-sig") as f:
        return json.load(f)


def save(p, d):
    p = Path(p)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False, indent=4) + "\n", encoding="utf-8")
    tmp.replace(p)


def key(s):
    return " ".join(str(s or "").casefold().split())


def names(data):
    out = []
    if isinstance(data, dict):
        out = list(data)
    elif isinstance(data, list):
        for x in data:
            if isinstance(x, str):
                out.append(x)
            elif isinstance(x, dict):
                mode = str(x.get("mode") or "").casefold()
                if mode and mode not in {"metro", "métro"}:
                    continue
                n = x.get("stop_name") or x.get("station") or x.get("nom_station")
                if n:
                    out.append(n)
    unique = {}
    [unique.setdefault(key(n), str(n).strip()) for n in out if str(n).strip()]
    return sorted(unique.values(), key=str.casefold)


def complete(x):
    if not RETENTER_INCOMPLETS:
        return bool(x)
    return bool(
        x
        and x.get("source_station")
        and x.get("theme") not in {None, "À vérifier"}
        and x.get("informations")
    )


def work(n):
    if DELAI_PAR_STATION:
        time.sleep(DELAI_PAR_STATION)
    try:
        return n, analyser.analyser_station(n), None
    except Exception as e:
        return (
            n,
            {
                "station": n,
                "theme": None,
                "sous_theme": None,
                "pourquoi_ce_nom": None,
                "informations": None,
                "personne": None,
                "source_station": None,
            },
            f"{e}\n{traceback.format_exc()}",
        )


def main():
    analyser.DEBUG = AFFICHER_DEBUG
    ns = names(load(FICHIER_ENTREE))
    if STATION_UNIQUE:
        ns = [n for n in ns if key(n) == key(STATION_UNIQUE)]
    if LIMITE_STATIONS is not None:
        ns = ns[:LIMITE_STATIONS]
    p = Path(FICHIER_SORTIE)
    old = (
        {}
        if RECOMMENCER_DEPUIS_ZERO or not p.exists()
        else {key(x.get("station")): x for x in load(p) if isinstance(x, dict)}
    )
    todo = [n for n in ns if not complete(old.get(key(n)))]
    print(
        f"Stations: {len(ns)}, deja completes: {len(ns) - len(todo)}, a traiter: {len(todo)}, workers: {NOMBRE_WORKERS}"
    )
    done = errors = 0
    try:
        with ThreadPoolExecutor(max_workers=NOMBRE_WORKERS) as ex:
            futures = {ex.submit(work, n): n for n in todo}
            for i, f in enumerate(as_completed(futures), 1):
                n, r, e = f.result()
                old[key(n)] = r
                done += 1
                if e:
                    errors += 1
                    print(f"[{i}/{len(todo)}] ERREUR {n}: {e}")
                else:
                    print(
                        f"[{i}/{len(todo)}] OK {n}: {r.get('theme')} / {r.get('sous_theme')}"
                    )
                if done % SAUVEGARDE_CHAQUE_N == 0:
                    save(p, sorted(old.values(), key=lambda x: key(x.get("station"))))
    except KeyboardInterrupt:
        print("Interruption, sauvegarde...")
    finally:
        save(p, sorted(old.values(), key=lambda x: key(x.get("station"))))
    print(f"Termine. Erreurs: {errors}. Fichier: {p.resolve()}")


if __name__ == "__main__":
    main()
