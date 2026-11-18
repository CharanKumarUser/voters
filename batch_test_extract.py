import cv2
import pymupdf
import numpy as np
import re
import sqlite3
import os
from rapidocr_onnxruntime import RapidOCR

PDF_PATH = 'voters-new.pdf'
PHOTOS_DIR = os.path.join('static', 'photos')
CROPS_DIR = os.path.join('static', 'crops_new')
os.makedirs(PHOTOS_DIR, exist_ok=True)
os.makedirs(CROPS_DIR, exist_ok=True)

# Grid parameters
col_xs = [114, 856, 1596]
card_w = 731
card_h = 303
row_y0 = 385
row_step = 303.5

doc = pymupdf.open(PDF_PATH)
engine = RapidOCR()

conn = sqlite3.connect('voters.db')
c = conn.cursor()
c.execute('SELECT epic_id, name, relation_type, relation_name, house_no, age, gender FROM voters')
db_voters = {r[0]: dict(name=r[1], relation_type=r[2], relation_name=r[3], house_no=r[4], age=r[5], gender=r[6]) for r in c.fetchall() if r[0]}
conn.close()

print(f'Existing voters in DB: {len(db_voters)}')

# Test pages 1 to 5
total_processed = 0
matched_count = 0
new_count = 0

for p_idx in range(5):
    p = doc[p_idx]
    pix = p.get_pixmap()
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape((pix.h, pix.w, pix.n))
    if pix.n == 4:
        img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
    elif pix.n == 3:
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

    for row in range(9):
        for col in range(3):
            total_processed += 1
            serial = total_processed
            y1 = int(row_y0 + row * row_step)
            y2 = int(y1 + card_h)
            x1 = col_xs[col]
            x2 = x1 + card_w
            card = img[y1:y2, x1:x2]

            # Save full card
            cv2.imwrite(os.path.join(CROPS_DIR, f'card_new_{serial:04d}.jpg'), card, [cv2.IMWRITE_JPEG_QUALITY, 95])

            # Extract Photo with high clarity
            photo = card[105:285, 558:722]

            # Extract EPIC
            bottom = card[190:303, 0:560]
            res, _ = engine(bottom)
            text = ' '.join([r[1] for r in res]) if res else ''
            
            # Match EPIC regex
            m = re.search(r'([A-Z]{3}\d{7})', text)
            if not m:
                m = re.search(r'([A-Z0-9]{10})', text)
            epic = m.group(1) if m else f'NEW{serial:04d}'

            # Save photo by EPIC and by serial
            photo_file = f'{epic}.jpg'
            cv2.imwrite(os.path.join(PHOTOS_DIR, photo_file), photo, [cv2.IMWRITE_JPEG_QUALITY, 98])
            cv2.imwrite(os.path.join(PHOTOS_DIR, f'photo_new_{serial:04d}.jpg'), photo, [cv2.IMWRITE_JPEG_QUALITY, 98])

            if epic in db_voters:
                matched_count += 1
            else:
                new_count += 1

print(f'Pages 1-5 (135 voters): Matched={matched_count}, New={new_count}')
