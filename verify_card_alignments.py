import sqlite3
import cv2
import re
from rapidocr_onnxruntime import RapidOCR

engine = RapidOCR()
conn = sqlite3.connect('voters.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()

c.execute('SELECT * FROM voters WHERE gp_serial IS NOT NULL ORDER BY gp_serial ASC')
voters = c.fetchall()

print(f"Auditing all {len(voters)} GP voters for photo-card-name alignment...")

mismatches = []
for v in voters:
    gp_s = v['gp_serial']
    card_path = f"static/crops/card_gp_{gp_s:04d}.jpg"
    img = cv2.imread(card_path)
    if img is None: continue
    
    # Read name area: y: 100 to 160, x: 10 to 520
    name_crop = img[100:160, 10:520]
    res, _ = engine(name_crop)
    t_name = ' '.join(r[1] for r in (res or []))

    # Read relation area: y: 150 to 215, x: 10 to 520
    rel_crop = img[150:215, 10:520]
    res_rel, _ = engine(rel_crop)
    t_rel = ' '.join(r[1] for r in (res_rel or []))

    # Check relation type in Telugu:
    # భర్త / భర్త పేరు = Husband (Female voter)
    # తండ్రి / తండ్రి పేరు = Father
    # తల్లి / తల్లి పేరు = Mother
    
    # Check if DB gender is Male, but relation text indicates Husband
    # (In RapidOCR on Telugu, భర్త often produces specific patterns)
    # But even better: let's check house number on card vs DB house number!
    # If house number on card doesn't match DB house number, it was assigned to the WRONG card!
    house_crop = img[200:260, 10:400]
    res_h, _ = engine(house_crop)
    t_h = ' '.join(r[1] for r in (res_h or []))
    
    m_h = re.search(r'[:\s]*(\d+[-\w\/]*)', t_h)
    card_house = m_h.group(1) if m_h else ''
    
    db_house = str(v['house_no']).strip()
    
    # Also check EPIC ID printed on the bottom line
    bot_crop = img[245:295, 10:480]
    res_b, _ = engine(bot_crop)
    t_b = ' '.join(r[1] for r in (res_b or []))
    m_epic = re.search(r'([A-Z0-9]{3}\d{7})', t_b)
    card_epic = m_epic.group(1) if m_epic else ''

    if card_epic and v['epic_id'] and not card_epic.endswith(v['epic_id'][-7:]):
        mismatches.append({
            'gp_serial': gp_s,
            'db_name': v['name'],
            'db_epic': v['epic_id'],
            'card_epic': card_epic,
            'db_house': db_house,
            'card_house': card_house
        })

print(f"\nFound {len(mismatches)} cards where card EPIC digits != DB EPIC:")
for m in mismatches:
    print(" ", m)
