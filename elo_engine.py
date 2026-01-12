class EloEngine:
    def __init__(self, initial_elo=1000):
        self.initial_elo = initial_elo

    def get_k_factor(self, matches_played):
        """
        Détermine le facteur K uniquement selon l'expérience du joueur.
        """
        if matches_played <= 10:
            return 40
        elif matches_played <= 30:
            return 20
        else:
            return 10

    def compute_new_ratings(self, winner_elo, loser_elo, winner_matches, loser_matches):
        # Probabilité de victoire du gagnant
        expected_win = 1 / (1 + 10 ** ((loser_elo - winner_elo) / 400))

        # On calcule le delta en utilisant le K du gagnant
        # (ou une moyenne des deux K pour être plus juste)
        k_winner = self.get_k_factor(winner_matches)

        delta = round(k_winner * (1 - expected_win))

        # On s'assure que le perdant ne perd pas plus que ce que le gagnant gagne
        new_winner_elo = winner_elo + delta
        new_loser_elo = loser_elo - delta

        return new_winner_elo, new_loser_elo, delta
