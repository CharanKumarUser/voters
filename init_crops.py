import os
import cv2
import pymupdf
import numpy as np
import sqlite3
import time

PDF_PATH = '2026-EROLLGEN-S01-175-SIR-DraftRoll-Revision1-ENG-159-WI (1).pdf'
CROPS_DIR = os.path.join('static', 'crops')
os.makedirs(CROPS_DIR, exist_ok=True)

# Initialize SQLite database
conn = sqlite3.connect('voters.db')
c = conn.cursor()
c.execute('''
CREATE TABLE IF NOT EXISTS voters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    serial_no INTEGER UNIQUE,
    epic_id TEXT DEFAULT '',
    name TEXT DEFAULT '',
    relation_type TEXT DEFAULT 'Father',
    relation_name TEXT DEFAULT '',
    house_no TEXT DEFAULT '',
    age INTEGER DEFAULT 0,
    gender TEXT DEFAULT 'Male',
    section_no TEXT DEFAULT '',
    section_name TEXT DEFAULT '',
    ac_name TEXT DEFAULT '175-KUPPAM',
    part_no TEXT DEFAULT '159',
    page_no INTEGER,
    crop_path TEXT,
    party TEXT DEFAULT 'UNASSIGNED',
    voted INTEGER DEFAULT 0,
    notes TEXT DEFAULT '',
    ocr_done INTEGER DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')
conn.commit()

doc = pymupdf.open(PDF_PATH)
print(f'Total pages in PDF: {len(doc)}')

serial_counter = 1
t0 = time.time()

for p_idx in range(2, 22): # Pages 3 to 22
    page_no = p_idx + 1
    page = doc[p_idx]
    pix = page.get_pixmap()
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape((pix.h, pix.w, pix.n))
    if pix.n == 4:
        img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
    elif pix.n == 3:
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    thresh = cv2.adaptiveThreshold(~gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 15, -2)
    scale = 20
    h_size = thresh.shape[1] // scale
    h_lines = cv2.dilate(cv2.erode(thresh, cv2.getStructuringElement(cv2.MORPH_RECT, (h_size, 1))), cv2.getStructuringElement(cv2.MORPH_RECT, (h_size, 1)))
    v_size = thresh.shape[0] // scale
    v_lines = cv2.dilate(cv2.erode(thresh, cv2.getStructuringElement(cv2.MORPH_RECT, (1, v_size))), cv2.getStructuringElement(cv2.MORPH_RECT, (1, v_size)))
    mask = h_lines + v_lines
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    boxes = [cv2.boundingRect(cnt) for cnt in contours if 500 < cv2.boundingRect(cnt)[2] < 700 and 200 < cv2.boundingRect(cnt)[3] < 300]
    boxes.sort(key=lambda b: (round(b[1] / 150), b[0]))

    # Determine section name based on page
    if page_no <= 10:
        sec_name = "1-Main Road Cheekatipalle"
    elif page_no <= 18:
        sec_name = "2-Gollapalle Cheekatipalle"
    else:
        sec_name = "3-Vengepalle Cheekatipalle"

    for (bx, by, bw, bh) in boxes:
        card_crop = img[by:by+bh, bx:bx+bw]
        crop_filename = f'voter_{serial_counter:04d}.jpg'
        crop_full_path = os.path.join(CROPS_DIR, crop_filename)
        cv2.imwrite(crop_full_path, card_crop, [cv2.IMWRITE_JPEG_QUALITY, 90])
        crop_rel_path = f'/static/crops/{crop_filename}'

        # Upsert into DB
        c.execute('''
        INSERT INTO voters (serial_no, page_no, crop_path, section_name, epic_id, name)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(serial_no) DO UPDATE SET
            page_no=excluded.page_no,
            crop_path=excluded.crop_path,
            section_name=excluded.section_name
        ''', (serial_counter, page_no, crop_rel_path, sec_name, f'VOTER-{serial_counter:03d}', f'Voter #{serial_counter}'))
        
        serial_counter += 1

    print(f'Page {page_no}: {len(boxes)} cards cropped. Total so far: {serial_counter - 1}')

conn.commit()
conn.close()
t1 = time.time()
print(f'Done! Successfully cropped and registered {serial_counter - 1} voters in {round(t1-t0, 2)} seconds!')

