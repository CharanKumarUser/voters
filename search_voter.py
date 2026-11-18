import sqlite3

conn = sqlite3.connect('voters.db')
c = conn.cursor()
c.execute("SELECT serial_no, epic_id, name, relation_type, relation_name, house_no, age, gender FROM voters WHERE epic_id LIKE '%0618025%'")
print('Search 0618025:', c.fetchall())

# Let's also check UXN2085678 (Mahendravarma)
c.execute("SELECT serial_no, epic_id, name, relation_type, relation_name, house_no, age, gender FROM voters WHERE epic_id LIKE '%2085678%'")
print('Search 2085678:', c.fetchall())
conn.close()
