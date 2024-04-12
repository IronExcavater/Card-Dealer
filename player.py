import sql


class Player:
    def __init__(self, id: int, name: str, balance=200):
        self.id = id
        self.name = name
        self.balance = balance
        self.bet = 0
        self.hand = []

    def bet(self, amount: int):
        self.bet = amount

    def withdraw(self, amount: int):
        self.balance -= amount
        Player.update_record(self)

    def deposit(self, amount: int):
        self.balance += amount
        Player.update_record(self)

    def create_record(self):
        create = '''
        INSERT INTO players VALUE
        ('{0}', '{1}', {2})
        '''.format(self.id, self.name, self.balance)
        sql.execute_query(sql.sql_connection, create)

    def update_record(self):
        update = '''
        UPDATE players
        SET balance = {0}
        WHERE id = {1}
        '''.format(self.balance, self.id)
        sql.execute_query(sql.sql_connection, update)
