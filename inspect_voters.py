import sqlite3

conn = sqlite3.connect('voters.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()

c.execute('SELECT * FROM voters WHERE gp_serial IS NOT NULL ORDER BY gp_serial ASC')
rows = c.fetchall()

print(f"Total voters with GP serial: {len(rows)}")
for r in rows[:25]:
    print(f"ID:{r['id']} | Serial:{r['serial_no']} | GP#{r['gp_serial']} | Name:{r['name']} | Gender:{r['gender']} | EPIC:{r['epic_id']} | Photo:{r['photo_path']}")
