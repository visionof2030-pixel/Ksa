import os
import random
import datetime
import jwt

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ======================
# CONFIG
# ======================
JWT_SECRET = os.getenv("JWT_SECRET", "CHANGE_ME_SECRET")
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "ADMIN123")

CODE_EXPIRY_DAYS = 30

# ======================
# APP
# ======================
app = FastAPI(title="Activation Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ======================
# HELPERS
# ======================
def generate_short_code(length=6):
    chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(random.choice(chars) for _ in range(length))


def jwt_from_code(code: str):
    payload = {
        "type": "activation",
        "code": code,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(days=CODE_EXPIRY_DAYS)
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
    return {"status": "ok"}

# 🔑 توليد كود قصير (للمشرف فقط)
@app.get("/generate-code")
def generate_code(key: str):
    if key != ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Forbidden")

    code = generate_short_code()
    return {
        "activation_code": code,
        "expires_in": f"{CODE_EXPIRY_DAYS} days"
    }

# ✅ تفعيل (الكود القصير → JWT)
@app.post("/activate")
def activate(code: str):
    if not code or len(code) < 4:
        raise HTTPException(status_code=400, detail="Invalid code")

    token = jwt_from_code(code)

    return {
        "token": token,
        "expires_in": f"{CODE_EXPIRY_DAYS} days"
    }

# ✅ تحقق من JWT
@app.get("/verify")
def verify(x_token: str = Header(..., alias="X-Token")):
    verify_jwt(x_token)
    return {"status": "valid"}