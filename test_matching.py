import cv2
import pymupdf
import numpy as np
import re
import sqlite3
from rapidocr_onnxruntime import RapidOCR

doc = pymupdf.open('voters-new.pdf')
engine = RapidOCR()

conn = sqlite3.connect('voters.db')
c = conn.cursor()
c.execute('SELECT epic_id, name, relation_name, house_no, age, gender FROM voters')
db_voters = {r[0]: dict(name=r[1], relation=r[2], house_no=r[3], age=r[4], gender=r[5]) for r in c.fetchall() if r[0]}
conn.close()

print(f'Existing voters in DB: {len(db_voters)}')

col_xs = [114, 856, 1596]
card_w = 731
card_h = 303
row_y0 = 385
row_step = 303.5

matched = 0
new_epics = []

# Test first 3 pages
for p_idx in range(3):
    p = doc[p_idx]
    pix = p.get_pixmap()
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape((pix.h, pix.w, pix.n))
    if pix.n == 4:
        img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
    elif pix.n == 3:
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

    for row in range(9):
        for col in range(3):
            y1 = int(row_y0 + row * row_step)
            y2 = int(y1 + card_h)
            x1 = col_xs[col]
            x2 = x1 + card_w
            card = img[y1:y2, x1:x2]

            # Bottom region for EPIC ID
            bottom = card[220:303, 10:560]
            res, _ = engine(bottom)
            text = ' '.join([r[1] for r in res]) if res else ''
            m = re.search(r'([A-Z]{3}[0-9]{7})', text)
            if not m:
                m = re.search(r'([A-Z0-9]{10})', text)
            epic = m.group(1) if m else None

            if epic:
                if epic in db_voters:
                    matched += 1
                else:
                    new_epics.append(epic)

print(f'First 3 pages (81 cards): Matched={matched}, New={len(new_epics)}')
print('Sample new EPICs:', new_epics[:5])
