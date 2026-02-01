import os
import sqlite3
import random
import string
import datetime
import jwt

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ======================
# ENV
# ======================
JWT_SECRET = os.getenv("JWT_SECRET", "CHANGE_ME_SECRET")

DB_FILE = "activation.db"
CODE_EXPIRY_DAYS = 30

# ======================
# APP
# ======================
app = FastAPI(title="AI Activation Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ======================
# DB INIT
# ======================
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS activation_codes (
            code TEXT PRIMARY KEY,
            expires_at TEXT,
            used INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ======================
# HELPERS
# ======================
def generate_short_code(length=6):
    chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(random.choice(chars) for _ in range(length))

def create_jwt():
    payload = {
        "type": "activation",
        "exp": datetime.datetime.utcnow() + datetime.timedelta(days=CODE_EXPIRY_DAYS)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

def verify_jwt(token: str):
    try:
        jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# ======================
# MODELS
# ======================
class ActivateRequest(BaseModel):
    code: str

class AskRequest(BaseModel):
    prompt: str

# ======================
# ROUTES
# ======================

@app.get("/")
def health():
    return {"status": "ok"}

# ---------- إنشاء كود تفعيل قصير ----------
@app.get("/admin/create-code")
def create_code():
    code = generate_short_code()
    expires = (datetime.datetime.utcnow() + datetime.timedelta(days=CODE_EXPIRY_DAYS)).isoformat()

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO activation_codes (code, expires_at) VALUES (?, ?)",
        (code, expires)
    )
    conn.commit()
    conn.close()

    return {
        "activation_code": code,
        "expires_in": f"{CODE_EXPIRY_DAYS} days"
    }

# ---------- تفعيل الكود (تحويله إلى JWT) ----------
@app.post("/activate")
def activate(data: ActivateRequest):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    cur.execute(
        "SELECT expires_at, used FROM activation_codes WHERE code = ?",
        (data.code.strip().upper(),)
    )
    row = cur.fetchone()

    if not row:
        conn.close()
        raise HTTPException(status_code=401, detail="Invalid code")

    expires_at, used = row

    if used:
        conn.close()
        raise HTTPException(status_code=401, detail="Code already used")

    if datetime.datetime.fromisoformat(expires_at) < datetime.datetime.utcnow():
        conn.close()
        raise HTTPException(status_code=401, detail="Code expired")

    # نعلّم الكود كمستخدم
    cur.execute(
        "UPDATE activation_codes SET used = 1 WHERE code = ?",
        (data.code.strip().upper(),)
    )
    conn.commit()
    conn.close()

    token = create_jwt()

    return {
        "token": token,
        "expires_in": f"{CODE_EXPIRY_DAYS} days"
    }

# ---------- الذكاء الاصطناعي ----------
@app.post("/generate")
def generate(
    data: AskRequest,
    x_token: str = Header(..., alias="X-Token")
):
    verify_jwt(x_token)

    # 🔹 هنا منطق Gemini / AI الحقيقي
    return {
        "answer": f"✅ تم التوليد بنجاح\n\n{data.prompt}"
    }