import os
import random
import datetime
import hashlib
import secrets
import jwt
import google.generativeai as genai

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ======================
# ENV
# ======================
JWT_SECRET = os.getenv("JWT_SECRET")
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN")

if not JWT_SECRET or not ADMIN_TOKEN:
    raise RuntimeError("JWT_SECRET or ADMIN_TOKEN missing")

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

# ======================
# APP
# ======================
app = FastAPI(title="Secure Educational AI Tool")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ======================
# MODELS
# ======================
class AskRequest(BaseModel):
    prompt: str

class ActivateRequest(BaseModel):
    code: str
    internal_token: str

# ======================
# HELPERS
# ======================
def pick_gemini_model():
    key = random.choice(GEMINI_KEYS)
    genai.configure(api_key=key)
    return genai.GenerativeModel("models/gemini-2.5-flash-lite")

def generate_short_code():
    return secrets.token_hex(3).upper()  # مثال: A3F9C2

def verify_usage_jwt(token: str):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        if payload.get("type") != "activation":
            raise HTTPException(status_code=401, detail="Invalid token type")
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# ======================
# ROUTES
# ======================

@app.get("/")
def health():
    return {
        "status": "ok",
        "time": datetime.datetime.utcnow().isoformat()
    }

# -------------------------------------------------
# توليد كود تفعيل (للمشرف فقط)
# -------------------------------------------------
@app.get("/easy-code")
def easy_code(key: str):
    if key != ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Forbidden")

    short_code = generate_short_code()
    code_hash = hashlib.sha256(short_code.encode()).hexdigest()

    payload = {
        "type": "activation_code",
        "code_hash": code_hash,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(days=30)
    }

    internal_token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")

    return {
        "activation_code": short_code,      # هذا يُعطى للمستخدم
        "internal_token": internal_token,   # هذا تحتفظ به أنت
        "expires_in": "30 days"
    }

# -------------------------------------------------
# تفعيل الأداة (التحقق الحقيقي)
# -------------------------------------------------
@app.post("/activate")
def activate(data: ActivateRequest):
    code = data.code.strip()
    if not code:
        raise HTTPException(status_code=400, detail="Empty code")

    try:
        payload = jwt.decode(
            data.internal_token,
            JWT_SECRET,
            algorithms=["HS256"]
        )

        if payload.get("type") != "activation_code":
            raise HTTPException(status_code=403)

        incoming_hash = hashlib.sha256(code.encode()).hexdigest()
        if incoming_hash != payload.get("code_hash"):
            raise HTTPException(status_code=403)

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=403, detail="Activation expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=403, detail="Invalid activation")

    usage_payload = {
        "type": "activation",
        "exp": datetime.datetime.utcnow() + datetime.timedelta(days=30)
    }

    usage_token = jwt.encode(
        usage_payload,
        JWT_SECRET,
        algorithm="HS256"
    )

    return {"token": usage_token}

# -------------------------------------------------
# تحقق من التفعيل
# -------------------------------------------------
@app.get("/verify")
def verify(x_token: str):
    verify_usage_jwt(x_token)
    return {"status": "ok"}

# -------------------------------------------------
# الذكاء الاصطناعي
# -------------------------------------------------
@app.post("/generate")
def generate(data: AskRequest, x_token: str):
    verify_usage_jwt(x_token)

    try:
        model = pick_gemini_model()
        response = model.generate_content(data.prompt)
        return {"answer": response.text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))