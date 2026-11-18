import cv2
import os

print("Checking sample photos from various pages:")
sample_serials = [1, 2, 3, 27, 28, 54, 55, 81, 82, 108, 109, 128, 129, 155, 156, 182, 183, 209, 210, 236, 237, 256, 257, 283, 284, 310, 311, 337, 338, 364, 365, 384, 385, 411, 412, 438, 439, 465, 466, 492, 493, 512, 513, 539, 540, 566, 567, 593]

for s in sample_serials:
    p_path = f"static/photos/photo_gp_{s:04d}.jpg"
    if os.path.exists(p_path):
        img = cv2.imread(p_path)
        h, w = img.shape[:2]
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        std = gray.std()
        mean = gray.mean()
        # Check border pixels
        top_dark = (gray[:10, :] < 50).mean()
        bot_dark = (gray[-10:, :] < 50).mean()
        print(f"GP#{s:04d}: shape=({w}x{h}), std={std:.1f}, mean={mean:.1f}, top_dark={top_dark:.2f}, bot_dark={bot_dark:.2f}")
    else:
        print(f"GP#{s:04d}: MISSING FILE!")
