import os
import sqlite3

conn = sqlite3.connect('voters.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()

c.execute('SELECT id, serial_no, name, epic_id, photo_path FROM voters WHERE gp_serial IS NULL')
rows = c.fetchall()
print(f"Total voters with gp_serial IS NULL: {len(rows)}")
for r in rows:
    p_path = r['photo_path'].lstrip('/') if r['photo_path'] else ''
    exists = os.path.exists(p_path)
    print(f"ID: {r['id']} | Name: {r['name']} | EPIC: {r['epic_id']} | Photo: {r['photo_path']} | Exists? {exists}")
