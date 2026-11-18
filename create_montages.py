import os
import cv2
import numpy as np

import populate_db_final
t_keys = sorted(populate_db_final.transliterated_new_voters.keys())
print(f"Total cards to audit: {len(t_keys)}")

OUT_DIR = "scratch_montages"
os.makedirs(OUT_DIR, exist_ok=True)

batch_size = 6
montage_files = []

for i in range(0, len(t_keys), batch_size):
    batch = t_keys[i:i+batch_size]
    card_imgs = []
    for s in batch:
        path = f"static/crops/card_gp_{s:04d}.jpg"
        img = cv2.imread(path)
        if img is not None:
            # Add a clear border and header text indicating GP#
            h, w = img.shape[:2]
            header = np.full((30, w, 3), (15, 23, 42), dtype=np.uint8)
            cv2.putText(header, f"CARD GP#{s}", (15, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            card_with_hdr = np.vstack([header, img])
            card_imgs.append(card_with_hdr)
    
    if card_imgs:
        montage = np.vstack(card_imgs)
        filename = f"{OUT_DIR}/montage_{i//batch_size:02d}.jpg"
        cv2.imwrite(filename, montage, [cv2.IMWRITE_JPEG_QUALITY, 90])
        montage_files.append((filename, batch))
        print(f"Created {filename} for GP cards: {batch}")

print(f"Total montages created: {len(montage_files)}")
