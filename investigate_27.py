import sqlite3
import json
import re

with open('extracted_593.json') as f:
    cards = json.load(f)

card_by_serial = {c['gp_serial']: c for c in cards}
card_epics = {c['epic_id'].strip().upper(): c for c in cards}

conn = sqlite3.connect('voters.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()

c.execute('SELECT * FROM voters WHERE gp_serial IS NULL')
unlinked = c.fetchall()

print(f"Investigating all {len(unlinked)} unlinked voters:")

for v in unlinked:
    epic = v['epic_id'].strip().upper()
    # Normalize O to 0, fix common typos
    norm_epic = epic.replace('UXNO', 'UXN0').replace('CWBO', 'CWB0')
    # Try digits
    m = re.search(r'(\d+)', norm_epic)
    digs = m.group(1) if m else ''
    
    # Check if this voter matches any card in extracted_593.json
    matched = None
    for c_epic, card in card_epics.items():
        c_norm = c_epic.replace('UXNO', 'UXN0')
        if norm_epic == c_norm or (len(digs) >= 6 and digs in c_norm):
            matched = card
            break
            
    print(f"Voter #{v['serial_no']:3d}: Name='{v['name']}', Gender='{v['gender']}', EPIC='{epic}'")
    if matched:
        gp_s = matched['gp_serial']
        c.execute('SELECT * FROM voters WHERE gp_serial = ?', (gp_s,))
        db_curr = c.fetchone()
        print(f"   -> MATCHES GP#{gp_s} (Card EPIC: {matched['epic_id']})")
        if db_curr:
            print(f"      Current DB Voter for GP#{gp_s}: ID:{db_curr['id']} Name='{db_curr['name']}', Gender='{db_curr['gender']}', EPIC='{db_curr['epic_id']}'")
    else:
        print(f"   -> No match found in 593 cards.")
