# main.py

from data import STATIONS
from game_logic import MetroGame

def play_round(game, theme):
    stations = game.get_stations_by_theme(theme)
    stations_names = list(stations.keys())
    
    print(f"\nVous avez sélectionné le thème : {theme}")
    print(f"Il y a {len(stations_names)} stations à identifier.")
    
    for target_station in stations_names:
        data = stations[target_station]
        print("\n--- Nouvelle station à deviner ---")
        
        hints = game.generate_hints(target_station, data)
        hint_index = 0
        max_hints = len(hints)
        
        guessed = False
        while not guessed:
            guess = input("Votre proposition (tapez 'indice' pour une aide, ou 'quitter') : ").strip()
            
            if guess.lower() == 'quitter':
                return
                
            if guess.lower() == target_station.lower():
                print("Correct ! C'est la bonne station.")
                guessed = True
            elif guess.lower() == 'indice':
                if hint_index < max_hints:
                    print(f"Indice : {hints[hint_index]}")
                    hint_index += 1
                else:
                    print("Vous avez épuisé tous les indices pour cette station.")
            else:
                print("Proposition incorrecte. Vous pouvez demander un indice.")
                
    print(f"\nFin du jeu. Vous avez identifié toutes les stations du thème {theme}.")

def main():
    # Instanciation de l'objet jeu avec les données importées.
    game = MetroGame(STATIONS)
    print("Application d'apprentissage thématique du métro parisien.")
    
    while True:
        print("\nThèmes disponibles :")
        for i, theme in enumerate(game.themes):
            print(f"- {i + 1}. {theme}")
        
        choice = input("\nIndiquez le numéro du thème souhaité (ou 'q' pour quitter) : ").strip()
        
        if choice.lower() == 'q':
            print("Fermeture de l'application.")
            break
        
        # Le bloc try/except capture les erreurs de saisie (si l'utilisateur tape une lettre au lieu d'un chiffre).
        try:
            theme_index = int(choice) - 1
            if 0 <= theme_index < len(game.themes):
                selected_theme = game.themes[theme_index]
                play_round(game, selected_theme)
            else:
                print("Erreur : Ce numéro ne correspond à aucun thème.")
        except ValueError:
            print("Erreur : La saisie attendue est un chiffre numérique.")

if __name__ == "__main__":
    main()
    