import os, json, random, string, datetime, jwt
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# ================== CONFIG ==================
JWT_SECRET = os.getenv("JWT_SECRET")
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN")
CODE_DAYS = 30
CODES_FILE = "codes.json"

if not JWT_SECRET or not ADMIN_TOKEN:
    raise RuntimeError("Missing ENV variables")

# ================== APP ==================
app = FastAPI(title="Activation Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ================== HELPERS ==================
def load_codes():
    if not os.path.exists(CODES_FILE):
        return {}
    with open(CODES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_codes(data):
    with open(CODES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def generate_short_code(length=6):
    chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(random.choice(chars) for _ in range(length))

def create_jwt():
    payload = {
        "type": "activation",
        "exp": datetime.datetime.utcnow() + datetime.timedelta(days=CODE_DAYS)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

# ================== ROUTES ==================
@app.get("/")
def health():
    return {"status": "ok"}

# -------- ADMIN: CREATE CODE --------
@app.get("/admin/create-code")
def create_code(key: str):
    if key != ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Forbidden")

    codes = load_codes()

    code = generate_short_code()
    while code in codes:
        code = generate_short_code()

    expires = (datetime.datetime.utcnow() + datetime.timedelta(days=CODE_DAYS)).isoformat()

    codes[code] = {
        "used": False,
        "expires": expires
    }
    save_codes(codes)

    return {
        "activation_code": code,
        "expires_in": f"{CODE_DAYS} days"
    }

# -------- ADMIN: LIST CODES --------
@app.get("/admin/codes")
def list_codes(key: str):
    if key != ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Forbidden")
    return load_codes()

# -------- VERIFY SHORT CODE (ONE TIME) --------
@app.post("/verify")
def verify_code(x_code: str = Header(..., alias="X-Code")):
    codes = load_codes()

    if x_code not in codes:
        raise HTTPException(status_code=401, detail="INVALID_CODE")

    record = codes[x_code]

    if record["used"]:
        raise HTTPException(status_code=401, detail="CODE_ALREADY_USED")

    if datetime.datetime.utcnow() > datetime.datetime.fromisoformat(record["expires"]):
        raise HTTPException(status_code=401, detail="CODE_EXPIRED")

    # mark as used
    codes[x_code]["used"] = True
    save_codes(codes)

    token = create_jwt()

    return {
        "token": token,
        "expires_in": f"{CODE_DAYS} days"
    }

# -------- PROTECTED AI ENDPOINT --------
@app.post("/generate")
def generate(x_token: str = Header(..., alias="X-Token")):
    try:
        payload = jwt.decode(x_token, JWT_SECRET, algorithms=["HS256"])
        if payload.get("type") != "activation":
            raise Exception()
    except:
        raise HTTPException(status_code=401, detail="INVALID_TOKEN")

    return {
        "answer": "تم التحقق بنجاح – الذكاء الاصطناعي يعمل"
    }