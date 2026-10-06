"""Génère des images synthétiques de test (pas de vrais visages nécessaires)
pour vérifier que le pipeline upload -> détection -> analyse fonctionne."""
import numpy as np
import cv2

def make_face_canvas(skin_bgr, size=400):
    img = np.full((size, size, 3), (235, 225, 215), dtype=np.uint8)  # fond neutre
    cv2.ellipse(img, (size // 2, size // 2 + 10), (110, 150), 0, 0, 360, skin_bgr, -1)
    # yeux + bouche simples pour aider le détecteur de visage Haar
    cv2.ellipse(img, (size // 2 - 40, size // 2 - 20), (14, 8), 0, 0, 360, (40, 40, 40), -1)
    cv2.ellipse(img, (size // 2 + 40, size // 2 - 20), (14, 8), 0, 0, 360, (40, 40, 40), -1)
    cv2.ellipse(img, (size // 2, size // 2 + 60), (30, 10), 0, 0, 180, (60, 40, 90), 3)
    return img

# Peau claire avec rougeurs simulées (acné)
img1 = make_face_canvas((150, 170, 210))
rng = np.random.default_rng(0)
for _ in range(40):
    cx, cy = rng.integers(140, 260), rng.integers(150, 300)
    cv2.circle(img1, (cx, cy), rng.integers(3, 7), (60, 60, 200), -1)
cv2.imwrite("/home/claude/backend/test_acne.jpg", img1)

# Peau plus foncée avec taches sombres simulées (hyperpigmentation)
img2 = make_face_canvas((60, 90, 130))
for _ in range(25):
    cx, cy = rng.integers(140, 260), rng.integers(150, 300)
    cv2.circle(img2, (cx, cy), rng.integers(4, 9), (20, 30, 50), -1)
cv2.imwrite("/home/claude/backend/test_taches.jpg", img2)

# Peau grasse / brillante (reflets)
img3 = make_face_canvas((160, 180, 220))
for _ in range(15):
    cx, cy = rng.integers(160, 240), rng.integers(170, 260)
    cv2.circle(img3, (cx, cy), rng.integers(6, 12), (245, 245, 250), -1)
cv2.imwrite("/home/claude/backend/test_grasse.jpg", img3)

print("images de test générées")
