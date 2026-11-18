import json
import sqlite3
import re
from rapidocr_onnxruntime import RapidOCR

with open('extracted_593.json') as f:
    data = json.load(f)

conn = sqlite3.connect('voters.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()
c.execute('SELECT * FROM voters')
db_by_serial = {r['serial_no']: dict(r) for r in c.fetchall()}
db_by_epic = {r['epic_id']: dict(r) for r in c.fetchall() if r['epic_id']}

unmatched = [v for v in data if v['epic_id'] not in db_by_epic]
print('Unmatched count:', len(unmatched))

engine = RapidOCR()
for v in unmatched[:6]:
    gp = v['gp_serial']
    crop_file = f'static/crops/card_gp_{gp:04d}.jpg'
    res, _ = engine(crop_file)
    t = ' '.join(r[1] for r in (res or []))
    m = re.search(r'175\s*[-–]\s*(\d{3})\s*[-–]\s*(\d+)', t)
    if m:
        part, s_no = m.group(1), int(m.group(2))
        db_match = db_by_serial.get(s_no, {})
        print(f"GP#{gp}: Part {part}, Serial {s_no} -> DB Name: {db_match.get('name')}, EPIC: {db_match.get('epic_id')}")
    else:
        print(f"GP#{gp}: No assembly match found")
