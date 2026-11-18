import sqlite3

conn = sqlite3.connect('voters.db')
c = conn.cursor()
c.execute("SELECT gender, count(id) FROM voters GROUP BY gender")
print(c.fetchall())
