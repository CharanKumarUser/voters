import json
import sqlite3
import re
from rapidocr_onnxruntime import RapidOCR

with open('extracted_593.json') as f:
    data = json.load(f)

conn = sqlite3.connect('voters.db')
c = conn.cursor()
c.execute('SELECT epic_id FROM voters')
db_epics = {r[0]: r[0] for r in c.fetchall() if r[0]}
suffix_map = {epic[-7:]: epic for epic in db_epics if len(epic) >= 7}

engine = RapidOCR()

matched_before = sum(1 for v in data if v['epic_id'] in db_epics)
newly_matched = 0

for v in data:
    orig = v['epic_id']
    if orig not in db_epics:
        # 1. Check if orig has 7 digits that match suffix_map
        m = re.search(r'(\d{7})', orig)
        if m and m.group(1) in suffix_map:
            v['epic_id'] = suffix_map[m.group(1)]
            newly_matched += 1
            continue

        # 2. Re-OCR the card bottom with high precision
        card_path = f"static/crops/card_gp_{v['gp_serial']:04d}.jpg"
        res, _ = engine(card_path)
        text = ' '.join(r[1] for r in (res or []))
        
        # Look for UXN / CWB or any 7 digits
        m_7 = re.search(r'(\d{7})', text)
        if m_7 and m_7.group(1) in suffix_map:
            v['epic_id'] = suffix_map[m_7.group(1)]
            newly_matched += 1
            continue

        m_any = re.search(r'([A-Z0-9]{3}\d{7})', text)
        if m_any:
            raw_epic = m_any.group(1)
            # Fix leading char
            fixed = 'UXN' + raw_epic[3:]
            if fixed in db_epics:
                v['epic_id'] = fixed
                newly_matched += 1
            elif raw_epic in db_epics:
                v['epic_id'] = raw_epic
                newly_matched += 1

print(f'Matched before: {matched_before}')
print(f'Newly matched: {newly_matched}')
total_m = sum(1 for v in data if v['epic_id'] in db_epics)
print(f'Total matched now: {total_m} / 593')
print(f'Remaining unmatched: {593 - total_m}')

with open('extracted_593.json', 'w') as f:
    json.dump(data, f, indent=2)
