class Player:
    def __init__(
        self,
        username,
        elo,
        email,
        password=None,
        pokemon_fan=False,
        id_player=None,
        access_token=None,
    ):
        self.username = username
        self.elo = elo
        self.email = email