import mysql.connector
import os

from dotenv import load_dotenv

load_dotenv()
password = os.getenv("MYSQL_PASSWORD")
user = os.getenv("MYSQL_USER")
mydb = mysql.connector.connect(
    host=f"{user}.mysql.pythonanywhere-services.com",
    user=f"{user}",
    passwd=f"{password}",
)

my_cursor = mydb.cursor()
# my_cursor.execute("CREATE DATABASE "+mydb.user+"$users")
# my_cursor.execute("SHOW DATABASES")
# for db in my_cursor:
#    print(db)
# my_cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'jisifu$default';")
my_cursor.execute(
    "SELECT table_name FROM information_schema.tables WHERE table_schema = 'jisifu$default';"
)
for db in my_cursor:
    print(db)
