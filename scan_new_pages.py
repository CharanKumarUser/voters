import pymupdf
import cv2
import numpy as np

doc = pymupdf.open('voters-new.pdf')
print(f'Total pages in doc: {len(doc)}')

for p_idx in range(23): # 0 to 22 (pages 1 to 23)
    p = doc[p_idx]
    pix = p.get_pixmap()
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape((pix.h, pix.w, pix.n))
    if pix.n == 4:
        img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
    elif pix.n == 3:
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    thresh = cv2.adaptiveThreshold(~gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 15, -2)

    scale = 25
    h_structure = cv2.getStructuringElement(cv2.MORPH_RECT, (thresh.shape[1] // scale, 1))
    h_lines = cv2.dilate(cv2.erode(thresh, h_structure), h_structure)
    v_structure = cv2.getStructuringElement(cv2.MORPH_RECT, (1, thresh.shape[0] // scale))
    v_lines = cv2.dilate(cv2.erode(thresh, v_structure), v_structure)

    mask = h_lines + v_lines
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    boxes = [cv2.boundingRect(c) for c in contours if 650 < cv2.boundingRect(c)[2] < 850 and 260 < cv2.boundingRect(c)[3] < 380]
    print(f'Page {p_idx+1}: {len(boxes)} boxes detected')
