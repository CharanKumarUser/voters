import json
import os
import cv2
import numpy as np
import sqlite3

with open('extracted_593.json') as f:
    data = json.load(f)

conn = sqlite3.connect('voters.db')
c = conn.cursor()
c.execute('SELECT epic_id FROM voters')
db_epics = set(r[0] for r in c.fetchall() if r[0])
conn.close()

# List unmatched
unmatched = [v for v in data if v['epic_id'] not in db_epics]
print(f'Total unmatched: {len(unmatched)}')

MONTAGE_DIR = 'scratch_montages'
os.makedirs(MONTAGE_DIR, exist_ok=True)

# We have already read:
# GP 1: Shriramulu, Kasturappa, 1-1, M, 42
# GP 2: Madhu, Shriramulu, 1-1, F, 36
# GP 5: Balaji L, Lakshmipati, 1-1/A1, M, 25
# GP 13: J Vijay, Jayaram, 1-9, M, 28
# GP 24: Ishvaramma, Chinna Achari, 4-3/1, F, 45
# GP 35: N Navya, N G Jagannath Babu, 1-23, F, 24
# GP 71: K V Madhan Mohan, Venkatappa, 4-2-1, M, 40
# GP 72: Mallika, K V Madhan Mohan, 4-2-1, F, 35
# GP 76: Ratnamma, Narayana, 4-11, F, 48
# GP 82: Venkatesu, Krishnappa, 4-11/1, M, 32
# GP 95: Radhappa Naidu, Lakshmappa Naidu, 4-19, M, 65

already_done = {1, 2, 5, 13, 24, 35, 71, 72, 76, 82, 95}
remaining = [u for u in unmatched if u['gp_serial'] not in already_done]
print(f'Remaining unmatched to transcribe: {len(remaining)}')

# Group in batches of 6
batch_size = 6
for b_idx in range(0, len(remaining), batch_size):
    batch = remaining[b_idx:b_idx+batch_size]
    imgs = []
    for item in batch:
        path = f"static/crops/card_gp_{item['gp_serial']:04d}.jpg"
        if os.path.exists(path):
            img = cv2.imread(path)
            # Add a clear label banner
            banner = np.zeros((30, img.shape[1], 3), dtype=np.uint8) + 240
            cv2.putText(banner, f"GP#{item['gp_serial']} - EPIC: {item['epic_id']}", (10, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 180), 2)
            card_with_banner = np.vstack([banner, img])
            imgs.append(card_with_banner)
    if imgs:
        montage = np.vstack(imgs)
        out_path = os.path.join(MONTAGE_DIR, f"batch_{b_idx//batch_size:02d}.jpg")
        cv2.imwrite(out_path, montage, [cv2.IMWRITE_JPEG_QUALITY, 95])

print('Montages created in scratch_montages')
