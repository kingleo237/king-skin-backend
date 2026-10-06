"""
King Skin — backend d'analyse cutanée (moteur heuristique de démarrage)
========================================================================

Ce backend est un VRAI pipeline de traitement d'image (pas une simulation) :
il reçoit une photo, détecte le visage, isole la zone de peau, et calcule
des indicateurs mesurés sur les pixels (rougeurs, taches, brillance,
texture, sécheresse) pour proposer un diagnostic parmi les 15 fiches de
la base King Skin.

LIMITE IMPORTANTE À CONNAÎTRE (voir README.md) :
Ce moteur utilise des heuristiques de vision par ordinateur classiques
(seuillage HSV, variance de Laplacien), pas un modèle entraîné. Ces
heuristiques sont notoirement MOINS FIABLES sur les peaux à forte
mélanine — exactement le biais que King Skin veut corriger. Ce backend
est un squelette technique fonctionnel pour valider le pipeline de bout
en bout (upload → analyse → mapping → réponse), pas le moteur final.
Pour la production, remplacez `analyze_skin()` par un appel à un
prestataire entraîné (Haut.AI, Perfect Corp) ou votre futur modèle
propriétaire (Phase 3 de la feuille de route).
"""

import io
import os
import numpy as np
import cv2
import requests
from PIL import Image
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# ============================================================
# FOURNISSEUR D'IA — configuration
# ============================================================
# AI_PROVIDER contrôle quel moteur répond à /api/diagnose :
#   "heuristic" (défaut) — le moteur de vision par ordinateur ci-dessous
#   "zyla"      — Scan Skin Analysis API (Zyla Labs), self-service,
#                 validé sur les 6 types de peau Fitzpatrick (I-VI).
#                 Inscription immédiate : zylalabs.com, ~25 USD/mois
#                 pour 50 requêtes. Il suffit de définir ZYLA_API_KEY.
#   "haut"      — Haut.AI. PAS ENCORE DISPONIBLE EN LIBRE-SERVICE :
#                 leur documentation exige de réserver une démo
#                 commerciale (haut.ai/book-a-demo) avant d'obtenir un
#                 accès API. La fonction ci-dessous est prête à
#                 compléter une fois cet accès obtenu.
#   "perfectcorp" — Perfect Corp (YouCam). Un "API Playground" existe
#                 pour tester, mais l'accès production passe en
#                 général par un contact commercial. Fonction prête
#                 à compléter de la même façon.
AI_PROVIDER = os.environ.get("AI_PROVIDER", "heuristic").lower()
ZYLA_API_KEY = os.environ.get("ZYLA_API_KEY", "")
ZYLA_ENDPOINT = "https://zylalabs.com/api/12885/scan+skin+analysis+api/25653/detect+skin+condition"

# Table de correspondance : mots-clés dans la réponse en anglais du
# fournisseur -> identifiant de fiche King Skin (C01-C15). Le premier
# mot-clé trouvé (dans l'ordre) l'emporte.
CONDITION_KEYWORDS = [
    ("C02", ["blackhead", "whitehead", "comedon"]),
    ("C01", ["acne", "pimple", "pustule", "papule"]),
    ("C03", ["scar"]),
    ("C05", ["melasma"]),
    ("C04", ["hyperpigmentation", "dark spot", "age spot", "sun spot", "pigmentation"]),
    ("C15", ["sunburn", "sun damage", "burn"]),
    ("C10", ["rosacea", "sensitiv", "irritat"]),
    ("C13", ["dark circle", "under eye", "puffiness", "eye bag"]),
    ("C12", ["wrinkle", "sagging", "fine line and deep"]),
    ("C11", ["fine line", "early aging", "early sign"]),
    ("C14", ["keratosis pilaris", "rough bump"]),
    ("C09", ["pore"]),
    ("C08", ["oily", "sebum", "shine", "shiny"]),
    ("C07", ["dry", "dehydrat", "flak"]),
    ("C06", ["dull"]),
]


def match_condition_from_text(result_text: str, summary_text: str):
    """Fait correspondre la réponse en texte libre d'un fournisseur tiers
    à l'une de nos 15 fiches King Skin, par recherche de mots-clés."""
    haystack = f"{result_text} {summary_text}".lower()
    for condition_id, keywords in CONDITION_KEYWORDS:
        if any(kw in haystack for kw in keywords):
            return condition_id
    return None


def call_zyla_api(image_bytes: bytes, filename: str):
    """Appel réel à l'API Zyla Labs (Scan Skin Analysis API)."""
    if not ZYLA_API_KEY:
        raise RuntimeError("ZYLA_API_KEY non configurée")
    headers = {"Authorization": f"Bearer {ZYLA_API_KEY}"}
    files = {"image": (filename, image_bytes, "image/jpeg")}
    params = {"skin_illness_location": "face"}
    resp = requests.post(ZYLA_ENDPOINT, headers=headers, files=files, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    result_text = data.get("result", "")
    summary_text = data.get("summary", "")
    confidence_pct = data.get("confidence", 0)
    condition_id = match_condition_from_text(result_text, summary_text)
    if condition_id is None:
        raise RuntimeError(f"Résultat Zyla non reconnu par le mapping local : '{result_text}'")
    return {
        "conditionId": condition_id,
        "confidence": round(float(confidence_pct) / 100.0, 2),
        "engine": "zyla-scan-skin-v1",
        "providerResult": result_text,
    }


def call_haut_api(image_bytes: bytes, filename: str):
    """PAS ENCORE BRANCHABLE : Haut.AI exige une démo commerciale avant
    accès API (voir haut.ai/book-a-demo). Une fois l'accès obtenu, le
    flux documenté est : POST /api/v1/auth/private_tokens/ (ou
    /api/v1/login/) pour un token Bearer -> upload de l'image via
    l'API Images -> lancement d'un run sur l'algorithme Acné/Pigmentation
    via companies/{companyId}/applications/{appId}/runs/ -> lecture du
    résultat structuré. Implémentez ici une fois les identifiants reçus."""
    raise NotImplementedError(
        "Haut.AI nécessite de réserver une démo commerciale (haut.ai/book-a-demo) "
        "avant de recevoir un accès API — non disponible en self-service à ce jour."
    )


def call_perfectcorp_api(image_bytes: bytes, filename: str):
    """PAS ENCORE BRANCHÉ : Perfect Corp propose un API Playground pour
    tester, mais l'accès production passe généralement par un contact
    commercial. Implémentez ici une fois un accès et une clé obtenus."""
    raise NotImplementedError(
        "Perfect Corp : accès production à demander auprès de leur équipe commerciale — "
        "non branché à ce jour."
    )

app = FastAPI(title="King Skin — Diagnostic Engine (heuristic v1)")

# En production, restreignez allow_origins à votre domaine (ex. king-skin.com)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST"],
    allow_headers=["*"],
)

FACE_CASCADE = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

# Conditions que ce moteur heuristique peut effectivement distinguer aujourd'hui.
# Les 7 autres fiches de la base (melasma, cicatrices, cernes, kératose, etc.)
# demandent une distinction plus fine qu'une caméra + seuils de couleur ne
# peuvent pas apporter de façon fiable — elles nécessitent un vrai modèle entraîné.
REACHABLE_CONDITIONS = ["C01", "C02", "C04", "C06", "C07", "C08", "C09", "C15"]


def detect_face_region(bgr_img):
    gray = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2GRAY)
    faces = FACE_CASCADE.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80))
    if len(faces) == 0:
        return bgr_img, False
    x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
    return bgr_img[y:y + h, x:x + w], True


def skin_mask_hsv(bgr_img):
    hsv = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2HSV)
    # Deux plages combinées pour couvrir plus large que le seuillage HSV "manuel" classique.
    # Reste une heuristique imparfaite — voir avertissement en tête de fichier.
    lower1 = np.array([0, 15, 30], dtype=np.uint8)
    upper1 = np.array([25, 200, 255], dtype=np.uint8)
    lower2 = np.array([0, 10, 10], dtype=np.uint8)
    upper2 = np.array([20, 150, 120], dtype=np.uint8)
    mask = cv2.inRange(hsv, lower1, upper1) | cv2.inRange(hsv, lower2, upper2)
    return mask


def analyze_skin(bgr_img):
    """Calcule des indicateurs réels à partir des pixels de l'image."""
    face_region, face_found = detect_face_region(bgr_img)
    face_region = cv2.resize(face_region, (300, 300))
    mask = skin_mask_hsv(face_region)
    mask_bool = mask > 0
    skin_pixel_count = int(mask_bool.sum())

    if skin_pixel_count < 500:
        # Pas assez de zone de peau détectée pour un calcul fiable
        return None, face_found, skin_pixel_count

    b, g, r = cv2.split(face_region.astype(np.float32))
    hsv = cv2.cvtColor(face_region, cv2.COLOR_BGR2HSV).astype(np.float32)
    h, s, v = cv2.split(hsv)
    gray = cv2.cvtColor(face_region, cv2.COLOR_BGR2GRAY)

    skin_r, skin_g, skin_b = r[mask_bool], g[mask_bool], b[mask_bool]
    skin_v, skin_s = v[mask_bool], s[mask_bool]

    # Rougeur : dominance du rouge sur les autres canaux (indicateur d'inflammation)
    redness = float(np.mean(np.clip((skin_r - (skin_g + skin_b) / 2) / 255.0, 0, 1)))

    # Taches sombres : pixels nettement plus foncés que la médiane locale de peau
    median_v = float(np.median(skin_v))
    dark_ratio = float(np.mean(skin_v < (median_v * 0.72)))

    # Brillance / sébum : pixels très clairs et peu saturés (reflets spéculaires)
    shine_ratio = float(np.mean((skin_v > 210) & (skin_s < 60)))

    # Texture : variance du Laplacien sur la zone de peau (irrégularités de surface)
    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    texture_score = float(np.var(laplacian[mask_bool])) if skin_pixel_count > 0 else 0.0
    texture_norm = min(texture_score / 800.0, 1.0)

    # Teint terne : luminosité + saturation moyenne faibles
    dullness = float(1 - np.clip((np.mean(skin_v) / 255.0 * 0.6 + np.mean(skin_s) / 255.0 * 0.4), 0, 1))

    # Sécheresse (proxy) : forte variance locale de luminosité sans brillance (aspect irrégulier/mat)
    dryness_proxy = float(np.clip((np.std(skin_v) / 255.0) - shine_ratio, 0, 1))

    # Coup de soleil (proxy) : rougeur très élevée ET diffuse sur une grande part de la zone
    sunburn_signal = redness > 0.22 and float(np.mean(skin_r > 190)) > 0.5

    scores = {
        "redness": round(redness, 3),
        "dark_spot_ratio": round(dark_ratio, 3),
        "shine_ratio": round(shine_ratio, 3),
        "texture_roughness": round(texture_norm, 3),
        "dullness": round(dullness, 3),
        "dryness_proxy": round(dryness_proxy, 3),
    }

    # --- Mapping heuristique vers les fiches de la base King Skin ---
    # Règles simples, par priorité. À remplacer par la sortie d'un modèle entraîné en production.
    if sunburn_signal:
        condition_id, margin = "C15", redness
    elif redness > 0.12 and texture_norm > 0.35:
        condition_id, margin = "C01", (redness + texture_norm) / 2
    elif texture_norm > 0.3 and shine_ratio > 0.08:
        condition_id, margin = "C02", (texture_norm + shine_ratio) / 2
    elif dark_ratio > 0.18:
        condition_id, margin = "C04", dark_ratio
    elif shine_ratio > 0.14:
        condition_id, margin = "C08", shine_ratio
    elif dryness_proxy > 0.22:
        condition_id, margin = "C07", dryness_proxy
    elif dullness > 0.55:
        condition_id, margin = "C06", dullness
    else:
        condition_id, margin = "C09", texture_norm

    # Confiance volontairement plafonnée bas : ceci est une heuristique, pas un modèle entraîné.
    confidence = round(min(0.35 + margin * 0.5, 0.68), 2)

    return {"conditionId": condition_id, "confidence": confidence, "rawScores": scores}, face_found, skin_pixel_count


@app.get("/")
def root():
    return {"status": "ok", "service": "King Skin diagnostic engine (heuristic v1)"}


@app.post("/api/diagnose")
async def diagnose(image: UploadFile = File(...)):
    contents = await image.read()

    # 1) Si un vrai fournisseur d'IA est configuré, on l'essaie en premier.
    if AI_PROVIDER == "zyla":
        try:
            result = call_zyla_api(contents, image.filename or "photo.jpg")
            return JSONResponse(result)
        except Exception as e:
            # Repli automatique sur le moteur heuristique local en cas d'échec
            # (clé manquante, quota dépassé, résultat non reconnu, panne réseau...).
            fallback_reason = str(e)
        provider_fallback = {"provider": "zyla", "fallbackReason": fallback_reason}
    elif AI_PROVIDER in ("haut", "perfectcorp"):
        try:
            fn = call_haut_api if AI_PROVIDER == "haut" else call_perfectcorp_api
            result = fn(contents, image.filename or "photo.jpg")
            return JSONResponse(result)
        except NotImplementedError as e:
            provider_fallback = {"provider": AI_PROVIDER, "fallbackReason": str(e)}
    else:
        provider_fallback = None

    # 2) Moteur heuristique local (toujours disponible, aucune clé requise).
    try:
        pil_img = Image.open(io.BytesIO(contents)).convert("RGB")
    except Exception:
        raise HTTPException(status_code=400, detail="Image illisible")

    bgr_img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    result, face_found, skin_px = analyze_skin(bgr_img)

    if result is None:
        raise HTTPException(status_code=422, detail="Zone de peau insuffisante détectée dans l'image")

    result["engine"] = "heuristic-cv-v1"
    result["faceDetected"] = face_found
    if provider_fallback:
        result["providerFallback"] = provider_fallback
    return JSONResponse(result)
