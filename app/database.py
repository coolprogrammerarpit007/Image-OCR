import mysql.connector
from mysql.connector import Error
from app.config import settings

class MySQLConnection:
    def __init__(self):
        self.connection = None

    def get_connection(self):
        try:
            if not self.connection or not self.connection.is_connected():
                self.connection = mysql.connector.connect(
                host=settings.MYSQL_HOST,
                port=settings.MYSQL_PORT,   # 👈 IMPORTANT
                user=settings.MYSQL_USER,
                password=settings.MYSQL_PASSWORD,
                database=settings.MYSQL_DATABASE,
                use_pure=True               # 👈 force TCP, avoid named pipe
            )
            return self.connection
        except Error as e:
            raise RuntimeError(f"DB Connection Failed: {e}")

db = MySQLConnection()