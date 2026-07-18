import ast
import json
import re
import unicodedata
from pathlib import Path


# ============================================================
# CONFIGURATION
# ============================================================

FICHIER_STATIONS = "creer_data/stations_base.json"
FICHIER_CATEGORIES = "sessions.py"
FICHIER_SORTIE = "stations_base_avec_categories.json"

NOM_VARIABLE_CATEGORIES = "SESSIONS_CATEGORIES"


# ============================================================
# MAPPING DES NOMS
# ============================================================

# Sens du mapping :
#
# "nom dans sessions.py" -> "nom dans stations_base.json"
#
# Une valeur None signifie que la station présente dans sessions.py
# n'a volontairement aucune correspondance dans stations_base.json.

MAPPING_NOMS_STATIONS = {
    "Austerlitz": "Gare d'Austerlitz",
    "Europe - Simone Veil": "Europe",
    "Gare Saint-Lazare": "Saint-Lazare",
    "Gaîté - Joséphine Baker": "Gaîté",
    "Jean Moulin": None,
    "Panthéon": None,
}


# ============================================================
# NORMALISATION DES NOMS
# ============================================================


def normaliser_nom(nom):
    """
    Normalise un nom afin de faciliter les correspondances.

    Exemples :
    - Alma - Marceau -> alma marceau
    - Louvre – Rivoli -> louvre rivoli
    - Musée -> musee
    - Gaîté -> gaite
    """

    if not nom:
        return ""

    nom = unicodedata.normalize(
        "NFD",
        str(nom),
    )

    nom = "".join(
        caractere for caractere in nom if unicodedata.category(caractere) != "Mn"
    )

    nom = nom.casefold()

    # Uniformisation des apostrophes
    nom = nom.replace("’", "'")
    nom = nom.replace("`", "'")

    # Transformation des tirets et apostrophes en espaces
    nom = re.sub(
        r"[-–—_'’]+",
        " ",
        nom,
    )

    # Suppression des autres signes
    nom = re.sub(
        r"[^a-z0-9]+",
        " ",
        nom,
    )

    # Suppression des espaces multiples
    nom = re.sub(
        r"\s+",
        " ",
        nom,
    )

    return nom.strip()


# ============================================================
# PRÉPARATION DU MAPPING
# ============================================================


def construire_mapping_normalise():
    """
    Normalise les clés du mapping.

    Le résultat conserve le nom cible tel qu'il doit apparaître
    dans stations_base.json.
    """

    mapping_normalise = {}

    for nom_sessions, nom_json in MAPPING_NOMS_STATIONS.items():
        cle = normaliser_nom(nom_sessions)
        mapping_normalise[cle] = nom_json

    return mapping_normalise


MAPPING_NORMALISE = construire_mapping_normalise()


def convertir_nom_sessions_vers_json(nom_sessions):
    """
    Convertit un nom présent dans sessions.py vers le nom correspondant
    dans stations_base.json.

    Si aucun mapping n'est défini, le nom original est utilisé.

    Si le mapping contient None, la station est volontairement ignorée.
    """

    nom_normalise = normaliser_nom(nom_sessions)

    if nom_normalise in MAPPING_NORMALISE:
        return MAPPING_NORMALISE[nom_normalise]

    return nom_sessions


# ============================================================
# LECTURE SÉCURISÉE DU FICHIER JSON
# ============================================================


def charger_json_avec_diagnostic(chemin):
    """
    Charge un fichier JSON et affiche précisément l'emplacement
    d'une éventuelle erreur de syntaxe.
    """

    chemin = Path(chemin)

    try:
        contenu = chemin.read_text(
            encoding="utf-8-sig",
        )

    except FileNotFoundError:
        raise FileNotFoundError(f"Fichier JSON introuvable : {chemin.resolve()}")

    try:
        return json.loads(contenu)

    except json.JSONDecodeError as erreur:
        lignes = contenu.splitlines()

        print("\n" + "=" * 70)
        print("ERREUR DANS LE FICHIER JSON")
        print("=" * 70)

        print(f"Fichier : {chemin.resolve()}")
        print(f"Message : {erreur.msg}")
        print(f"Ligne   : {erreur.lineno}")
        print(f"Colonne : {erreur.colno}")
        print(f"Position: {erreur.pos}")

        debut = max(
            0,
            erreur.lineno - 4,
        )

        fin = min(
            len(lignes),
            erreur.lineno + 3,
        )

        print("\nContexte de l'erreur :")

        for index in range(debut, fin):
            numero_ligne = index + 1

            if numero_ligne == erreur.lineno:
                marqueur = ">>>"
            else:
                marqueur = "   "

            print(f"{marqueur} {numero_ligne:5d} | {lignes[index]}")

            if numero_ligne == erreur.lineno:
                print(
                    " " * 12
                    + " "
                    * max(
                        0,
                        erreur.colno - 1,
                    )
                    + "^"
                )

        raise


# ============================================================
# LECTURE SÉCURISÉE DU FICHIER PYTHON
# ============================================================


def charger_categories_python(chemin):
    """
    Lit uniquement la variable SESSIONS_CATEGORIES.

    Le fichier Python n'est pas exécuté. Le dictionnaire est lu avec
    ast.literal_eval.
    """

    chemin = Path(chemin)

    if not chemin.exists():
        raise FileNotFoundError(f"Fichier Python introuvable : {chemin.resolve()}")

    contenu = chemin.read_text(
        encoding="utf-8-sig",
    )

    arbre = ast.parse(
        contenu,
        filename=str(chemin),
    )

    for noeud in arbre.body:
        # Cas :
        # SESSIONS_CATEGORIES = {...}

        if isinstance(noeud, ast.Assign):
            for cible in noeud.targets:
                if isinstance(cible, ast.Name) and cible.id == NOM_VARIABLE_CATEGORIES:
                    categories = ast.literal_eval(noeud.value)

                    if not isinstance(categories, dict):
                        raise ValueError(
                            f"{NOM_VARIABLE_CATEGORIES} doit être un dictionnaire."
                        )

                    return categories

        # Cas :
        # SESSIONS_CATEGORIES: dict = {...}

        if isinstance(noeud, ast.AnnAssign):
            cible = noeud.target

            if isinstance(cible, ast.Name) and cible.id == NOM_VARIABLE_CATEGORIES:
                categories = ast.literal_eval(noeud.value)

                if not isinstance(categories, dict):
                    raise ValueError(
                        f"{NOM_VARIABLE_CATEGORIES} doit être un dictionnaire."
                    )

                return categories

    raise ValueError(
        f"La variable {NOM_VARIABLE_CATEGORIES} n'a pas été trouvée dans {chemin}."
    )


# ============================================================
# CRÉATION DE L'INDEX DES CATÉGORIES
# ============================================================


def construire_index_categories(categories):
    """
    Transforme SESSIONS_CATEGORIES en index utilisable avec les noms
    présents dans le fichier JSON.

    Le mapping est appliqué ici dans le bon sens :

        nom dans sessions.py -> nom dans stations_base.json

    Retourne :
    - l'index des associations ;
    - les noms volontairement ignorés ;
    - la liste des entrées issues de sessions.py.
    """

    index = {}
    noms_ignores = set()
    entrees_categories = []

    for theme, sous_themes in categories.items():
        if not isinstance(sous_themes, dict):
            print(
                f"AVERTISSEMENT : le thème {theme!r} ne contient pas un dictionnaire."
            )
            continue

        for sous_theme, noms_stations in sous_themes.items():
            if not isinstance(noms_stations, list):
                print(
                    f"AVERTISSEMENT : le sous-thème "
                    f"{sous_theme!r} ne contient pas une liste."
                )
                continue

            for nom_dans_sessions in noms_stations:
                if not isinstance(nom_dans_sessions, str):
                    print(
                        "AVERTISSEMENT : nom de station ignoré, "
                        f"type inattendu : {nom_dans_sessions!r}"
                    )
                    continue

                # Application du mapping dans le bon sens
                nom_dans_json = convertir_nom_sessions_vers_json(nom_dans_sessions)

                entree = {
                    "nom_dans_sessions": nom_dans_sessions,
                    "nom_dans_json": nom_dans_json,
                    "theme": theme,
                    "sous_theme": sous_theme,
                }

                entrees_categories.append(entree)

                # None signifie que l'absence est volontaire
                if nom_dans_json is None:
                    noms_ignores.add(normaliser_nom(nom_dans_sessions))
                    continue

                nom_normalise_json = normaliser_nom(nom_dans_json)

                if not nom_normalise_json:
                    continue

                association = {
                    "theme": theme,
                    "sous_theme": sous_theme,
                    "nom_dans_sessions": nom_dans_sessions,
                    "nom_dans_json": nom_dans_json,
                }

                index.setdefault(
                    nom_normalise_json,
                    [],
                ).append(association)

    return (
        index,
        noms_ignores,
        entrees_categories,
    )


# ============================================================
# DÉDOUBLONNAGE
# ============================================================


def dedoublonner(liste):
    """
    Déduplique une liste tout en conservant son ordre.
    """

    resultat = []

    for element in liste:
        if element not in resultat:
            resultat.append(element)

    return resultat


# ============================================================
# ENRICHISSEMENT DES STATIONS
# ============================================================


def enrichir_stations(stations, index_categories):
    """
    Ajoute les thèmes et sous-thèmes à chaque station du JSON.
    """

    nouvelles_stations = {}

    stations_trouvees = 0
    stations_sans_categorie = []

    # Noms normalisés des stations du JSON ayant trouvé
    # au moins une association.
    noms_json_utilises = set()

    # Noms exacts provenant de sessions.py et effectivement utilisés.
    noms_sessions_utilises = set()

    for nom_station, informations in stations.items():
        if not isinstance(informations, dict):
            print(
                f"AVERTISSEMENT : les informations de "
                f"{nom_station!r} ne sont pas un dictionnaire."
            )

            informations = {}

        nom_json_normalise = normaliser_nom(nom_station)

        associations = index_categories.get(
            nom_json_normalise,
            [],
        )

        nouvelles_informations = dict(informations)

        themes = []
        sous_themes = []
        categories_detaillees = []

        for association in associations:
            theme = association["theme"]
            sous_theme = association["sous_theme"]

            themes.append(theme)
            sous_themes.append(sous_theme)

            categories_detaillees.append(
                {
                    "theme": theme,
                    "sous_theme": sous_theme,
                }
            )

            noms_sessions_utilises.add(normaliser_nom(association["nom_dans_sessions"]))

        themes = dedoublonner(themes)
        sous_themes = dedoublonner(sous_themes)
        categories_detaillees = dedoublonner(categories_detaillees)

        if associations:
            stations_trouvees += 1

            noms_json_utilises.add(nom_json_normalise)

        else:
            stations_sans_categorie.append(nom_station)

        # Listes, car plusieurs thèmes et sous-thèmes
        # peuvent être associés à une même station.
        nouvelles_informations["theme"] = themes
        nouvelles_informations["sous_theme"] = sous_themes

        # Ce champ conserve la relation entre chaque thème
        # et son sous-thème.
        nouvelles_informations["categories"] = categories_detaillees

        nouvelles_stations[nom_station] = nouvelles_informations

    return (
        nouvelles_stations,
        stations_trouvees,
        stations_sans_categorie,
        noms_json_utilises,
        noms_sessions_utilises,
    )


# ============================================================
# CALCUL DES CORRESPONDANCES MANQUANTES
# ============================================================


def calculer_categories_sans_correspondance(
    entrees_categories,
    noms_sessions_utilises,
    noms_json_existants,
):
    """
    Retourne uniquement les noms de sessions.py qui :

    - ne sont pas explicitement associés à None ;
    - n'ont pas trouvé de correspondance dans le JSON.

    Les entrées comme Jean Moulin et Panthéon ne sont donc pas
    signalées puisqu'elles sont volontairement ignorées.
    """

    absentes = []

    for entree in entrees_categories:
        nom_sessions = entree["nom_dans_sessions"]
        nom_json = entree["nom_dans_json"]

        # Correspondance volontairement inexistante
        if nom_json is None:
            continue

        cle_sessions = normaliser_nom(nom_sessions)

        cle_json = normaliser_nom(nom_json)

        # La correspondance a été utilisée
        if cle_sessions in noms_sessions_utilises:
            continue

        # Le nom cible existe dans le JSON, il ne doit pas
        # être considéré comme absent.
        if cle_json in noms_json_existants:
            continue

        absentes.append(
            {
                "nom_dans_sessions": nom_sessions,
                "nom_attendu_dans_json": nom_json,
            }
        )

    # Déduplication
    resultat = []

    for element in absentes:
        if element not in resultat:
            resultat.append(element)

    return resultat


# ============================================================
# PROGRAMME PRINCIPAL
# ============================================================


def main():
    chemin_stations = Path(FICHIER_STATIONS)

    chemin_categories = Path(FICHIER_CATEGORIES)

    chemin_sortie = Path(FICHIER_SORTIE)

    # -----------------------------
    # Chargement des stations
    # -----------------------------

    stations = charger_json_avec_diagnostic(chemin_stations)

    if not isinstance(stations, dict):
        raise ValueError(
            "Le fichier des stations doit contenir un "
            "dictionnaire dont les clés sont les noms "
            "des stations."
        )

    noms_json_existants = {normaliser_nom(nom_station) for nom_station in stations}

    # -----------------------------
    # Chargement des catégories
    # -----------------------------

    categories = charger_categories_python(chemin_categories)

    (
        index_categories,
        noms_ignores,
        entrees_categories,
    ) = construire_index_categories(categories)

    # -----------------------------
    # Enrichissement
    # -----------------------------

    (
        nouvelles_stations,
        nombre_trouve,
        stations_sans_categorie,
        noms_json_utilises,
        noms_sessions_utilises,
    ) = enrichir_stations(
        stations,
        index_categories,
    )

    # -----------------------------
    # Catégories réellement absentes
    # -----------------------------

    stations_categories_absentes = calculer_categories_sans_correspondance(
        entrees_categories,
        noms_sessions_utilises,
        noms_json_existants,
    )

    # -----------------------------
    # Écriture du nouveau JSON
    # -----------------------------

    chemin_sortie.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with chemin_sortie.open(
        "w",
        encoding="utf-8",
    ) as fichier:
        json.dump(
            nouvelles_stations,
            fichier,
            ensure_ascii=False,
            indent=4,
        )

        fichier.write("\n")

    # -----------------------------
    # Rapport
    # -----------------------------

    print("=" * 70)
    print("RÉSULTAT")
    print("=" * 70)

    print(f"Stations dans le JSON : {len(stations)}")

    print(f"Stations ayant au moins une catégorie : {nombre_trouve}")

    print(f"Stations sans catégorie : {len(stations_sans_categorie)}")

    print(f"Entrées volontairement sans correspondance : {len(noms_ignores)}")

    print(
        "Stations de sessions.py réellement absentes "
        f"du JSON : {len(stations_categories_absentes)}"
    )

    print(f"Fichier créé : {chemin_sortie.resolve()}")

    # -----------------------------
    # Stations JSON sans catégorie
    # -----------------------------

    if stations_sans_categorie:
        print("\nPremières stations du JSON sans catégorie :")

        for nom_station in stations_sans_categorie[:20]:
            print(f"  - {nom_station}")

    # -----------------------------
    # Entrées ignorées volontairement
    # -----------------------------

    entrees_ignorees = sorted(
        [
            nom_sessions
            for nom_sessions, nom_json in MAPPING_NOMS_STATIONS.items()
            if nom_json is None
        ],
        key=str.casefold,
    )

    if entrees_ignorees:
        print("\nEntrées ignorées volontairement :")

        for nom_station in entrees_ignorees:
            print(f"  - {nom_station}")

    # -----------------------------
    # Vraies correspondances absentes
    # -----------------------------

    if stations_categories_absentes:
        print("\nStations de sessions.py sans correspondance dans le JSON :")

        for element in stations_categories_absentes[:30]:
            print(
                f"  - {element['nom_dans_sessions']} "
                f"-> nom JSON attendu : "
                f"{element['nom_attendu_dans_json']}"
            )


if __name__ == "__main__":
    main()
