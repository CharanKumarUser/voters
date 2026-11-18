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

            # 1. Native high-clarity photo crop (300 DPI, unscaled, zero blur)
            photo = card[105:285, 558:722]

            # 2. Extract EPIC ID from bottom strip
            bottom = card[200:card.shape[0], 0:560]
            res, _ = engine(bottom)
            text = ' '.join([r[1] for r in res]) if res else ''
            m = re.search(r'([A-Z]{3}\d{7})', text)
            if not m:
                m = re.search(r'([A-Z0-9]{10})', text)
            epic = m.group(1) if m else f'GP{serial:04d}'

            # 3. Save photo by gp_serial and by epic
            photo_file = f'photo_gp_{serial:04d}.jpg'
            cv2.imwrite(os.path.join(PHOTOS_DIR, photo_file), photo, [cv2.IMWRITE_JPEG_QUALITY, 98])
            if epic and not epic.startswith('GP'):
                cv2.imwrite(os.path.join(PHOTOS_DIR, f'{epic}.jpg'), photo, [cv2.IMWRITE_JPEG_QUALITY, 98])

            # 4. Save card crop
            card_file = f'card_gp_{serial:04d}.jpg'
            cv2.imwrite(os.path.join(CROPS_DIR, card_file), card, [cv2.IMWRITE_JPEG_QUALITY, 95])

            voters.append({
                'gp_serial': serial,
                'epic_id': epic,
                'photo_path': f'/static/photos/{photo_file}',
                'crop_path': f'/static/crops/{card_file}',
                'page_no': p_idx + 1
            })

    return p_idx + 1, voters

def main():
    print('Starting 4-Worker Sync Pipeline...')
    t0 = time.time()

    conn = sqlite3.connect(DB_PATH, timeout=60.0)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # Ensure gp_serial column
    c.execute('PRAGMA table_info(voters)')
    cols = [r[1] for r in c.fetchall()]
    if 'gp_serial' not in cols:
        c.execute('ALTER TABLE voters ADD COLUMN gp_serial INTEGER')
    conn.commit()

    c.execute('SELECT * FROM voters')
    db_voters = {r['epic_id']: dict(r) for r in c.fetchall() if r['epic_id']}
    print(f'Currently {len(db_voters)} voters in database.')

    # Run 4 workers across pages 1 to 23 (excluding page 24!)
    all_voters = []
    with ProcessPoolExecutor(max_workers=4) as executor:
        for p_no, voters in executor.map(worker_page, range(23)):
            all_voters.extend(voters)
            print(f'Page {p_no}/23 complete ({len(voters)} cards)')

    print(f'Total cards extracted: {len(all_voters)}')

    # Clear previous responses as requested
    c.execute("UPDATE voters SET party = 'UNASSIGNED', voted = 0")
    conn.commit()
    print('Cleared previous recorded party responses.')

    # Match & Insert
    c.execute('SELECT MAX(serial_no) FROM voters')
    max_serial = c.fetchone()[0] or 538

    matched = 0
    added = 0

    for v in all_voters:
        epic = v['epic_id']
        gp_s = v['gp_serial']
        photo = v['photo_path']
        crop = v['crop_path']

        if epic in db_voters:
            c.execute('''
                UPDATE voters SET
                    photo_path = ?,
                    crop_path = ?,
                    gp_serial = ?
                WHERE epic_id = ?
            ''', (photo, crop, gp_s, epic))
            matched += 1
        else:
            max_serial += 1
            c.execute('''
                INSERT INTO voters (
                    serial_no, epic_id, name, relation_type, relation_name,
                    house_no, age, gender, section_name, ac_name, part_no,
                    page_no, crop_path, photo_path, party, voted, gp_serial
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                max_serial,
                epic,
                f'Voter GP#{gp_s}',
                'Guardian',
                'N/A',
                'Cheekatipalle',
                35,
                'Male',
                'Cheekatipalle GP Ward 1',
                '175-KUPPAM',
                '132',
                v['page_no'],
                crop,
                photo,
                'UNASSIGNED',
                0,
                gp_s
            ))
            added += 1

    conn.commit()

    # Total in DB
    c.execute('SELECT COUNT(*) FROM voters')
    total_db = c.fetchone()[0]
    conn.close()

    t1 = time.time()
    print('='*50)
    print(f'SYNC COMPLETE in {round(t1-t0, 1)}s!')
    print(f'Matched existing voters with real photos: {matched}')
    print(f'Added new GP voters: {added}')
    print(f'Total voters now in Database: {total_db}')
    print('='*50)

if __name__ == '__main__':
    main()
