import base64
import gc
import os
import time
import traceback
from io import BytesIO

import numpy as np
import torch
import torch.nn.functional as F
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from PIL import Image
from torchvision import models, transforms

# ===================== CONFIG =====================
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
LABELS = ["Grade 1", "Grade 2", "Grade 3", "Healthy"]
NUM_CLASSES = 4

STRICT_FOOT_VALIDATION = os.getenv("STRICT_FOOT_VALIDATION", "false").lower() == "true"
BYPASS_VISION_API = os.getenv("BYPASS_VISION_API", "false").lower() == "true"
VISION_THRESHOLD = 0.25
HEALTHY_CONFIDENCE_THRESHOLD = 0.85

# ===================== FASTAPI =====================
app = FastAPI(title="DFU Classifier + GradCAM (Medical Safe)")

# Wide-open CORS — explicit origins + wildcard. Order matters: this is the
# FIRST middleware added, so it sees all responses including errors.
ALLOWED_ORIGINS = [
    "http://127.0.0.1:5501",
    "http://localhost:5501",
    "http://127.0.0.1:5500",
    "http://localhost:5500",
    "*",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=".*",
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=False,
    expose_headers=["*"],
    max_age=3600,
)

# Fallback middleware: ensures CORS headers are on EVERY response, even if
# something inside the app throws before CORSMiddleware can attach them.
@app.middleware("http")
async def force_cors_headers(request, call_next):
    if request.method == "OPTIONS":
        from starlette.responses import Response
        return Response(
            status_code=200,
            headers={
                "Access-Control-Allow-Origin":  "*",
                "Access-Control-Allow-Methods": "*",
                "Access-Control-Allow-Headers": "*",
                "Access-Control-Max-Age":       "3600",
            },
        )
    try:
        response = await call_next(request)
    except Exception as e:
        from starlette.responses import JSONResponse
        traceback.print_exc()
        response = JSONResponse(
            status_code=500,
            content={"error": f"{type(e).__name__}: {e}"},
        )
    response.headers["Access-Control-Allow-Origin"]  = "*"
    response.headers["Access-Control-Allow-Methods"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "*"
    return response

class ImageInput(BaseModel):
    file: str

# ===================== LOAD MODEL =====================
MODEL_PATH = "mobilenet_model.pth"

def load_model():
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(
            f"Model weights '{MODEL_PATH}' not found in working directory. "
            f"Make sure the file is committed to the repository."
        )
    model = models.mobilenet_v2(weights=None)
    model.classifier[1] = torch.nn.Linear(model.last_channel, NUM_CLASSES)
    model.load_state_dict(torch.load(MODEL_PATH, map_location=DEVICE))
    model.eval().to(DEVICE)
    return model

try:
    model = load_model()
    print("[OK] Model loaded", flush=True)
except Exception as e:
    print(f"[FAIL] Model load failed: {e}", flush=True)
    raise

# ===================== VISION CLIENT =====================
# Vision SDK is imported lazily so a 512 MB free-tier dyno isn't forced to
# load ~100 MB of google.cloud.* into RAM when BYPASS_VISION_API=true.
vision = None  # type: ignore  (filled in only when not bypassed)

def create_vision_client():
    global vision
    if BYPASS_VISION_API:
        print("[OK] Vision API bypassed (BYPASS_VISION_API=true)", flush=True)
        return None
    try:
        from google.cloud import vision as _vision
        from google.auth import default
        vision = _vision
        creds, project = default()
        print(f"[OK] Vision API ready (project={project})", flush=True)
        return vision.ImageAnnotatorClient(credentials=creds)
    except Exception as e:
        print(f"[WARN] Vision init failed: {e}", flush=True)
        return None

vision_client = create_vision_client()

# ===================== PREPROCESS =====================
preprocess = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    ),
])

IMAGENET_MEAN = np.array([0.485, 0.456, 0.406]).reshape(1, 1, 3)
IMAGENET_STD  = np.array([0.229, 0.224, 0.225]).reshape(1, 1, 3)

def denorm(x):
    x = x.cpu().numpy().transpose(0, 2, 3, 1)
    return np.clip(x * IMAGENET_STD + IMAGENET_MEAN, 0, 1)

# ===================== GRADCAM =====================
# IMPORTANT: a single GradCAM instance is constructed at module load and
# reused for every request. Previously the predict() handler instantiated a
# new GradCAM per call, each one registering fresh forward+backward hooks on
# the model. Hooks were never removed, so the model accumulated thousands of
# hooks under load -> memory growth -> OOM kill -> 502 Bad Gateway.
class GradCAM:
    def __init__(self, model, layer):
        self.model = model
        self.grad = None
        self.act = None
        # Hooks registered exactly once.
        layer.register_forward_hook(
            lambda m, i, o: setattr(self, "act", o)
        )
        layer.register_full_backward_hook(
            lambda m, gi, go: setattr(self, "grad", go[0])
        )

    def __call__(self, x, idx):
        self.model.zero_grad()
        out = self.model(x)
        out[:, idx].sum().backward()

        w = self.grad.mean(dim=(2, 3), keepdim=True)
        cam = (w * self.act).sum(dim=1, keepdim=True)
        cam = torch.relu(cam)
        cam = F.interpolate(cam, x.shape[2:], mode="bilinear", align_corners=False)
        cam = (cam - cam.min()) / (cam.max() - cam.min() + 1e-8)
        return cam[0, 0].detach().cpu().numpy()

gradcam = GradCAM(model, model.features[-1])

# Pure-numpy / PIL jet colormap, replacing matplotlib.
# matplotlib pulled in ~60 MB of RAM and added 2-5 s per heatmap render on
# Render's free 0.1-CPU dyno. With this, heatmap generation is ~50 ms and
# matplotlib never needs to be imported.
_JET_STOPS = np.array([
    [0.00, 0.00, 0.50],
    [0.00, 0.00, 1.00],
    [0.00, 0.50, 1.00],
    [0.00, 1.00, 1.00],
    [0.50, 1.00, 0.50],
    [1.00, 1.00, 0.00],
    [1.00, 0.50, 0.00],
    [1.00, 0.00, 0.00],
    [0.50, 0.00, 0.00],
], dtype=np.float32)
_JET_POS = np.linspace(0.0, 1.0, _JET_STOPS.shape[0]).astype(np.float32)

def _jet_colormap(cam):
    """cam: (H,W) in [0,1] -> (H,W,3) uint8."""
    cam = np.clip(cam, 0.0, 1.0).astype(np.float32)
    r = np.interp(cam, _JET_POS, _JET_STOPS[:, 0])
    g = np.interp(cam, _JET_POS, _JET_STOPS[:, 1])
    b = np.interp(cam, _JET_POS, _JET_STOPS[:, 2])
    return (np.stack([r, g, b], axis=-1) * 255.0).astype(np.uint8)

def cam_to_base64(cam, img):
    """img: (H,W,3) in [0,1] (from denorm). cam: (H,W) in [0,1]."""
    base = (np.asarray(img, dtype=np.float32) * 255.0)
    heat = _jet_colormap(cam).astype(np.float32)
    blended = np.clip(base * 0.5 + heat * 0.5, 0, 255).astype(np.uint8)
    buf = BytesIO()
    Image.fromarray(blended).save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()

# ===================== SAFE FOOT VALIDATION =====================
FOOT_KEYWORDS = {
    "foot", "feet", "heel", "toe", "toes", "ankle", "sole", "plantar",
    "leg", "lower leg", "human leg", "skin", "barefoot",
    "ulcer", "wound", "infection", "callus", "medical", "injury"
}

def extract_terms(resp):
    terms = []

    for l in resp.label_annotations:
        if l.score >= VISION_THRESHOLD:
            terms.append(l.description.lower())

    for o in resp.localized_object_annotations:
        if o.score >= VISION_THRESHOLD:
            terms.append(o.name.lower())

    if resp.web_detection:
        for e in resp.web_detection.web_entities:
            if e.score >= VISION_THRESHOLD and e.description:
                terms.append(e.description.lower())

    return list(set(terms))

def is_foot_image(img_bytes):
    if BYPASS_VISION_API:
        return True, {"vision": "bypassed"}

    if vision_client is None:
        return True, {"vision": "client_not_ready_but_allowed"}

    features = [
        vision.Feature(type=vision.Feature.Type.LABEL_DETECTION),
        vision.Feature(type=vision.Feature.Type.OBJECT_LOCALIZATION),
        vision.Feature(type=vision.Feature.Type.WEB_DETECTION),
    ]

    image = {"content": img_bytes}

    try:
        resp = vision_client.annotate_image({"image": image, "features": features})
    except Exception as e:
        return True, {"vision_error": str(e), "allowed": True}

    terms = extract_terms(resp)

    foot_hit = any(
        any(k in t for k in FOOT_KEYWORDS)
        for t in terms
    )

    allowed = foot_hit or not STRICT_FOOT_VALIDATION

    return allowed, {
        "vision_terms": terms,
        "foot_detected": foot_hit,
        "strict_mode": STRICT_FOOT_VALIDATION
    }

# ===================== ENDPOINTS =====================
@app.get("/")
def root():
    return {
        "service": "DFU Classifier + GradCAM",
        "status": "ok",
        "endpoints": ["/health", "/predict", "/docs"]
    }

@app.get("/health")
def health():
    return {
        "model_loaded": True,
        "vision_ready": vision_client is not None,
        "strict_foot_validation": STRICT_FOOT_VALIDATION,
        "bypass_vision": BYPASS_VISION_API
    }

@app.post("/predict")
def predict(data: ImageInput):
    t0 = time.perf_counter()
    try:
        img_bytes = base64.b64decode(data.file.split(",")[-1])

        ok, vision_debug = is_foot_image(img_bytes)
        if not ok:
            return {
                "error": "Upload a foot image",
                "vision_debug": vision_debug
            }

        img = Image.open(BytesIO(img_bytes)).convert("RGB")
        # Cap input dimensions to keep RAM/CPU low on the free dyno. Phones
        # often upload 12 MP photos that we resize to 224 anyway for the
        # model, so a 1024-px thumbnail here loses nothing meaningful.
        if max(img.size) > 1024:
            img.thumbnail((1024, 1024), Image.LANCZOS)

        x = preprocess(img).unsqueeze(0).to(DEVICE)
        t1 = time.perf_counter()

        with torch.no_grad():
            probs = F.softmax(model(x), dim=1)[0].cpu().numpy()

        pred_idx = int(np.argmax(probs))
        pred_label = LABELS[pred_idx]
        healthy_idx = LABELS.index("Healthy")

        gradcam_img = None
        cam_note = None
        cam_class_label = None

        if pred_idx != healthy_idx:
            cam_idx = pred_idx
            cam_note = "Grad-CAM shown for predicted ulcer grade."
        elif probs[healthy_idx] < HEALTHY_CONFIDENCE_THRESHOLD:
            cam_idx = int(np.argsort(probs)[-2])
            cam_note = (
                f"Predicted Healthy with low confidence "
                f"({probs[healthy_idx]*100:.1f}%). "
                f"Showing Grad-CAM for {LABELS[cam_idx]}."
            )
        else:
            cam_idx = None
            cam_note = "Confident Healthy prediction. Grad-CAM not shown."

        t2 = time.perf_counter()
        if cam_idx is not None:
            cam = gradcam(x, cam_idx)         # singleton, no hook leak
            gradcam_img = cam_to_base64(cam, denorm(x)[0])
            cam_class_label = LABELS[cam_idx]
        t3 = time.perf_counter()
        print(
            f"[predict] decode+resize={t1-t0:.2f}s "
            f"infer={t2-t1:.2f}s cam={t3-t2:.2f}s total={t3-t0:.2f}s",
            flush=True,
        )

        response = {
            "prediction": pred_label,
            "predicted_label": pred_label,
            "predicted_class": pred_label,
            "labels": LABELS,
            "probabilities": (probs * 100).tolist(),
            "gradcam": gradcam_img,
            "gradcam_image": gradcam_img,
            "cam_class_label": cam_class_label,
            "cam_note": cam_note,
            "vision_debug": vision_debug
        }
        # Encourage prompt cleanup on the 512 MB free tier.
        gc.collect()
        return response

    except Exception as e:
        traceback.print_exc()
        return {
            "error": f"Prediction failed: {type(e).__name__}: {e}",
        }

# ===================== RUN =====================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
