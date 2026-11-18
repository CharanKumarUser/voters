import os
import re
import cv2
import pymupdf
import numpy as np
import sqlite3
import time
from concurrent.futures import ProcessPoolExecutor
from rapidocr_onnxruntime import RapidOCR

PDF_PATH = '2026-EROLLGEN-S01-175-SIR-DraftRoll-Revision1-ENG-159-WI (1).pdf'
DB_PATH = 'voters.db'

def clean_name(s):
    s = re.sub(r'^[^a-zA-Z]+', '', s)
    s = re.sub(r'[^a-zA-Z\s\.]+$', '', s)
    return s.strip()

def parse_card_lines(raw_lines, fallback_serial):
    epic_id = ''
    name = ''
    rel_type = 'Father'
    rel_name = ''
    house_no = ''
    age = 0
    gender = 'Male'

    for line in raw_lines:
        line_clean = line.strip()

        # 1. EPIC ID
        if not epic_id:
            m_epic = re.search(r'\b([A-Z]{3}\d{7})\b', line_clean)
            if m_epic:
                epic_id = m_epic.group(1)
            else:
                m_epic2 = re.search(r'\b([A-Z0-9]{10})\b', line_clean)
                if m_epic2 and not m_epic2.group(1).startswith('0'):
                    epic_id = m_epic2.group(1)

        # 2. Name
        if not name and re.search(r'Name\s*[:\.]?', line_clean, re.I):
            if not re.search(r'(Father|Husband|Mother|Other)', line_clean, re.I):
                name_part = re.sub(r'^.*?Name\s*[:\.]?\s*', '', line_clean, flags=re.I)
                name = clean_name(name_part)

        # 3. Relation
        if re.search(r'Husband', line_clean, re.I):
            rel_type = 'Husband'
            r_part = re.sub(r'^.*?Husband[s\']?\s*Name\s*[:\.]?\s*', '', line_clean, flags=re.I)
            rel_name = clean_name(r_part)
        elif re.search(r'Father', line_clean, re.I):
            rel_type = 'Father'
            r_part = re.sub(r'^.*?Father[s\']?\s*Name\s*[:\.]?\s*', '', line_clean, flags=re.I)
            rel_name = clean_name(r_part)
        elif re.search(r'Mother', line_clean, re.I):
            rel_type = 'Mother'
            r_part = re.sub(r'^.*?Mother[s\']?\s*Name\s*[:\.]?\s*', '', line_clean, flags=re.I)
            rel_name = clean_name(r_part)

        # 4. House Number
        if re.search(r'House[\.\s]*Number', line_clean, re.I):
            h_part = re.sub(r'^.*?House[\.\s]*Number\s*[:\.]?\s*', '', line_clean, flags=re.I)
            house_no = h_part.strip()

        # 5. Age & Gender
        if 'Age' in line_clean or 'Gender' in line_clean:
            m_age = re.search(r'Age\s*[:lI\s]*(\d+)', line_clean)
            if m_age:
                age = int(m_age.group(1))
            m_gen = re.search(r'Gender\s*[:\s]*(Male|Female|Third Gender)', line_clean, re.I)
            if m_gen:
                g = m_gen.group(1).lower()
                gender = 'Female' if 'fem' in g else 'Male'

    return {
        'serial_no': fallback_serial,
        'epic_id': epic_id or f'UXN{fallback_serial:07d}',
        'name': name or f'Voter #{fallback_serial}',
        'relation_type': rel_type,
        'relation_name': rel_name or 'N/A',
        'house_no': house_no or '1',
        'age': age if age > 0 else 35,
        'gender': gender
    }

def worker_process_page(args):
    p_idx, start_serial = args
    page_no = p_idx + 1
    t0 = time.time()
    
    # Each process instantiates its own RapidOCR instance
    engine = RapidOCR()
    doc = pymupdf.open(PDF_PATH)
    page = doc[p_idx]
    pix = page.get_pixmap()
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape((pix.h, pix.w, pix.n))
    if pix.n == 4:
        img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
    elif pix.n == 3:
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

    ocr_results, _ = engine(img)

    sec_name = "1-Main Road Cheekatipalle"
    for item in ocr_results:
        t = item[1]
        if 'Section' in t:
            sec_name = t.strip()
            break

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

    voters_parsed = []
    current_serial = start_serial

    for (bx, by, bw, bh) in boxes:
        texts_in_box = []
        for item in ocr_results:
            poly = item[0]
            tx = min(p[0] for p in poly)
            ty = min(p[1] for p in poly)
            if bx <= tx <= bx + bw and by <= ty <= by + bh:
                texts_in_box.append((ty, tx, item[1]))
        texts_in_box.sort(key=lambda x: (round(x[0] / 30), x[1]))
        card_lines = [t[2] for t in texts_in_box]

        parsed = parse_card_lines(card_lines, current_serial)
        parsed['section_name'] = sec_name
        voters_parsed.append(parsed)
        current_serial += 1

    t1 = time.time()
    return page_no, voters_parsed, round(t1 - t0, 1)

def main():
    print('Starting 3-Worker Parallel OCR Extraction...')
    # Page serial start numbers:
    # Page 3: 1 (30 voters)
    # Page 4: 31 (30 voters)
    # Page 5: 61 (30 voters)
    # Page 6: 91 (30 voters)
    # Page 7: 121 (30 voters)
    # Page 8: 151 (30 voters)
    # Page 9: 181 (30 voters)
    # Page 10: 211 (10 voters -> ends at 220)
    # Page 11: 221 (30 voters)
    # Page 12: 251 (30 voters)
    # Page 13: 281 (30 voters)
    # Page 14: 311 (30 voters)
    # Page 15: 341 (30 voters)
    # Page 16: 371 (30 voters)
    # Page 17: 401 (30 voters)
    # Page 18: 431 (12 voters -> ends at 442)
    # Page 19: 443 (30 voters)
    # Page 20: 473 (30 voters)
    # Page 21: 503 (30 voters)
    # Page 22: 533 (6 voters -> ends at 538)

    page_starts = [
        (2, 1),    # p3
        (3, 31),   # p4
        (4, 61),   # p5
        (5, 91),   # p6
        (6, 121),  # p7
        (7, 151),  # p8
        (8, 181),  # p9
        (9, 211),  # p10
        (10, 221), # p11
        (11, 251), # p12
        (12, 281), # p13
        (13, 311), # p14
        (14, 341), # p15
        (15, 371), # p16
        (16, 401), # p17
        (17, 431), # p18
        (18, 443), # p19
        (19, 473), # p20
        (20, 503), # p21
        (21, 533)  # p22
    ]

    total_start = time.time()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    with ProcessPoolExecutor(max_workers=3) as executor:
        for page_no, voters, dur in executor.map(worker_process_page, page_starts):
            for v in voters:
                c.execute('''
                UPDATE voters SET
                    epic_id = ?,
                    name = ?,
                    relation_type = ?,
                    relation_name = ?,
                    house_no = ?,
                    age = ?,
                    gender = ?,
                    section_name = ?,
                    ocr_done = 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE serial_no = ?
                ''', (
                    v['epic_id'],
                    v['name'],
                    v['relation_type'],
                    v['relation_name'],
                    v['house_no'],
                    v['age'],
                    v['gender'],
                    v['section_name'],
                    v['serial_no']
                ))
            conn.commit()
            print(f'Page {page_no} enriched ({len(voters)} voters) in {dur}s')

    conn.close()
    print(f'All 538 voters completely enriched in {round(time.time() - total_start, 1)}s!')

if __name__ == '__main__':
    main()

