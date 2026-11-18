import sqlite3
import json

conn = sqlite3.connect('voters.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()

# Check voters that were inserted with generic names like 'Voter GP#...'
c.execute("SELECT gp_serial, serial_no, name, gender, epic_id FROM voters WHERE name LIKE 'Voter GP%'")
generic_voters = c.fetchall()
print(f"Generic 'Voter GP#...' voters: {len(generic_voters)}")
for g in generic_voters:
    print(dict(g))
