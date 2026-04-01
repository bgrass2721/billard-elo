class EloEngine:
    def __init__(self, initial_elo=1000):
        self.initial_elo = initial_elo
        
        # --- PARAMÈTRES V3 (Asymétrique + Diviseur 600) ---
        self.k_win = 50       
        self.k_loss = 30      
        self.diviseur = 600   

    def compute_new_ratings(self, winner_elo, loser_elo, winner_matches=0, loser_matches=0):
        # Probabilités de victoire
        exp_winner = 1 / (1 + 10 ** ((loser_elo - winner_elo) / self.diviseur))
        exp_loser = 1 / (1 + 10 ** ((winner_elo - loser_elo) / self.diviseur))

        # Calcul des gains et pertes asymétriques
        gain = round(self.k_win * (1 - exp_winner))
        perte = round(self.k_loss * (0 - exp_loser)) # Valeur négative

        # Application des scores
        new_winner_elo = winner_elo + gain
        new_loser_elo = loser_elo + perte 

        # On retourne 4 valeurs : Nouveaux Elos, le Gain (positif), et la Perte (en valeur absolue)
        return new_winner_elo, new_loser_elo, gain, abs(perte)