import json
import re
import unicodedata
from pathlib import Path


# ============================================================
# CONFIGURATION
# ============================================================

# JSON principal, organisé en dictionnaire :
# {
#     "Abbesses": {...},
#     "Aimé Césaire": {...}
# }
FICHIER_BASE = "stations_base_avec_categories.json"

# JSON enrichi, organisé en liste :
# [
#     {
#         "station": "Abbesses",
#         "theme": "Lieu géographique",
#         ...
#     }
# ]
FICHIER_ENRICHISSEMENT = "corrigé_complet.json"

# Nouveau fichier produit
FICHIER_SORTIE = "stations_finales.json"

# ------------------------------------------------------------
# Options de fusion
# ------------------------------------------------------------

# Ajoute pourquoi_ce_nom dans le JSON final.
AJOUTER_POURQUOI_CE_NOM = True

# Ajoute l'objet personne complet.
AJOUTER_INFORMATIONS_PERSONNE = True

# Ajoute le type détecté par Wikipédia dans les champs :
# type_origine et sous_type_origine.
AJOUTER_TYPE_ORIGINE = True

# Ajoute le thème Wikipédia dans les listes theme, sous_theme
# et categories.
#
# Il est conseillé de laisser False, car les thèmes du premier
# fichier constituent une taxonomie différente.
AJOUTER_TYPE_ORIGINE_AUX_CATEGORIES = False

# Ajoute le résumé de la page de station.
AJOUTER_RESUME_STATION = False

# Ajoute la source Wikipédia complète.
AJOUTER_SOURCE_STATION = False

# Remplace une description existante.
# False signifie que seules les descriptions nulles ou vides
# seront alimentées.
REMPLACER_DESCRIPTION_EXISTANTE = False

# Remplace un siècle existant.
REMPLACER_SIECLE_EXISTANT = False

# Si True, les stations du fichier d'enrichissement absentes
# du fichier de base seront ajoutées.
AJOUTER_STATIONS_ABSENTES = False


# ============================================================
# MAPPING ÉVENTUEL DES NOMS
# ============================================================

# Sens :
# nom dans le JSON d'enrichissement -> nom dans le JSON principal

MAPPING_NOMS_STATIONS = {
    # Exemples :
    # "Austerlitz": "Gare d'Austerlitz",
    # "Europe - Simone Veil": "Europe",
}

# Pour ton cas actuel, les noms semblent déjà correspondre.
# Tu peux donc laisser ce dictionnaire vide.


# ============================================================
# OUTILS DE NORMALISATION
# ============================================================


def normaliser_nom(nom):
    """
    Normalise un nom pour faire correspondre les stations malgré :
    - les accents ;
    - les différences de casse ;
    - les tirets ;
    - les apostrophes ;
    - les espaces multiples.
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

    nom = nom.replace("’", "'")
    nom = nom.replace("`", "'")

    nom = re.sub(
        r"[-–—_'’]+",
        " ",
        nom,
    )

    nom = re.sub(
        r"[^a-z0-9]+",
        " ",
        nom,
    )

    nom = re.sub(
        r"\s+",
        " ",
        nom,
    )

    return nom.strip()


def dedoublonner(liste):
    """
    Déduplique une liste tout en conservant l'ordre.
    """

    resultat = []

    for element in liste:
        if element not in resultat:
            resultat.append(element)

    return resultat


# ============================================================
# LECTURE JSON AVEC DIAGNOSTIC
# ============================================================


def charger_json(chemin):
    """
    Charge un fichier JSON et affiche la ligne exacte en cas
    d'erreur de syntaxe.
    """

    chemin = Path(chemin)

    if not chemin.exists():
        raise FileNotFoundError(f"Fichier introuvable : {chemin.resolve()}")

    contenu = chemin.read_text(
        encoding="utf-8-sig",
    )

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

        debut = max(
            0,
            erreur.lineno - 4,
        )

        fin = min(
            len(lignes),
            erreur.lineno + 3,
        )

        print("\nContexte :")

        for index in range(debut, fin):
            numero = index + 1

            marqueur = ">>>" if numero == erreur.lineno else "   "

            print(f"{marqueur} {numero:5d} | {lignes[index]}")

            if numero == erreur.lineno:
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


def sauvegarder_json(chemin, donnees):
    """
    Écrit le fichier dans un fichier temporaire avant de remplacer
    le fichier final.
    """

    chemin = Path(chemin)

    chemin.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    chemin_temporaire = chemin.with_suffix(chemin.suffix + ".tmp")

    chemin_temporaire.write_text(
        json.dumps(
            donnees,
            ensure_ascii=False,
            indent=4,
        )
        + "\n",
        encoding="utf-8",
    )

    chemin_temporaire.replace(chemin)


# ============================================================
# INDEX DES STATIONS
# ============================================================


def construire_index_base(stations_base):
    """
    Crée un index normalisé :

    {
        "aime cesaire": "Aimé Césaire",
        "alexandre dumas": "Alexandre Dumas"
    }
    """

    index = {}

    for nom_station in stations_base:
        cle = normaliser_nom(nom_station)

        if cle in index:
            print(
                "AVERTISSEMENT : plusieurs noms de stations "
                f"correspondent à la clé {cle!r}."
            )

        index[cle] = nom_station

    return index


def construire_mapping_normalise():
    """
    Normalise les clés du mapping manuel.
    """

    return {
        normaliser_nom(nom_source): nom_cible
        for nom_source, nom_cible in MAPPING_NOMS_STATIONS.items()
    }


# ============================================================
# MISE À JOUR DES CHAMPS
# ============================================================


def ajouter_categorie(
    informations_base,
    theme,
    sous_theme,
):
    """
    Ajoute un thème et son sous-thème aux champs existants,
    sans doublon.
    """

    if not theme:
        return

    themes = informations_base.get("theme")

    if not isinstance(themes, list):
        themes = [] if themes is None else [themes]

    sous_themes = informations_base.get("sous_theme")

    if not isinstance(sous_themes, list):
        sous_themes = [] if sous_themes is None else [sous_themes]

    categories = informations_base.get("categories")

    if not isinstance(categories, list):
        categories = []

    themes.append(theme)

    if sous_theme:
        sous_themes.append(sous_theme)

    categorie = {
        "theme": theme,
        "sous_theme": sous_theme,
    }

    if categorie not in categories:
        categories.append(categorie)

    informations_base["theme"] = dedoublonner(themes)

    informations_base["sous_theme"] = dedoublonner(sous_themes)

    informations_base["categories"] = categories


def obtenir_siecles(enrichissement):
    """
    Récupère les siècles depuis l'objet personne.
    """

    personne = enrichissement.get("personne")

    if not isinstance(personne, dict):
        return None

    siecles = personne.get("siecles_vecus")

    if not siecles:
        return None

    if isinstance(siecles, str):
        return [siecles]

    if isinstance(siecles, list):
        return dedoublonner(siecles)

    return None


def fusionner_une_station(
    informations_base,
    enrichissement,
):
    """
    Fusionne les informations Wikipédia dans la station de base.
    """

    # --------------------------------------------------------
    # Description
    # --------------------------------------------------------

    description_actuelle = informations_base.get("description")

    nouvelle_description = enrichissement.get("informations")

    if nouvelle_description:
        if REMPLACER_DESCRIPTION_EXISTANTE or not description_actuelle:
            informations_base["description"] = nouvelle_description

    # --------------------------------------------------------
    # Siècle
    # --------------------------------------------------------

    siecles = obtenir_siecles(enrichissement)

    siecle_actuel = informations_base.get("siecle")

    if siecles:
        if REMPLACER_SIECLE_EXISTANT or not siecle_actuel:
            informations_base["siecle"] = siecles

    # --------------------------------------------------------
    # Pourquoi ce nom
    # --------------------------------------------------------

    if AJOUTER_POURQUOI_CE_NOM:
        informations_base["pourquoi_ce_nom"] = enrichissement.get("pourquoi_ce_nom")

    # --------------------------------------------------------
    # Type de l'origine
    # --------------------------------------------------------

    theme_origine = enrichissement.get("theme")

    sous_theme_origine = enrichissement.get("sous_theme")

    if AJOUTER_TYPE_ORIGINE:
        informations_base["type_origine"] = theme_origine

        informations_base["sous_type_origine"] = sous_theme_origine

    # --------------------------------------------------------
    # Ajout éventuel dans les catégories existantes
    # --------------------------------------------------------

    if AJOUTER_TYPE_ORIGINE_AUX_CATEGORIES:
        ajouter_categorie(
            informations_base,
            theme_origine,
            sous_theme_origine,
        )

    # --------------------------------------------------------
    # Informations sur la personne
    # --------------------------------------------------------

    if AJOUTER_INFORMATIONS_PERSONNE:
        personne = enrichissement.get("personne")

        if isinstance(personne, dict):
            informations_base["personne"] = personne

        elif theme_origine == "Personne":
            informations_base["personne"] = None

    # --------------------------------------------------------
    # Source Wikipédia
    # --------------------------------------------------------

    source_station = enrichissement.get("source_station")

    if AJOUTER_SOURCE_STATION and isinstance(source_station, dict):
        informations_base["source_station"] = source_station

    # --------------------------------------------------------
    # Résumé de la station
    # --------------------------------------------------------

    if AJOUTER_RESUME_STATION and isinstance(source_station, dict):
        informations_base["resume_station"] = source_station.get("resume")


# ============================================================
# FUSION COMPLÈTE
# ============================================================


def fusionner_donnees(
    stations_base,
    enrichissements,
):
    """
    Fusionne tous les éléments de la liste d'enrichissement dans
    le dictionnaire des stations.
    """

    # Copie complète par sérialisation JSON
    stations_finales = json.loads(
        json.dumps(
            stations_base,
            ensure_ascii=False,
        )
    )

    index_base = construire_index_base(stations_finales)

    mapping_normalise = construire_mapping_normalise()

    stations_mises_a_jour = 0
    stations_sans_correspondance = []
    stations_enrichissement_invalides = []
    noms_base_utilises = set()

    for position, enrichissement in enumerate(
        enrichissements,
        start=1,
    ):
        if not isinstance(enrichissement, dict):
            stations_enrichissement_invalides.append(position)
            continue

        nom_source = enrichissement.get("station")

        if not isinstance(nom_source, str):
            stations_enrichissement_invalides.append(position)
            continue

        cle_source = normaliser_nom(nom_source)

        # Application éventuelle du mapping
        nom_recherche = mapping_normalise.get(
            cle_source,
            nom_source,
        )

        if nom_recherche is None:
            stations_sans_correspondance.append(nom_source)
            continue

        cle_recherche = normaliser_nom(nom_recherche)

        nom_dans_base = index_base.get(cle_recherche)

        if nom_dans_base is None:
            if AJOUTER_STATIONS_ABSENTES:
                nom_dans_base = nom_recherche

                stations_finales[nom_dans_base] = {
                    "lignes": [],
                    "commune": None,
                    "code_insee": None,
                    "latitude": None,
                    "longitude": None,
                    "theme": [],
                    "sous_theme": [],
                    "siecle": None,
                    "description": None,
                    "categories": [],
                }

                index_base[cle_recherche] = nom_dans_base

            else:
                stations_sans_correspondance.append(nom_source)
                continue

        fusionner_une_station(
            stations_finales[nom_dans_base],
            enrichissement,
        )

        stations_mises_a_jour += 1

        noms_base_utilises.add(normaliser_nom(nom_dans_base))

    stations_base_sans_enrichissement = [
        nom_station
        for nom_station in stations_finales
        if normaliser_nom(nom_station) not in noms_base_utilises
    ]

    return {
        "stations": stations_finales,
        "nombre_mises_a_jour": stations_mises_a_jour,
        "sans_correspondance": dedoublonner(stations_sans_correspondance),
        "entrees_invalides": (stations_enrichissement_invalides),
        "base_sans_enrichissement": (stations_base_sans_enrichissement),
    }


# ============================================================
# PROGRAMME PRINCIPAL
# ============================================================


def main():
    print("=" * 70)
    print("FUSION DES INFORMATIONS DES STATIONS")
    print("=" * 70)

    stations_base = charger_json(FICHIER_BASE)

    enrichissements = charger_json(FICHIER_ENRICHISSEMENT)

    if not isinstance(stations_base, dict):
        raise ValueError(
            "Le fichier de base doit contenir un dictionnaire "
            "indexé par nom de station."
        )

    if not isinstance(enrichissements, list):
        raise ValueError(
            "Le fichier d'enrichissement doit contenir une liste d'objets."
        )

    resultat = fusionner_donnees(
        stations_base,
        enrichissements,
    )

    sauvegarder_json(
        FICHIER_SORTIE,
        resultat["stations"],
    )

    print(f"Stations dans le fichier de base : {len(stations_base)}")

    print(f"Entrées dans l'enrichissement : {len(enrichissements)}")

    print(f"Stations mises à jour : {resultat['nombre_mises_a_jour']}")

    print(
        "Stations enrichies sans correspondance : "
        f"{len(resultat['sans_correspondance'])}"
    )

    print(
        "Stations de base sans enrichissement : "
        f"{len(resultat['base_sans_enrichissement'])}"
    )

    print(f"Entrées invalides : {len(resultat['entrees_invalides'])}")

    print(f"Fichier créé : {Path(FICHIER_SORTIE).resolve()}")

    if resultat["sans_correspondance"]:
        print("\nStations du fichier d'enrichissement sans correspondance :")

        for station in resultat["sans_correspondance"][:30]:
            print(f"  - {station}")

    if resultat["base_sans_enrichissement"]:
        print("\nPremières stations de la base sans enrichissement :")

        for station in resultat["base_sans_enrichissement"][:30]:
            print(f"  - {station}")

    if resultat["entrees_invalides"]:
        print("\nPositions des entrées invalides dans la liste d'enrichissement :")

        for position in resultat["entrees_invalides"]:
            print(f"  - élément #{position}")


if __name__ == "__main__":
    main()
