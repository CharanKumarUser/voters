import json
import sqlite3
import re

with open('extracted_593.json') as f:
    cards = json.load(f)

# The 27 voters with gp_serial IS NULL
conn = sqlite3.connect('voters.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()
c.execute('SELECT * FROM voters WHERE gp_serial IS NULL')
missing_voters = c.fetchall()

print(f"Checking if any of the {len(missing_voters)} voters exist in voters-new.pdf...")

card_epics = {c['epic_id']: c for c in cards}
card_digits = {re.search(r'(\d{7})', c['epic_id']).group(1): c for c in cards if re.search(r'(\d{7})', c['epic_id'])}

matched = []
unmatched = []

for v in missing_voters:
    epic = v['epic_id']
    m = re.search(r'(\d{7})', epic)
    digits = m.group(1) if m else ''
    
    if epic in card_epics:
        matched.append((v, card_epics[epic], 'Direct EPIC match'))
    elif digits in card_digits:
        matched.append((v, card_digits[digits], '7-digit match'))
    else:
        unmatched.append(v)

print(f"Matched in voters-new.pdf: {len(matched)}")
for v, card, reason in matched:
    print(f"  Voter #{v['serial_no']} {v['name']} -> Found in Card GP#{card['gp_serial']} ({reason})")

print(f"\nTruly not in voters-new.pdf: {len(unmatched)}")
for v in unmatched:
    print(f"  Voter #{v['serial_no']} {v['name']} ({v['epic_id']})")
