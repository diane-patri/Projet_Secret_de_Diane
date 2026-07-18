# build.py
import json

def compiler_projet():
    # Lecture du squelette de l'interface
    with open("template.html", "r", encoding="utf-8") as f:
        html_content = f.read()

    # Lecture des styles visuels
    with open("style.css", "r", encoding="utf-8") as f:
        css_content = f.read()

    # Lecture de la logique interactive complète
    with open("logic.js", "r", encoding="utf-8") as f:
        js_content = f.read()

    # Lecture des bases de données au format JSON
    with open("data.json", "r", encoding="utf-8") as f:
        donnees_stations = json.load(f)

    with open("sessions_config.json", "r", encoding="utf-8") as f:
        config_sessions = json.load(f)

    # Transformation des données en constantes JavaScript globales
    donnees_stations_str = json.dumps(donnees_stations, ensure_ascii=False)
    donnees_sessions_str = json.dumps(config_sessions, ensure_ascii=False)

    js_complet = (
        f"const STATIONS = {donnees_stations_str};\n"
        f"const SESSIONS_CONFIG = {donnees_sessions_str};\n\n"
        f"{js_content}"
    )

    # Remplacement des balises d'injection par le code réel
    html_content = html_content.replace("/* INJECT_CSS */", css_content)
    html_content = html_content.replace("/* INJECT_JS */", js_complet)

    # Création du fichier exécutable par le navigateur
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)

    print("L'application a été compilée avec succès dans 'index.html'.")

if __name__ == "__main__":
    compiler_projet()