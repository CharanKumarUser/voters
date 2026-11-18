import json
import re
import sqlite3
from rapidocr_onnxruntime import RapidOCR

with open('extracted_593.json') as f:
    data = json.load(f)

gp_cards = [v for v in data if v['epic_id'].startswith('GP')]
print(f'Total cards with GP fallback: {len(gp_cards)}')

engine = RapidOCR()
recovered = 0
for v in gp_cards:
    crop_file = f"static/crops/card_gp_{v['gp_serial']:04d}.jpg"
    res, _ = engine(crop_file)
    text = ' '.join(r[1] for r in (res or []))
    m = re.search(r'([A-Z]{3}\d{7})', text)
    if not m:
        m = re.search(r'([A-Z0-9]{10})', text)
    if m:
        v['epic_id'] = m.group(1)
        recovered += 1

print(f'Recovered {recovered} out of {len(gp_cards)} EPIC IDs!')

conn = sqlite3.connect('voters.db')
c = conn.cursor()
c.execute('SELECT epic_id FROM voters')
db_epics = set(r[0] for r in c.fetchall() if r[0])
conn.close()

matched = [v for v in data if v['epic_id'] in db_epics]
print(f'Total extracted: {len(data)}, Total matched with DB: {len(matched)}')
print(f'Remaining unmatched: {len(data) - len(matched)}')

with open('extracted_593.json', 'w') as f:
    json.dump(data, f, indent=2)
print('Updated extracted_593.json')
