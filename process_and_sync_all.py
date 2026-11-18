import os
import re
import cv2
import pymupdf
import numpy as np
import sqlite3
import time
from concurrent.futures import ProcessPoolExecutor
from rapidocr_onnxruntime import RapidOCR
from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate

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

def telugu_to_english(text):
    if not text or not text.strip():
        return ''
    try:
        res = transliterate(text.strip(), sanscript.TELUGU, sanscript.ITRANS)
        res = res.replace('~N', 'n').replace('~n', 'n').replace('Sh', 'sh').replace('shh', 'sh').replace('.D', 'd').replace('.N', 'n')
        res = res.replace('Mth', 'nth').replace('Mt', 'nt').replace('Mp', 'mp').replace('Mb', 'mb').replace('M', 'n')
        res = res.replace('aa', 'a').replace('ii', 'i').replace('uu', 'u')
        words = [w.capitalize() for w in res.split()]
        return ' '.join(words)
    except Exception:
        return text.strip()

def process_page_worker(p_idx):
    # p_idx is 0-indexed (0 to 22)
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
    page_voters = []

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

            # 1. High-clarity native photo extraction (164x180 at 300 DPI)
            photo = card[105:285, 558:722]

            # 2. Extract EPIC ID from bottom strip
            bottom = card[200:card.shape[0], 0:560]
            res_bottom, _ = engine(bottom)
            text_bottom = ' '.join([r[1] for r in res_bottom]) if res_bottom else ''
            m = re.search(r'([A-Z]{3}\d{7})', text_bottom)
            if not m:
                m = re.search(r'([A-Z0-9]{10})', text_bottom)
            epic = m.group(1) if m else f'GP{serial:04d}'

            # 3. Extract House No from middle strip
            mid = card[160:220, 0:560]
            res_mid, _ = engine(mid)
            text_mid = ' '.join([r[1] for r in res_mid]) if res_mid else ''
            m_house = re.search(r'[:\s]*(\d+[-\w\/]*)', text_mid)
            house_no = m_house.group(1) if m_house else ''

            # 4. Save photo under epic and serial
            photo_epic_path = os.path.join(PHOTOS_DIR, f'{epic}.jpg')
            photo_serial_path = os.path.join(PHOTOS_DIR, f'photo_gp_{serial:04d}.jpg')
            cv2.imwrite(photo_epic_path, photo, [cv2.IMWRITE_JPEG_QUALITY, 98])
            cv2.imwrite(photo_serial_path, photo, [cv2.IMWRITE_JPEG_QUALITY, 98])

            # 5. Save full card crop
            card_crop_path = os.path.join(CROPS_DIR, f'card_gp_{serial:04d}.jpg')
            cv2.imwrite(card_crop_path, card, [cv2.IMWRITE_JPEG_QUALITY, 95])

            page_voters.append({
                'gp_serial': serial,
                'epic_id': epic,
                'house_no': house_no,
                'photo_path': f'/static/photos/{epic}.jpg',
                'crop_path': f'/static/crops/card_gp_{serial:04d}.jpg',
                'page_no': p_idx + 1
            })

    return p_idx + 1, page_voters

def main():
    print('Starting 3-Worker Extraction & Matching Pipeline...')
    t0 = time.time()

    # Step 1: Query existing DB voters
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Add new columns if not present
    c.execute('PRAGMA table_info(voters)')
    cols = [r[1] for r in c.fetchall()]
    if 'gp_serial' not in cols:
        c.execute('ALTER TABLE voters ADD COLUMN gp_serial INTEGER')
    conn.commit()

    c.execute('SELECT * FROM voters')
    db_voters = {r['epic_id']: dict(r) for r in c.fetchall() if r['epic_id']}
    
    # Step 2: Run parallel extraction on Pages 1 to 23
    all_extracted = []
    with ProcessPoolExecutor(max_workers=3) as executor:
        for page_num, voters in executor.map(process_page_worker, range(23)):
            all_extracted.extend(voters)
            print(f'Page {page_num}/23 extracted ({len(voters)} voters)')

    print(f'Extraction complete! Total voters extracted from voters-new.pdf: {len(all_extracted)}')

    # Step 3: Clear previous recorded response as requested!
    c.execute("UPDATE voters SET party = 'UNASSIGNED', voted = 0")
    conn.commit()
    print('Cleared all previous party responses.')

    # Step 4: Match and update existing voters, or insert new voters
    matched = 0
    added_new = 0

    # Get max current serial_no
    c.execute('SELECT MAX(serial_no) FROM voters')
    max_serial = c.fetchone()[0] or 538

    for v in all_extracted:
        epic = v['epic_id']
        gp_serial = v['gp_serial']

        if epic in db_voters:
            # Update existing voter with new high-clarity photo & new card slip
            c.execute('''
                UPDATE voters SET
                    photo_path = ?,
                    crop_path = ?,
                    gp_serial = ?
                WHERE epic_id = ?
            ''', (v['photo_path'], v['crop_path'], gp_serial, epic))
            matched += 1
        else:
            # New voter from voters-new.pdf!
            max_serial += 1
            default_name = f'Voter #{gp_serial}'
            house = v['house_no'] or '1-1'
            c.execute('''
                INSERT INTO voters (
                    serial_no, epic_id, name, relation_type, relation_name, 
                    house_no, age, gender, section_name, ac_name, part_no, 
                    page_no, crop_path, photo_path, party, voted, gp_serial
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                max_serial,
                epic,
                default_name,
                'Guardian',
                'N/A',
                house,
                35,
                'Male',
                'Cheekatipalle GP Ward 1',
                '175-KUPPAM',
                '132',
                v['page_no'],
                v['crop_path'],
                v['photo_path'],
                'UNASSIGNED',
                0,
                gp_serial
            ))
            added_new += 1

    conn.commit()
    
    # Check total count in DB
    c.execute('SELECT COUNT(*) FROM voters')
    total_in_db = c.fetchone()[0]
    conn.close()

    t1 = time.time()
    print('='*50)
    print(f'SYNC COMPLETE in {round(t1-t0, 1)} seconds!')
    print(f'Matched existing voters: {matched}')
    print(f'Added new voters: {added_new}')
    print(f'Total voters now in Database: {total_in_db}')
    print('='*50)

if __name__ == '__main__':
    main()
