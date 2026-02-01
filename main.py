import os
import random
import string
import datetime
import jwt
import google.generativeai as genai

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ======================
# ENV
# ======================
JWT_SECRET = os.getenv("JWT_SECRET", "CHANGE_THIS_SECRET")
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "CHANGE_ADMIN_TOKEN")

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
app = FastAPI(title="Educational AI Tool")

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

# ======================
# HELPERS
# ======================
def pick_gemini_model():
    key = random.choice(GEMINI_KEYS)
    genai.configure(api_key=key)
    return genai.GenerativeModel("models/gemini-2.5-flash-lite")

def generate_short_code(length=6):
    chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(random.choice(chars) for _ in range(length))

def verify_jwt(token: str):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        if payload.get("type") != "activation":
            raise HTTPException(status_code=401, detail="Invalid token type")
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Activation expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid access token")

# ======================
# ROUTES
# ======================
@app.get("/")
def health():
    return {"status": "ok"}

# -------------------------------------------------
# توليد كود قصير (للمشرف فقط)
# -------------------------------------------------
@app.get("/easy-code")
def easy_code(key: str):
    if key != ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Forbidden")

    short_code = generate_short_code()

    return {
        "activation_code": short_code,
        "expires_in": "30 days"
    }

# -------------------------------------------------
# تفعيل الكود القصير → JWT
# -------------------------------------------------
@app.post("/activate")
def activate(data: ActivateRequest):
    code = data.code.strip().upper()

    if len(code) < 4:
        raise HTTPException(status_code=400, detail="Invalid activation code")

    payload = {
        "type": "activation",
        "code": code,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(days=30)
    }

    token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")

    return {
        "token": token,
        "expires_in": "30 days"
    }

# -------------------------------------------------
# تحقق من JWT (يُستخدم بالفرونت)
# -------------------------------------------------
@app.get("/verify")
def verify(x_token: str = Header(..., alias="X-Token")):
    verify_jwt(x_token)
    return {"status": "ok"}

# -------------------------------------------------
# توليد محتوى Gemini
# -------------------------------------------------
@app.post("/generate")
def generate(
    data: AskRequest,
    x_token: str = Header(..., alias="X-Token")
):
    verify_jwt(x_token)

    try:
        model = pick_gemini_model()
        response = model.generate_content(data.prompt)

        return {"answer": response.text}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))