import sqlite3
import json

with open('extracted_593.json') as f:
    cards = json.load(f)

card_map = {c['gp_serial']: c for c in cards}

conn = sqlite3.connect('voters.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()
c.execute("SELECT gp_serial, epic_id, name, relation_type, relation_name, house_no, gender FROM voters ORDER BY gp_serial ASC")
db_voters = {r['gp_serial']: dict(r) for r in c.fetchall()}

import populate_db_final
t_keys = set(populate_db_final.transliterated_new_voters.keys())

print(f"Total in DB: {len(db_voters)}")
print(f"Total in transliterated_new_voters: {len(t_keys)}")

matched_samples = [s for s in sorted(db_voters.keys()) if s not in t_keys][:20]
print("\n--- SAMPLE MATCHES FROM PART 159 ---")
for s in matched_samples:
    v = db_voters[s]
    c_card = card_map[s]
    print(f"GP#{s:3d} | DB EPIC: {v['epic_id']:10s} | Card EPIC: {c_card['epic_id']:10s} | Name: {v['name']:20s} | Rel: {v['relation_type']:7s} {v['relation_name']:18s} | House: {v['house_no']}")
