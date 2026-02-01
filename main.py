import os
import random
import datetime
import jwt

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ======================
# ENV
# ======================
JWT_SECRET = os.getenv("JWT_SECRET", "CHANGE_THIS_SECRET")
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "ADMIN_KEY")

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
# STORAGE (Short Codes)
# ======================
# { "ABC123": datetime }
SHORT_CODES = {}

# ======================
# MODELS
# ======================
class AskRequest(BaseModel):
    prompt: str

# ======================
# HELPERS
# ======================
def generate_short_code(length=6):
    chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(random.choice(chars) for _ in range(length))

def create_jwt(expiry: datetime.datetime):
    payload = {
        "type": "activation",
        "exp": expiry
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

def verify_jwt(token: str):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        if payload.get("type") != "activation":
            raise HTTPException(status_code=401, detail="Invalid token type")
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Activation expired")
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

# --------------------------------------------------
# توليد كود تفعيل قصير (للإدارة فقط)
# --------------------------------------------------
@app.get("/easy-code")
def easy_code(key: str):
    if key != ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Forbidden")

    short_code = generate_short_code()
    expiry = datetime.datetime.utcnow() + datetime.timedelta(days=30)

    SHORT_CODES[short_code] = expiry

    return {
        "activation_code": short_code,
        "expires_in": "30 days"
    }

# --------------------------------------------------
# التحقق من كود التفعيل (يُستخدم في صفحة التفعيل)
# --------------------------------------------------
@app.get("/verify")
def verify_activation(x_token: str = Header(None, alias="X-Token")):
    if not x_token:
        raise HTTPException(status_code=401, detail="Missing activation code")

    expiry = SHORT_CODES.get(x_token)

    if not expiry:
        raise HTTPException(status_code=401, detail="Invalid activation code")

    if datetime.datetime.utcnow() > expiry:
        del SHORT_CODES[x_token]
        raise HTTPException(status_code=401, detail="Activation code expired")

    jwt_token = create_jwt(expiry)

    return {
        "token": jwt_token
    }

# --------------------------------------------------
# توليد الرد (محمي بالتفعيل)
# --------------------------------------------------
@app.post("/generate")
def generate(
    data: AskRequest,
    x_token: str = Header(None, alias="X-Token")
):
    if not x_token:
        raise HTTPException(status_code=401, detail="Not activated")

    verify_jwt(x_token)

    # 🔹 ضع منطق الذكاء الاصطناعي هنا
    return {
        "answer": f"تم استلام الطلب بنجاح. النص: {data.prompt}"
    }