import json
import sqlite3
import re
import os
import cv2
from rapidocr_onnxruntime import RapidOCR

engine = RapidOCR()
conn = sqlite3.connect('voters.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()

c.execute('SELECT * FROM voters WHERE gp_serial IS NOT NULL ORDER BY gp_serial ASC')
voters = c.fetchall()

print(f"Checking {len(voters)} voters with GP serial...")

mismatches = []
missing_photos = []

for v in voters:
    gp_s = v['gp_serial']
    photo_file = f"static/photos/photo_gp_{gp_s:04d}.jpg"
    card_file = f"static/crops/card_gp_{gp_s:04d}.jpg"
    
    # 1. Check if photo file exists and is not blank
    if not os.path.exists(photo_file):
        missing_photos.append((gp_s, v['name'], 'File missing'))
        continue
    
    img_photo = cv2.imread(photo_file)
    if img_photo is None or img_photo.size == 0:
        missing_photos.append((gp_s, v['name'], 'Unreadable image'))
        continue

    # Check if photo is blank / pure white / empty box
    gray = cv2.cvtColor(img_photo, cv2.COLOR_BGR2GRAY)
    std = gray.std()
    if std < 12.0:
        missing_photos.append((gp_s, v['name'], f'Blank/Empty photo box (std={std:.1f})'))

    # 2. Check EPIC on card vs EPIC in DB
    if os.path.exists(card_file):
        img_card = cv2.imread(card_file)
        bot_strip = img_card[240:298, 10:480]
        res, _ = engine(bot_strip)
        t = ' '.join(r[1] for r in (res or []))
        
        # Extract digits
        m_num = re.search(r'(\d{7})', t)
        card_num = m_num.group(1) if m_num else None
        
        db_epic = v['epic_id'] or ''
        db_num = re.search(r'(\d{7})', db_epic)
        db_digits = db_num.group(1) if db_num else None

        if card_num and db_digits and card_num != db_digits:
            mismatches.append({
                'gp_serial': gp_s,
                'db_name': v['name'],
                'db_gender': v['gender'],
                'db_epic': db_epic,
                'card_epic_digits': card_num,
                'card_text': t
            })

print(f"\nMissing / Blank Photos: {len(missing_photos)}")
for mp in missing_photos[:15]:
    print(" ", mp)

print(f"\nEPIC Mismatches (Wrong voter assigned to GP serial!): {len(mismatches)}")
for mm in mismatches[:20]:
    print(" ", mm)
