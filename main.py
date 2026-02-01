import os
import random
import datetime
import jwt
import google.generativeai as genai

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ==================================================
# ENV VARIABLES (تُضبط من Render فقط)
# ==================================================

JWT_SECRET = os.getenv("JWT_SECRET")
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN")

if not JWT_SECRET or not ADMIN_TOKEN:
    raise RuntimeError("JWT_SECRET or ADMIN_TOKEN missing")

# ===== 7 مفاتيح Gemini =====
GEMINI_KEYS = [
    os.getenv("GEMINI_API_KEY_1"),
    os.getenv("GEMINI_API_KEY_2"),
    os.getenv("GEMINI_API_KEY_3"),
    os.getenv("GEMINI_API_KEY_4"),
    os.getenv("GEMINI_API_KEY_5"),
    os.getenv("GEMINI_API_KEY_6"),
    os.getenv("GEMINI_API_KEY_7"),
]
GEMINI_KEYS = [k for k in GEMINI_KEYS if k]

if not GEMINI_KEYS:
    raise RuntimeError("No Gemini API Keys found")

# ==================================================
# APP
# ==================================================

app = FastAPI(title="Educational AI Tool")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================================================
# MODELS
# ==================================================

class AskRequest(BaseModel):
    prompt: str

class ActivateRequest(BaseModel):
    code: str

# ==================================================
# HELPERS
# ==================================================

def pick_gemini_model():
    key = random.choice(GEMINI_KEYS)
    genai.configure(api_key=key)
    return genai.GenerativeModel("models/gemini-2.5-flash-lite")

def verify_jwt(token: str):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        if payload.get("type") != "activation":
            raise HTTPException(status_code=401, detail="Invalid token type")
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Activation code expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid access token")

# ==================================================
# ROUTES
# ==================================================

@app.get("/")
def health():
    return {
        "status": "ok",
        "time": datetime.datetime.utcnow().isoformat()
    }

# --------------------------------------------------
# توليد كود تفعيل قصير (للمشرف فقط)
# --------------------------------------------------
@app.get("/generate-code")
def generate_code(key: str):
    if key != ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Forbidden")

    short_code = "".join(random.choice("ABCDEFGHJKLMNPQRSTUVWXYZ23456789") for _ in range(6))

    payload = {
        "type": "activation",
        "code": short_code,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(days=30)
    }

    token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")

    return {
        "activation_code": short_code,
        "token": token,
        "expires_in": "30 days"
    }

# --------------------------------------------------
# تفعيل الأداة (تحويل كود قصير → JWT)
# --------------------------------------------------
@app.post("/activate")
def activate(data: ActivateRequest):
    if not data.code:
        raise HTTPException(status_code=400, detail="Code required")

    payload = {
        "type": "activation",
        "code": data.code,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(days=30)
    }

    token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")

    return {
        "token": token
    }

# --------------------------------------------------
# تحقق فقط (اختياري)
# --------------------------------------------------
@app.get("/verify")
def verify(x_token: str = Header(..., alias="X-Token")):
    verify_jwt(x_token)
    return {"status": "ok"}

# --------------------------------------------------
# توليد رد Gemini (محمي بالتفعيل)
# --------------------------------------------------
@app.post("/generate")
def generate(
    data: AskRequest,
    x_token: str = Header(..., alias="X-Token")
):
    verify_jwt(x_token)

    model = pick_gemini_model()
    response = model.generate_content(data.prompt)

    return {
        "answer": response.text
    }