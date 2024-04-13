import os
import sys

from dotenv import load_dotenv

import mysql.connector
from mysql.connector import Error

load_dotenv()
mysql_password = os.environ['MYSQL_PASSWORD']


def establish_connection(host_name, user_name, database_name):
    try:
        connection = mysql.connector.connect(host=host_name, user=user_name, password=mysql_password, database=database_name)
        print('Established connection to MySQL {0} database'.format(database_name))
        return connection
    except Error as e:
        print('Error while connecting to MySQL Database,', e)
        sys.exit()


def create_database(connection, query):
    cursor = connection.cursor()
    try:
        cursor.execute(query)
        print('Database successfully created')
    except Error as e:
        print('Error while creating database,', e)
        sys.exit()


def execute_query(connection, query):
    cursor = connection.cursor()
    try:
        cursor.execute(query)
        connection.commit()
        print('Query successfully executed')
    except Error as e:
        print('Error while executing query,', e)
        sys.exit()


def read_query(connection, query):
    cursor = connection.cursor()
    try:
        cursor.execute(query)
        return cursor.fetchall()
    except Error as e:
        print('Error while executing query,', e)
        sys.exit()


sql_connection = establish_connection('localhost', 'root', 'blackjack')
