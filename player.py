import sql


class Player:
    def __init__(self, user_id: int, user_name: str, display_name: str, wins: int, total_games: int, balance=200):
        self.id = user_id
        self.user_name = user_name
        self.display_name = display_name
        self.balance = balance
        self.inactivity = 0
        self.blackjack_extras = {'insurance': 0, 'even': False}
        self.hands = []
        self.wins = wins
        self.total_games = total_games

    def create_record(self):
        create = '''
        INSERT INTO players (user_id, user_name, display_name, balance, wins, total_games) VALUE
        ('{0}', '{1}', '{2}', {3}, 0, 0)
        '''.format(self.id, self.user_name, self.display_name, self.balance)
        sql.execute_query(sql.sql_connection, create)

    def change_balance(self, amount: int):
        self.balance += amount
        update = '''
                UPDATE players
                SET balance = {0}
                WHERE user_id = {1}
                '''.format(self.balance, self.id)
        sql.execute_query(sql.sql_connection, update)

    def change_games(self, is_win: bool):
        if is_win:
            self.wins += 1
        self.total_games += 1
        update = '''
        UPDATE players
        SET wins = {0}, total_games = {1}
        WHERE user_id = {2}
        '''.format(self.wins, self.total_games, self.id)
        sql.execute_query(sql.sql_connection, update)
