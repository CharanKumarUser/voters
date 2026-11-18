import os
import re
import cv2
import pymupdf
import numpy as np
import sqlite3
import time
from concurrent.futures import ProcessPoolExecutor
from rapidocr_onnxruntime import RapidOCR

PDF_PATH = 'voters-new.pdf'
DB_PATH = 'voters.db'

col_xs = [114, 856, 1596]
card_w = 731
p1_rows = [582, 875, 1176, 1479, 1779, 2081, 2383, 2683, 2984, 3285]
other_rows = [379, 671, 971, 1272, 1575, 1875, 2176, 2477, 2777, 3077]

def worker_page(p_idx):
    engine = RapidOCR()
    doc = pymupdf.open(PDF_PATH)
    p = doc[p_idx]
    pix = p.get_pixmap()
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape((pix.h, pix.w, pix.n))
    if pix.n == 4:
        img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
    elif pix.n == 3:
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

    rows = p1_rows if p_idx == 0 else other_rows
    voters = []

    for r_idx in range(9):
        y1 = rows[r_idx]
        y2 = rows[r_idx + 1]
        for c_idx in range(3):
            serial = (p_idx * 27) + (r_idx * 3) + c_idx + 1
            if serial > 593:
                break
            x1 = col_xs[c_idx]
            x2 = x1 + card_w
            card = img[y1:y2, x1:x2]

            # 1. EPIC ID from bottom strip (card[200:card.shape[0], 0:560])
            bottom = card[200:card.shape[0], 0:560]
            res_bot, _ = engine(bottom)
            text_bot = ' '.join([r[1] for r in res_bot]) if res_bot else ''
            m = re.search(r'([A-Z]{3}\d{7})', text_bot)
            if not m:
                m = re.search(r'([A-Z0-9]{10})', text_bot)
            epic = m.group(1) if m else f'GP{serial:04d}'

            # 2. Extract House No and AC/Part info
            top_mid = card[0:200, 0:560]
            res_top, _ = engine(top_mid)
            text_top = ' '.join([r[1] for r in res_top]) if res_top else ''
            
            # AC-Part-Serial
            m_ac = re.search(r'175\s*[-–]\s*(\d{3})\s*[-–]\s*(\d+)', text_top)
            part_no = m_ac.group(1) if m_ac else '132'
            ac_serial = int(m_ac.group(2)) if m_ac else None

            # House number: e.g. 1-1, 2-15, etc.
            m_house = re.search(r'[:\s]*(\d+[-\w\/]*)', text_top)
            house = m_house.group(1) if m_house else ''

            voters.append({
                'gp_serial': serial,
                'epic_id': epic,
                'part_no': part_no,
                'ac_serial': ac_serial,
                'house_no': house,
                'page_no': p_idx + 1
            })

    return p_idx + 1, voters

if __name__ == '__main__':
    t0 = time.time()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT epic_id FROM voters')
    db_epics = set(r[0] for r in c.fetchall() if r[0])
    conn.close()

    print(f'Starting scan of 23 pages (593 voters)... DB has {len(db_epics)} voters.')
    all_voters = []
    with ProcessPoolExecutor(max_workers=4) as executor:
        for p_no, voters in executor.map(worker_page, range(23)):
            all_voters.extend(voters)
            print(f'Page {p_no}/23 processed ({len(voters)} voters)')

    matched = [v for v in all_voters if v['epic_id'] in db_epics]
    unmatched = [v for v in all_voters if v['epic_id'] not in db_epics]

    print(f'Scan done in {round(time.time() - t0, 1)}s')
    print(f'Total cards: {len(all_voters)}')
    print(f'Matched existing DB: {len(matched)}')
    print(f'Unmatched (New Voters): {len(unmatched)}')
    print('Sample unmatched voters:', unmatched[:10])
