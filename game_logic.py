# game_logic.py

class MetroGame:
    def __init__(self, stations_data):
        self.stations_data = stations_data
        self.themes = self._extract_themes()

    def _extract_themes(self):
        # L'utilisation d'un ensemble (set) permet d'éliminer automatiquement les doublons.
        themes = set()
        for data in self.stations_data.values():
            themes.add(data["theme"])
        # Le retour est une liste triée alphabétiquement pour un affichage cohérent.
        return sorted(list(themes))

    def get_stations_by_theme(self, theme):
        # Une compréhension de dictionnaire filtre les stations selon le thème sélectionné.
        return {name: data for name, data in self.stations_data.items() if data["theme"] == theme}

    def generate_hints(self, station_name, station_data):
        # Cette méthode construit la liste ordonnée des indices.
        lignes = station_data["lignes"]
        hints = []
        
        # Indice 1 : La ligne principale
        hints.append(f"La station se trouve sur la ligne {lignes[0]}.")
        
        # Indice 2 : Les correspondances
        if len(lignes) > 1:
            autres_lignes = ", ".join(lignes[1:])
            hints.append(f"Elle est également desservie par les lignes : {autres_lignes}.")
        else:
            hints.append("Il n'y a aucune autre ligne à cette station.")
            
        # Indice 3 : La première lettre
        hints.append(f"La première lettre de la station est '{station_name[0]}'.")
        
        # Indice 4 : Un indice supplémentaire sur la longueur du mot
        hints.append(f"Le nom complet comporte {len(station_name)} caractères (espaces inclus).")
        
        return hints
    