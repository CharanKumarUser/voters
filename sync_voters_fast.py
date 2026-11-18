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
PHOTOS_DIR = os.path.join('static', 'photos')
CROPS_DIR = os.path.join('static', 'crops')
os.makedirs(PHOTOS_DIR, exist_ok=True)
os.makedirs(CROPS_DIR, exist_ok=True)

col_xs = [114, 856, 1596]
card_w = 731
p1_rows = [582, 875, 1176, 1479, 1779, 2081, 2383, 2683, 2984, 3285]
other_rows = [379, 671, 971, 1272, 1575, 1875, 2176, 2477, 2777, 3077]
header_pages = {0, 5, 10, 15, 20}
short_pages = {4, 9, 14, 19}

# Starting serial for each page
page_starts = {
    0: 1,    1: 28,   2: 55,   3: 82,   4: 109,
    5: 129,  6: 156,  7: 183,  8: 210,  9: 237,
    10: 257, 11: 284, 12: 311, 13: 338, 14: 365,
    15: 385, 16: 412, 17: 439, 18: 466, 19: 493,
    20: 513, 21: 540, 22: 567
}

def get_ward(serial):
    if serial <= 128: return 1
    elif serial <= 256: return 2
    elif serial <= 384: return 3
    elif serial <= 512: return 4
    else: return 5

def process_page(p_idx):
    engine = RapidOCR()
    doc = pymupdf.open(PDF_PATH)
    p = doc[p_idx]
    pix = p.get_pixmap()
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape((pix.h, pix.w, pix.n))
    if pix.n == 4:
        img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
    elif pix.n == 3:
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

    rows = p1_rows if p_idx in header_pages else other_rows
    max_r = 7 if p_idx in short_pages else 9
    
    current_serial = page_starts[p_idx]
    voters = []

    for r in range(max_r):
        cols_in_row = 2 if (p_idx in short_pages and r == 6) else 3
        for c in range(cols_in_row):
            gp_s = current_serial
            current_serial += 1
            if gp_s > 593:
                break

            y1 = rows[r]
            y2 = rows[r+1]
            x1 = col_xs[c]
            x2 = x1 + card_w
            card = img[y1:y2, x1:x2]

            # 1. High-clarity native photo (164x180 px at 300 DPI)
            photo = card[105:285, 558:722]

            # 2. Extract EPIC ID from bottom strip
            bottom = card[200:card.shape[0], 0:560]
            res, _ = engine(bottom)
            text_bot = ' '.join([item[1] for item in (res or [])])
            m = re.search(r'([A-Z]{3}\d{7})', text_bot)
            if not m:
                m = re.search(r'([A-Z0-9]{10})', text_bot)
            epic = m.group(1) if m else f'GP{gp_s:04d}'

            # 3. Extract House No from card
            m_house = re.search(r'[:\s]*(\d+[-\w\/]*)', text_bot)
            house = m_house.group(1) if m_house else ''

            # 4. Save photo file
            photo_file = f'photo_gp_{gp_s:04d}.jpg'
            cv2.imwrite(os.path.join(PHOTOS_DIR, photo_file), photo, [cv2.IMWRITE_JPEG_QUALITY, 98])
            if epic and not epic.startswith('GP'):
                cv2.imwrite(os.path.join(PHOTOS_DIR, f'{epic}.jpg'), photo, [cv2.IMWRITE_JPEG_QUALITY, 98])

            # 5. Save card crop file
            card_file = f'card_gp_{gp_s:04d}.jpg'
            cv2.imwrite(os.path.join(CROPS_DIR, card_file), card, [cv2.IMWRITE_JPEG_QUALITY, 95])

            voters.append({
                'gp_serial': gp_s,
                'epic_id': epic,
                'house_no': house,
                'ward': get_ward(gp_s),
                'photo_path': f'/static/photos/{photo_file}',
                'crop_path': f'/static/crops/{card_file}',
                'page_no': p_idx + 1
            })

    return p_idx + 1, voters

if __name__ == '__main__':
    t0 = time.time()
    print('Starting 4-Worker parallel extraction across Pages 1 to 23 (593 voters)...')
    all_voters = []
    with ProcessPoolExecutor(max_workers=4) as executor:
        for p_no, vlist in executor.map(process_page, range(23)):
            all_voters.extend(vlist)
            print(f'Page {p_no:02d}/23 done ({len(vlist)} cards, cumulative: {len(all_voters)})')

    all_voters.sort(key=lambda x: x['gp_serial'])
    print(f'Done in {time.time()-t0:.1f}s! Total cards extracted: {len(all_voters)}')
    print(f'First serial: {all_voters[0]["gp_serial"]}, Last serial: {all_voters[-1]["gp_serial"]}')

    # Save extracted info to a json for quick access
    import json
    with open('extracted_593.json', 'w') as f:
        json.dump(all_voters, f, indent=2)
    print('Saved extracted_593.json')
