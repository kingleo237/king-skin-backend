# King Skin — Backend d'analyse cutanée (v1 heuristique)

Ce dossier contient un **vrai backend fonctionnel**, testé de bout en bout :
il reçoit une photo par HTTP, détecte le visage, analyse les pixels de la
zone de peau, et renvoie un diagnostic parmi les 15 fiches de la base
King Skin. Ce n'est pas une simulation — `main.py` fait un traitement
d'image réel avec OpenCV/NumPy.

## ⚠️ Ce que ce moteur EST et N'EST PAS

**Ce qu'il est** : un pipeline technique complet et fonctionnel (upload →
détection de visage → extraction de la zone de peau → calcul d'indicateurs
→ mapping vers une fiche diagnostic → réponse JSON), prêt à déployer et à
brancher sur votre plateforme dès aujourd'hui.

**Ce qu'il n'est pas** : un moteur de diagnostic fiable au niveau clinique.
Il utilise des heuristiques classiques de vision par ordinateur (seuillage
de couleur, variance de texture) réglées à la main sur des images de test
synthétiques — pas un modèle entraîné sur de vraies données dermatologiques.
Deux limites concrètes à connaître :

1. **Moins fiable sur les peaux à forte mélanine.** Le seuillage de couleur
   (HSV) utilisé pour détecter la peau et les rougeurs est une technique
   connue pour moins bien fonctionner sur les tons de peau foncés — c'est
   précisément le biais que King Skin veut corriger. Ce backend ne corrige
   pas ce biais ; il faut un modèle entraîné pour ça (voir plus bas).
2. **Ne distingue que 8 des 15 conditions** (`C01, C02, C04, C06, C07, C08,
   C09, C15` — voir `REACHABLE_CONDITIONS` dans `main.py`). Les autres
   (melasma, cicatrices, cernes, kératose pilaire, etc.) demandent une
   distinction trop fine pour de simples seuils de couleur.

**Utilisez ce backend pour** : valider techniquement toute la chaîne
(déploiement, appel réseau depuis votre plateforme, format de réponse,
mapping vers votre base de données) pendant que vous négociez ou testez
un vrai fournisseur (Haut.AI, Perfect Corp).

**Pour la production** : remplacez le contenu de la fonction `analyze_skin()`
dans `main.py` par un appel à l'API du fournisseur choisi. Le reste du
backend (endpoint, format de réponse, CORS) n'a pas besoin de changer —
c'est conçu pour que ce soit un remplacement d'une seule fonction.

## Tester en local

```bash
pip install -r requirements.txt
python make_test_images.py          # génère 3 images de test synthétiques
uvicorn main:app --host 0.0.0.0 --port 8000
```

Dans un autre terminal :
```bash
curl -X POST http://127.0.0.1:8000/api/diagnose -F "image=@test_acne.jpg"
```

Réponse type :
```json
{
  "conditionId": "C09",
  "confidence": 0.44,
  "rawScores": {"redness": 0.219, "dark_spot_ratio": 0.009, "shine_ratio": 0.002, "texture_roughness": 0.185, "dullness": 0.383, "dryness_proxy": 0.057},
  "engine": "heuristic-cv-v1",
  "faceDetected": true
}
```

## Déployer en ligne (gratuit pour commencer)

**Option Railway (recommandée, la plus simple) :**
1. Créez un compte sur railway.app
2. "New Project" → "Deploy from GitHub repo" (poussez ce dossier sur un repo GitHub au préalable)
3. Railway détecte automatiquement `requirements.txt`
4. Ajoutez la commande de démarrage : `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Une fois déployé, Railway vous donne une URL publique (ex. `https://king-skin-backend.up.railway.app`)

**Option Render :**
1. Créez un compte sur render.com
2. "New Web Service" → connectez votre repo GitHub
3. Build command : `pip install -r requirements.txt`
4. Start command : `uvicorn main:app --host 0.0.0.0 --port $PORT`

## Brancher sur la plateforme King Skin

Une fois déployé, ouvrez `king-leo-skin.html` et remplacez :
```js
const API_ENDPOINT = ""; // ← vide actuellement
```
par :
```js
const API_ENDPOINT = "https://votre-backend-deploye.up.railway.app/api/diagnose";
```

Le bouton "Scanner une vraie photo" sur la plateforme appellera alors ce
backend réel au lieu d'afficher le message de repli.

## Vrai fournisseur d'IA déjà branché : Zyla Labs

Le backend sait maintenant appeler un vrai fournisseur d'IA tiers. Pour
l'activer, définissez ces deux variables d'environnement (sur Railway :
Settings → Variables) :

```
AI_PROVIDER=zyla
ZYLA_API_KEY=votre_clé_zyla
```

**Pour obtenir une clé** : créez un compte sur zylalabs.com, abonnez-vous
à "Scan Skin Analysis API" (essai gratuit 7 jours, 50 requêtes ; puis à
partir de ~25 USD/mois), copiez la clé depuis la page de l'API. Cette
API est validée sur les 6 types de peau Fitzpatrick (I-VI) — c'est un
vrai argument sur votre marché, à vérifier vous-même sur un échantillon
de photos avant de vous engager sur un plan payant.

Sans `AI_PROVIDER` défini (ou en cas d'échec de l'appel Zyla — clé
manquante, quota dépassé, résultat non reconnu), le backend bascule
automatiquement sur le moteur heuristique local : aucune interruption
de service.

## Haut.AI et Perfect Corp : pas encore branchables en self-service

Contrairement à Zyla, ces deux fournisseurs ne proposent pas
d'inscription immédiate pour un accès production :
- **Haut.AI** demande de réserver une démo commerciale (haut.ai/book-a-demo)
- **Perfect Corp** propose un playground de test, mais l'accès production
  passe généralement par un contact commercial

Les fonctions `call_haut_api()` et `call_perfectcorp_api()` dans `main.py`
sont déjà présentes, avec les étapes documentées en commentaire, prêtes à
compléter dès que vous obtenez un accès.
