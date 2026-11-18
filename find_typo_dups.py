import sqlite3

conn = sqlite3.connect('voters.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()

c.execute('SELECT id, serial_no, gp_serial, name, epic_id, photo_path FROM voters')
all_voters = c.fetchall()

print(f"Total voters currently: {len(all_voters)}")

# Normalize epic: replace O with 0 in UXNO -> UXN0
by_clean_epic = {}
duplicates = []

for v in all_voters:
    raw = v['epic_id'] or ''
    clean = raw.replace('UXNO', 'UXN0').replace('CWB0', 'CWB0').strip()
    if clean in by_clean_epic:
        duplicates.append((by_clean_epic[clean], dict(v)))
    else:
        by_clean_epic[clean] = dict(v)

print(f"Found {len(duplicates)} duplicate pairs between old roll and new GP roll:")
for d1, d2 in duplicates:
    print(f"  Old/Existing: ID {d1['id']} (GP: {d1['gp_serial']}, Name: {d1['name']}, EPIC: {d1['epic_id']}, Photo: {d1['photo_path']})")
    print(f"  Duplicate:    ID {d2['id']} (GP: {d2['gp_serial']}, Name: {d2['name']}, EPIC: {d2['epic_id']}, Photo: {d2['photo_path']})")
    print("-" * 50)
