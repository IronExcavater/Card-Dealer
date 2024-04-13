import sql

create = '''
CREATE TABLE players (
    user_id VARCHAR(18) PRIMARY KEY NOT NULL,
    name TEXT NOT NULL,
    balance INT NOT NULL,
    last_reward DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
)
'''
sql.execute_query(sql.sql_connection, create)
