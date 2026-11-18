import os
import cv2
import pymupdf
import numpy as np
import time

PDF_PATH = 'voters-new.pdf'
PHOTOS_DIR = os.path.join('static', 'photos')
CROPS_DIR = os.path.join('static', 'crops_new')
os.makedirs(PHOTOS_DIR, exist_ok=True)
os.makedirs(CROPS_DIR, exist_ok=True)

col_xs = [114, 856, 1596]
card_w = 731
card_h = 303
row_y0 = 385
row_step = 303.5

doc = pymupdf.open(PDF_PATH)
print(f'Opened {PDF_PATH}, total pages: {len(doc)}')

t0 = time.time()
serial = 0

# Process pages 1 to 23 (indices 0 to 22), excluding page 24
for p_idx in range(23):
    p = doc[p_idx]
    pix = p.get_pixmap() # Native 300 DPI: 2480 x 3507
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape((pix.h, pix.w, pix.n))
    if pix.n == 4:
        img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
    elif pix.n == 3:
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

    for row in range(9):
        for col in range(3):
            serial += 1
            if serial > 593: # 593 is the last voter on page 23
                break

            y1 = int(row_y0 + row * row_step)
            y2 = int(y1 + card_h)
            x1 = col_xs[col]
            x2 = x1 + card_w
            card = img[y1:y2, x1:x2]

            # 1. Save full card
            card_filename = f'card_new_{serial:04d}.jpg'
            cv2.imwrite(os.path.join(CROPS_DIR, card_filename), card, [cv2.IMWRITE_JPEG_QUALITY, 95])

            # 2. Extract Photo with maximum clarity (Native unscaled 300 DPI)
            photo = card[105:285, 558:722]
            photo_filename = f'photo_gp_{serial:04d}.jpg'
            cv2.imwrite(os.path.join(PHOTOS_DIR, photo_filename), photo, [cv2.IMWRITE_JPEG_QUALITY, 98])

    print(f'Page {p_idx+1}/23 processed. Total cards cropped: {serial}')

t1 = time.time()
print(f'Done! Cropped {serial} high-clarity voter photos and cards in {round(t1-t0, 1)}s!')
