import json
import sqlite3
import re
import cv2
from rapidocr_onnxruntime import RapidOCR

engine = RapidOCR()
conn = sqlite3.connect('voters.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()
c.execute("SELECT gp_serial, epic_id, name, relation_type, relation_name, house_no, gender FROM voters ORDER BY gp_serial ASC")
db_voters = {r['gp_serial']: dict(r) for r in c.fetchall()}

print(f"Scanning bottom line of all 593 card crops for printed EPIC ID...")

mismatches = []
ocr_results = {}

for s in range(1, 594):
    card_path = f"static/crops/card_gp_{s:04d}.jpg"
    img = cv2.imread(card_path)
    if img is None:
        continue
    
    # Bottom strip has: "ఓటరు ఐడి. కార్డు నెం. : UXN1234567"
    # Usually in y: 235 to 300, x: 0 to 600
    bot = img[230:303, 0:600]
    res, _ = engine(bot)
    text = ' '.join(r[1] for r in (res or []))
    
    # Look for 3 letters + 7 digits or just 7 digits
    m = re.search(r'([A-Z0-9]{3}\s*\d{7})', text)
    if not m:
        m = re.search(r'(\d{7})', text)
        
    card_epic = m.group(1).replace(' ', '') if m else ''
    ocr_results[s] = card_epic
    
    db_v = db_voters.get(s, {})
    db_epic = db_v.get('epic_id', '')
    
    # Check digits match
    card_digits = ''.join(ch for ch in card_epic if ch.isdigit())
    db_digits = ''.join(ch for ch in db_epic if ch.isdigit())
    
    if card_digits and db_digits and card_digits != db_digits:
        mismatches.append({
            'gp_serial': s,
            'card_epic': card_epic,
            'db_epic': db_epic,
            'db_name': db_v.get('name'),
            'db_gender': db_v.get('gender')
        })

print(f"\nTotal mismatched EPIC cards: {len(mismatches)}")
for m in mismatches:
    print(m)
