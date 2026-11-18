import sqlite3

conn = sqlite3.connect('voters.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()

# 1. Update the 7 correctly matched voters from the old roll into their respective GP cards
updates = [
    # (gp_serial, old_serial_no, dummy_id)
    (282, 271, 568),
    (300, 288, 569),
    (412, 398, 579),
    (422, 406, 583),
    (432, 412, 587),
    (465, 441, 600),
    (556, 493, 605)
]

for gp_s, old_s, dummy_id in updates:
    c.execute('SELECT * FROM voters WHERE serial_no = ? AND gp_serial IS NULL', (old_s,))
    old_row = c.fetchone()
    if old_row:
        c.execute('''
            UPDATE voters SET
                name = ?,
                relation_type = ?,
                relation_name = ?,
                gender = ?,
                age = ?,
                house_no = ?,
                epic_id = ?
            WHERE id = ?
        ''', (
            old_row['name'],
            old_row['relation_type'],
            old_row['relation_name'],
            old_row['gender'],
            old_row['age'],
            old_row['house_no'],
            old_row['epic_id'].replace('UXNO', 'UXN0'),
            dummy_id
        ))
        print(f"Updated GP#{gp_s} (ID:{dummy_id}) with correct voter #{old_s}: '{old_row['name']}' ({old_row['gender']})")

# 2. Delete all records where gp_serial IS NULL (the unlinked old records not in GP roll)
c.execute('DELETE FROM voters WHERE gp_serial IS NULL')
conn.commit()

# 3. Verify counts
c.execute('SELECT COUNT(*) FROM voters')
total = c.fetchone()[0]

c.execute('SELECT COUNT(DISTINCT gp_serial) FROM voters')
distinct_gp = c.fetchone()[0]

c.execute('SELECT MIN(gp_serial), MAX(gp_serial) FROM voters')
min_gp, max_gp = c.fetchone()

c.execute("SELECT COUNT(*) FROM voters WHERE photo_path IS NULL OR photo_path = '' OR photo_path LIKE '%photo_0%'")
bad_photos = c.fetchone()[0]

c.execute("SELECT COUNT(*) FROM voters WHERE gender = 'Female'")
females = c.fetchone()[0]

c.execute("SELECT COUNT(*) FROM voters WHERE gender = 'Male'")
males = c.fetchone()[0]

print(f"\n--- VERIFICATION ---")
print(f"Total voters in DB: {total} (Expected: 593)")
print(f"Distinct GP Serials: {distinct_gp} (Expected: 593)")
print(f"GP Serial Range: {min_gp} to {max_gp} (Expected: 1 to 593)")
print(f"Bad / Dummy Photos: {bad_photos} (Expected: 0)")
print(f"Females: {females}, Males: {males} (Total: {females + males})")

conn.close()
