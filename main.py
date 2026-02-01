import express from "express";
import cors from "cors";
import jwt from "jsonwebtoken";

const app = express();
app.use(cors());
app.use(express.json());

/* ================== الإعدادات ================== */
const PORT = process.env.PORT || 3000;
const JWT_SECRET = "CHANGE_THIS_SECRET_123"; // غيّره
const CODE_EXPIRY_DAYS = 30;

/* ================== توليد كود قصير ================== */
function generateShortCode() {
  const chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";
  let code = "";
  for (let i = 0; i < 6; i++) {
    code += chars[Math.floor(Math.random() * chars.length)];
  }
  return code;
}

/* ================== توليد كود تفعيل (مرة واحدة) ================== */
/*
  استخدم هذا فقط عند البيع أو الإنشاء
  شغّله يدويًا ثم خزّن الكود عندك
*/
app.get("/generate", (req, res) => {
  const shortCode = generateShortCode();

  const token = jwt.sign(
    {
      type: "activation",
      code: shortCode
    },
    JWT_SECRET,
    { expiresIn: `${CODE_EXPIRY_DAYS}d` }
  );

  res.json({
    activation_code: shortCode,
    expires_in: `${CODE_EXPIRY_DAYS} days`
  });
});

/* ================== التحقق من التفعيل ================== */
app.get("/verify", (req, res) => {
  const code = req.headers["x-token"];

  if (!code) {
    return res.status(401).json({ error: "NO_CODE" });
  }

  try {
    // نفك التوكن الأصلي
    const decoded = jwt.verify(code, JWT_SECRET);

    if (decoded.type !== "activation") {
      return res.status(403).json({ error: "INVALID_TYPE" });
    }

    res.json({
      status: "valid"
    });

  } catch (err) {
    return res.status(403).json({ error: "INVALID_OR_EXPIRED" });
  }
});

/* ================== API الذكاء الاصطناعي ================== */
app.post("/generate", (req, res) => {
  const token = req.headers["x-token"];
  if (!token) {
    return res.status(401).json({ error: "NOT_ACTIVATED" });
  }

  try {
    jwt.verify(token, JWT_SECRET);
  } catch {
    return res.status(403).json({ error: "INVALID_TOKEN" });
  }

  // 🔹 هنا ضع منطق الذكاء الاصطناعي الخاص بك
  res.json({
    answer: "نص تجريبي صادر من الذكاء الاصطناعي"
  });
});

/* ================== تشغيل السيرفر ================== */
app.listen(PORT, () => {
  console.log(`✅ Server running on port ${PORT}`);
});
