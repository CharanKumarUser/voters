import sqlite3

conn = sqlite3.connect('voters.db')
c = conn.cursor()
c.execute('SELECT COUNT(*) FROM voters')
total = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM voters WHERE party = 'UNASSIGNED'")
unassigned = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM voters WHERE photo_path IS NOT NULL AND photo_path != ''")
with_photo = c.fetchone()[0]
c.execute('SELECT COUNT(*) FROM voters WHERE gp_serial IS NOT NULL')
with_gp = c.fetchone()[0]
c.execute('SELECT MIN(gp_serial), MAX(gp_serial) FROM voters WHERE gp_serial IS NOT NULL')
gp_range = c.fetchone()

print(f'Total in DB: {total}')
print(f'Unassigned (Clean Slate): {unassigned}')
print(f'Voters with Photos: {with_photo}')
print(f'Voters with GP Serials: {with_gp} (Range: {gp_range[0]} to {gp_range[1]})')
