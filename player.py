import sql


class Player:
    def __init__(self, user_id: int, user_name: str, display_name: str, balance=200):
        self.id = user_id
        self.user_name = user_name
        self.display_name = display_name
        self.balance = balance
        self.inactivity = 0
        self.insurance_bet = 0
        self.hands = []

    def change_balance(self, amount: int):
        self.balance += amount
        Player.update_record(self)

    def create_record(self):
        create = '''
        INSERT INTO players (user_id, user_name, display_name, balance) VALUE
        ('{0}', '{1}', '{2}', {3})
        '''.format(self.id, self.user_name, self.display_name, self.balance)
        sql.execute_query(sql.sql_connection, create)

    def update_record(self):
        update = '''
        UPDATE players
        SET balance = {0}
        WHERE user_id = {1}
        '''.format(self.balance, self.id)
        sql.execute_query(sql.sql_connection, update)
