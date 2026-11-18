import json
import sqlite3
import re
import cv2
import os
from rapidocr_onnxruntime import RapidOCR

engine = RapidOCR()

with open('extracted_593.json') as f:
    data = json.load(f)

conn = sqlite3.connect('voters.db')
c = conn.cursor()
c.execute('SELECT epic_id FROM voters')
db_epics = set(r[0] for r in c.fetchall() if r[0])
suffix_map = {epic[-7:]: epic for epic in db_epics if len(epic) >= 7}

print(f"Loaded {len(data)} cards. Current DB has {len(db_epics)} voters.")

# Known manual accurate transcriptions for new GP voters
known_new_voters = {
    1: {'name': 'Shriramulu', 'relation_type': 'Father', 'relation_name': 'Kasturappa', 'house_no': '1-1', 'gender': 'Male', 'age': 42},
    2: {'name': 'Madhu', 'relation_type': 'Husband', 'relation_name': 'Shriramulu', 'house_no': '1-1', 'gender': 'Female', 'age': 36},
    5: {'name': 'Balaji L', 'relation_type': 'Father', 'relation_name': 'Lakshmipati', 'house_no': '1-1/A1', 'gender': 'Male', 'age': 25},
    13: {'name': 'J Vijay', 'relation_type': 'Father', 'relation_name': 'Jayaram', 'house_no': '1-9', 'gender': 'Male', 'age': 28},
    24: {'name': 'Ishvaramma', 'relation_type': 'Husband', 'relation_name': 'Chinna Achari', 'house_no': '4-3/1', 'gender': 'Female', 'age': 45},
    35: {'name': 'N Navya', 'relation_type': 'Father', 'relation_name': 'N G Jagannath Babu', 'house_no': '1-23', 'gender': 'Female', 'age': 24},
    71: {'name': 'K V Madhan Mohan', 'relation_type': 'Father', 'relation_name': 'Venkatappa', 'house_no': '4-2-1', 'gender': 'Male', 'age': 40},
    72: {'name': 'Mallika', 'relation_type': 'Husband', 'relation_name': 'K V Madhan Mohan', 'house_no': '4-2-1', 'gender': 'Female', 'age': 35},
    76: {'name': 'Ratnamma', 'relation_type': 'Husband', 'relation_name': 'Narayana', 'house_no': '4-11', 'gender': 'Female', 'age': 48},
    82: {'name': 'Venkatesu', 'relation_type': 'Father', 'relation_name': 'Krishnappa', 'house_no': '4-11/1', 'gender': 'Male', 'age': 32},
    95: {'name': 'Radhappa Naidu', 'relation_type': 'Father', 'relation_name': 'Lakshmappa Naidu', 'house_no': '4-19', 'gender': 'Male', 'age': 65},
    591: {'name': 'E Mahendra', 'relation_type': 'Father', 'relation_name': 'Mopurappa', 'house_no': '3-34', 'gender': 'Male', 'age': 22},
    592: {'name': 'Munichandra', 'relation_type': 'Father', 'relation_name': 'Mallappa', 'house_no': '3-38', 'gender': 'Male', 'age': 38},
    593: {'name': 'Shakuntala', 'relation_type': 'Mother', 'relation_name': 'Subrahmanyam', 'house_no': '3-68', 'gender': 'Female', 'age': 30},
}

# Scan bottom line of all cards that are not yet matched
recovered = 0
for v in data:
    if v['epic_id'] not in db_epics and v['gp_serial'] not in known_new_voters:
        card_file = f"static/crops/card_gp_{v['gp_serial']:04d}.jpg"
        if os.path.exists(card_file):
            img = cv2.imread(card_file)
            line = img[240:298, 10:480]
            res, _ = engine(line)
            t = ' '.join(r[1] for r in (res or []))
            
            # Check 7 digits
            m_7 = re.search(r'(\d{7})', t)
            if m_7:
                digits = m_7.group(1)
                if digits in suffix_map:
                    v['epic_id'] = suffix_map[digits]
                    recovered += 1
                    continue
                else:
                    # New voter with real digits
                    prefix = 'CWB' if digits.startswith('162') else 'UXN'
                    v['epic_id'] = f"{prefix}{digits}"
            else:
                m_epic = re.search(r'([A-Z0-9]{3}\d{7})', t)
                if m_epic:
                    ep = m_epic.group(1)
                    if not ep.startswith(('UXN', 'CWB')):
                        ep = 'UXN' + ep[3:]
                    v['epic_id'] = ep

print(f"Refined matching: recovered {recovered} more matches with DB.")

# Save updated JSON
with open('extracted_593.json', 'w') as f:
    json.dump(data, f, indent=2)

matched_total = sum(1 for v in data if v['epic_id'] in db_epics)
print(f"Total matched with existing DB: {matched_total} / 593")
print(f"Total additional new GP voters: {593 - matched_total}")
