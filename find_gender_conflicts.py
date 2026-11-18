import json
import sqlite3
import re
import cv2
from rapidocr_onnxruntime import RapidOCR

engine = RapidOCR()
conn = sqlite3.connect('voters.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()

c.execute('SELECT * FROM voters WHERE gp_serial IS NOT NULL')
voters = {r['gp_serial']: dict(r) for r in c.fetchall()}

print(f"Auditing gender consistency across {len(voters)} cards...")

conflicts = []

for gp_s, v in sorted(voters.items()):
    card_file = f"static/crops/card_gp_{gp_s:04d}.jpg"
    img = cv2.imread(card_file)
    if img is None: continue
    
    # OCR middle relation area
    rel_area = img[130:220, 10:400]
    res, _ = engine(rel_area)
    t = ' '.join(r[1] for r in (res or []))
    
    # In Telugu: భర్త (Husband) -> means voter is a married WOMAN (Female)!
    # RapidOCR might read భర్త as specific characters or symbols
    # But let's check Telugu unicode if possible, or check:
    # Does the card photo look male/female, or does DB gender match?
    
    # Also check if the DB name has female suffixes like -AMMA, -DEVI, -KUMARI, -LATHA, -BAI, -MANI, -THI
    # while DB gender is 'Male', OR vice versa (name ends with -APPA, -RAJU, -CHARI, -REDDY, -GOWDA, -PRASAD, -KUMAR while gender is 'Female')!
    name = v['name'].upper()
    g = v['gender']

    female_indicators = ['AMMA', 'DEVI', 'KUMARI', 'LATHA', 'LATHAA', 'BHAGYA', 'RADHA', 'SHOBHA', 'PARVATHI', 'LAKSHMI', 'SARASWATHI', 'GOWRI', 'RANI', 'PUSHPA', 'VANI', 'ROOPA', 'MADHU', 'SHILPA', 'CHANDRAKALA', 'MAMATHA', 'SWATHI', 'SUJATHA', 'KAVITHA', 'BHAVANI', 'PADMA']
    male_indicators = ['APPA', 'RAJU', 'REDDY', 'NAIDU', 'GOWD', 'KUMAR', 'CHARI', 'SWAMY', 'PRASAD', 'BABU', 'VARMA', 'MURTHY', 'RAMAN', 'RAMA', 'MOHAN', 'SHANKAR', 'SHEKAR', 'VENKATESH', 'KRISHNA']

    is_female_name = any(re.search(r'\b' + ind + r'\b|' + ind + r'$', name) for ind in female_indicators)
    is_male_name = any(re.search(r'\b' + ind + r'\b|' + ind + r'$', name) for ind in male_indicators)

    if is_female_name and g == 'Male':
        conflicts.append((gp_s, v['name'], g, 'Female Name marked as Male in DB', v['epic_id']))
    elif is_male_name and g == 'Female' and not any(f in name for f in female_indicators):
        conflicts.append((gp_s, v['name'], g, 'Male Name marked as Female in DB', v['epic_id']))

print(f"\nFound {len(conflicts)} Gender-Name discrepancies in DB:")
for conf in conflicts[:30]:
    print(" ", conf)
