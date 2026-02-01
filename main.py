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
JWT_SECRET = os.getenv("JWT_SECRET", "CHANGE_ME")
CODE_EXPIRY_DAYS = 30

app = FastAPI(title="Activation API")

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

# ======================
# HELPERS
# ======================
def generate_short_code():
    chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(random.choice(chars) for _ in range(6))

def verify_jwt(token: str):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        if payload.get("type") != "activation":
            raise HTTPException(status_code=401, detail="Invalid token type")
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid")

# ======================
# ROUTES
# ======================
@app.get("/")
def health():
    return {"status": "ok"}

# 🔹 توليد كود قصير (يُستخدم عدة مرات)
@app.get("/easy-code")
def easy_code():
    code = generate_short_code()

    token = jwt.encode(
        {
            "type": "activation",
            "code": code,
            "exp": datetime.datetime.utcnow()
            + datetime.timedelta(days=CODE_EXPIRY_DAYS)
        },
        JWT_SECRET,
        algorithm="HS256"
    )

    return {
        "activation_code": code,
        "token": token,
        "expires_in": f"{CODE_EXPIRY_DAYS} days"
    }

# 🔹 التحقق (بدون استهلاك)
@app.get("/verify")
def verify(x_token: str = Header(..., alias="X-Token")):
    verify_jwt(x_token)
    return {"status": "valid"}

# 🔹 الاستخدام الفعلي
@app.post("/generate")
def generate(
    data: AskRequest,
    x_token: str = Header(..., alias="X-Token")
):
    verify_jwt(x_token)

    return {
        "answer": f"تم التنفيذ بنجاح: {data.prompt}"
    }