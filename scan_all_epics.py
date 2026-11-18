import cv2
import pymupdf
import numpy as np
import re
import sqlite3
from rapidocr_onnxruntime import RapidOCR

PDF_PATH = 'voters-new.pdf'
doc = pymupdf.open(PDF_PATH)
engine = RapidOCR()

conn = sqlite3.connect('voters.db')
c = conn.cursor()
c.execute('SELECT epic_id FROM voters WHERE epic_id != ""')
existing_epics = set(r[0].strip() for r in c.fetchall())
conn.close()

print(f'Total existing EPICs in voters.db: {len(existing_epics)}')

col_xs = [114, 856, 1596]
card_w = 731

p1_rows = [582, 875, 1176, 1479, 1779, 2081, 2383, 2683, 2984, 3285]
other_rows = [379, 671, 971, 1272, 1575, 1875, 2176, 2477, 2777, 3077]

total_cards = 0
found_epics = {}
new_epics_list = []

for p_idx in range(23):
    p = doc[p_idx]
    pix = p.get_pixmap()
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape((pix.h, pix.w, pix.n))
    if pix.n == 4:
        img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
    elif pix.n == 3:
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

    rows = p1_rows if p_idx == 0 else other_rows

    for r_idx in range(9):
        y1 = rows[r_idx]
        y2 = rows[r_idx + 1]
        for c_idx in range(3):
            total_cards += 1
            serial = total_cards
            if serial > 593:
                break
            x1 = col_xs[c_idx]
            x2 = x1 + card_w

            card = img[y1:y2, x1:x2]
            bottom = card[200:card.shape[0], 0:560]
            res, _ = engine(bottom)
            text = ' '.join([r[1] for r in res]) if res else ''
            m = re.search(r'([A-Z]{3}\d{7}|[A-Z0-9]{10})', text)
            epic = m.group(1) if m else f'UNKNOWN_{serial:04d}'

            found_epics[serial] = epic
            if epic in existing_epics:
                pass
            else:
                new_epics_list.append((serial, epic, p_idx + 1))

    print(f'Page {p_idx+1}/23 processed. Cards: {total_cards}, Unique matched so far: {total_cards - len(new_epics_list)}')

print(f'Done! Total scanned: {total_cards}, Matched: {total_cards - len(new_epics_list)}, New: {len(new_epics_list)}')
print('First 10 new voters (serial, epic, page):', new_epics_list[:10])
