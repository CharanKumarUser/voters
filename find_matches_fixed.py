import sqlite3
import json
import re

with open('extracted_593.json') as f:
    cards = json.load(f)

card_epics = {}
card_7digs = {}
for card in cards:
    ep = card['epic_id'].strip().upper()
    card_epics[ep] = card
    m = re.search(r'(\d{7})', ep)
    if m:
        card_7digs[m.group(1)] = card

conn = sqlite3.connect('voters.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()
c.execute('SELECT id, serial_no, name, gender, relation_type, relation_name, epic_id FROM voters WHERE gp_serial IS NULL')
unlinked = c.fetchall()

print(f"Checking {len(unlinked)} unlinked voters:")
matched_count = 0
for v in unlinked:
    orig = v['epic_id']
    fixed = orig.replace('UXNO', 'UXN0')
    m = re.search(r'(\d{7})', fixed)
    digs = m.group(1) if m else ''
    
    matched_card = None
    reason = ''
    if fixed in card_epics:
        matched_card = card_epics[fixed]
        reason = 'Exact fixed EPIC'
    elif digs and digs in card_7digs:
        matched_card = card_7digs[digs]
        reason = f'7 digits ({digs})'
        
    if matched_card:
        gp_s = matched_card['gp_serial']
        c.execute('SELECT id, serial_no, name, gender, epic_id FROM voters WHERE gp_serial = ?', (gp_s,))
        curr = c.fetchone()
        curr_name = curr['name'] if curr else 'None'
        curr_gender = curr['gender'] if curr else 'None'
        print(f"Voter #{v['serial_no']} {v['name']} ({v['gender']}) -> Card GP#{gp_s} ({reason}) | Currently in DB: {curr_name} ({curr_gender})")
        matched_count += 1
    else:
        print(f"Voter #{v['serial_no']} {v['name']} ({v['gender']}) [{orig}] -> No match")

print(f"\nTotal matched out of 27: {matched_count}")
