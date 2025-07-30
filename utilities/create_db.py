import mysql.connector

mydb = mysql.connector.connect(
    host="jisifu.mysql.pythonanywhere-services.com",
    user="jisifu",
    passwd="j]Q)Kwb9#8&R:&b",
)

my_cursor = mydb.cursor()
#my_cursor.execute("CREATE DATABASE "+mydb.user+"$users")
my_cursor.execute("SHOW DATABASES")
for db in my_cursor:
    print(db)
