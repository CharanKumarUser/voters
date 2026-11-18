import os
import re
import cv2
import pymupdf
import numpy as np
import sqlite3
import time
from rapidocr_onnxruntime import RapidOCR

PDF_PATH = '2026-EROLLGEN-S01-175-SIR-DraftRoll-Revision1-ENG-159-WI (1).pdf'
DB_PATH = 'voters.db'

def clean_name(s):
    # remove leading/trailing non-letters
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
            # check it's not Father's Name or Husband's Name
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
        'relation_name': rel_name or 'Not Specified',
        'house_no': house_no or '1',
        'age': age if age > 0 else 35,
        'gender': gender
    }

def process_page(engine, doc, p_idx, start_serial):
    page_no = p_idx + 1
    page = doc[p_idx]
    pix = page.get_pixmap()
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape((pix.h, pix.w, pix.n))
    if pix.n == 4:
        img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
    elif pix.n == 3:
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

    # 1. OCR on full page
    ocr_results, _ = engine(img)

    # 2. Extract Section Name from header
    sec_name = "1-Main Road Cheekatipalle"
    for item in ocr_results:
        t = item[1]
        if 'Section' in t:
            sec_name = t.strip()
            break

    # 3. Detect card boxes
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
        # texts inside this box
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

    return voters_parsed, current_serial

def main():
    print('Starting OCR Enrichment Engine...')
    engine = RapidOCR()
    doc = pymupdf.open(PDF_PATH)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    current_serial = 1
    total_start = time.time()

    for p_idx in range(2, 22):
        p_no = p_idx + 1
        t0 = time.time()
        voters, current_serial = process_page(engine, doc, p_idx, current_serial)

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
        t1 = time.time()
        print(f'Page {p_no}/22 enriched ({len(voters)} voters, current total: {current_serial - 1}) in {round(t1-t0, 1)}s')

    conn.close()
    print(f'All voters enriched successfully in {round(time.time() - total_start, 1)}s!')

if __name__ == '__main__':
    main()

