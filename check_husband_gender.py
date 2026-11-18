import sqlite3
import cv2
import re

conn = sqlite3.connect('voters.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()

c.execute('SELECT * FROM voters WHERE gp_serial IS NOT NULL ORDER BY gp_serial ASC')
voters = {r['gp_serial']: dict(r) for r in c.fetchall()}

# Check cards where relation is Husband (భర్త)
# Let's inspect Telugu text on the cards:
# We know in Telugu: భర్త (BhartHa) = Husband
# If a card has భర్త, the voter is female.

# Let's check how many voters in DB have relation_type = 'Husband'
c.execute("SELECT COUNT(*) FROM voters WHERE relation_type = 'Husband' AND gender = 'Male'")
h_male = c.fetchall()
print("Voters with relation_type == 'Husband' but gender == 'Male':", h_male)

c.execute("SELECT id, gp_serial, name, gender, relation_type, relation_name FROM voters WHERE relation_type = 'Husband' AND gender = 'Male'")
for r in c.fetchall():
    print("  ", dict(r))
