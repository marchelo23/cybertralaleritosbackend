# app.py - Rutas y lógica fintech P2P (MVP Hackathon)
import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import db

load_dotenv()

app = Flask(__name__)
CORS(app)

INVESTOR_ID = 1  # Inversionista simulado global
CREDIT_LIMIT_CAP = 500
VUDY_API_KEY = os.environ.get("VUDY") or os.environ.get("VUDY_API_KEY")
VUDY_API_URL = os.environ.get("VUDY_API_URL", "").rstrip("/")
KYC_REQUIRED_FOR_LOAN = os.environ.get("KYC_REQUIRED", "0") == "1"


@app.route("/", methods=["GET"])
def index():
    return jsonify({"message": "Cybertralaleritos API", "docs": "POST /login, GET /user/<id>, POST /request_loan, POST /pay_loan, POST /kyc/verify, POST /vudy/deposit, POST /vudy/withdraw"})


@app.route("/healthz", methods=["GET"])
def healthz():
    """Health check para Render (Health Check Path: /healthz)."""
    return jsonify({"status": "ok"})


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    email = data.get("email")
    if not email:
        return jsonify({"error": "email required"}), 400
    user = db.get_user_by_email(email)
    if not user:
        return jsonify({"error": "user not found"}), 404
    return jsonify(user)


@app.route("/user/<int:uid>", methods=["GET"])
def user_profile(uid):
    user = db.get_user_by_id(uid)
    if not user:
        return jsonify({"error": "user not found"}), 404
    return jsonify(user)


@app.route("/request_loan", methods=["POST"])
def request_loan():
    data = request.get_json() or {}
    user_id = data.get("user_id")
    amount = data.get("amount")
    if user_id is None or amount is None:
        return jsonify({"error": "user_id and amount required"}), 400
    try:
        amount = float(amount)
    except (TypeError, ValueError):
        return jsonify({"error": "amount must be a number"}), 400
    if amount <= 0:
        return jsonify({"error": "amount must be positive"}), 400

    user = db.get_user_by_id(user_id)
    if not user:
        return jsonify({"error": "user not found"}), 404
    if user.get("type") != "borrower":
        return jsonify({"error": "only borrowers can request loans"}), 400
    if KYC_REQUIRED_FOR_LOAN and not user.get("kyc_verified"):
        return jsonify({"error": "KYC verification required before requesting a loan"}), 403
    credit_limit = user.get("credit_limit", 0)
    if amount > credit_limit:
        return jsonify({"error": "amount exceeds credit_limit", "credit_limit": credit_limit}), 400

    investor = db.get_user_by_id(INVESTOR_ID)
    if not investor or investor.get("balance", 0) < amount:
        return jsonify({"error": "insufficient investor funds"}), 400

    investor["balance"] = investor["balance"] - amount
    db.save_user(investor)
    loan = db.create_loan(borrower_id=user_id, amount=amount, investor_id=INVESTOR_ID)
    return jsonify({"ok": True, "loan": loan})


@app.route("/pay_loan", methods=["POST"])
def pay_loan():
    data = request.get_json() or {}
    user_id = data.get("user_id")
    loan_id = data.get("loan_id")
    if user_id is None or loan_id is None:
        return jsonify({"error": "user_id and loan_id required"}), 400

    user = db.get_user_by_id(user_id)
    if not user:
        return jsonify({"error": "user not found"}), 404
    loan = db.get_loan_by_id(loan_id)
    if not loan:
        return jsonify({"error": "loan not found"}), 404
    if loan.get("borrower_id") != user_id:
        return jsonify({"error": "loan does not belong to this user"}), 400
    if loan.get("status") == "paid":
        return jsonify({"error": "loan already paid"}), 400

    loan["status"] = "paid"
    db.update_loan(loan)

    successful_payments = user.get("successful_payments", 0) + 1
    user["successful_payments"] = successful_payments
    new_limit = user.get("credit_limit", 0) + (15 + 5 * successful_payments)
    user["credit_limit"] = min(new_limit, CREDIT_LIMIT_CAP)
    db.save_user(user)

    return jsonify({"ok": True, "user": user, "loan": loan})


def _verify_kyc_with_vudy(user_id: int, dui: str):
    """Llama a la API Vudy para verificar identidad (DUI). Devuelve (ok, mensaje)."""
    if not VUDY_API_KEY:
        return False, "VUDY_API_KEY not configured"
    if not VUDY_API_URL:
        # Sin URL configurada: modo dev, aceptamos DUI no vacío como verificado
        if dui and len(dui.strip()) >= 4:
            return True, "ok"
        return False, "dui required"
    try:
        import requests
        r = requests.post(
            f"{VUDY_API_URL}/verify",
            headers={"Authorization": f"Bearer {VUDY_API_KEY}", "Content-Type": "application/json"},
            json={"user_id": user_id, "dui": dui},
            timeout=15,
        )
        if r.status_code == 200:
            data = r.json() if r.content else {}
            if data.get("verified") is True or data.get("success") is True:
                return True, "ok"
            return False, data.get("message", "verification failed")
        return False, r.text or f"HTTP {r.status_code}"
    except Exception as e:
        return False, str(e)


@app.route("/kyc/verify", methods=["POST"])
def kyc_verify():
    """Verificación KYC con API Vudy (DUI/documento). Autentica que sea esa persona."""
    data = request.get_json() or {}
    user_id = data.get("user_id")
    dui = data.get("dui") or data.get("document_id") or ""
    if user_id is None:
        return jsonify({"error": "user_id required"}), 400
    if not isinstance(dui, str):
        dui = str(dui).strip()
    user = db.get_user_by_id(user_id)
    if not user:
        return jsonify({"error": "user not found"}), 404
    if user.get("kyc_verified"):
        return jsonify({"ok": True, "message": "already verified", "user": user})
    ok, msg = _verify_kyc_with_vudy(user_id, dui)
    if not ok:
        return jsonify({"error": "KYC verification failed", "detail": msg}), 400
    user["kyc_verified"] = True
    db.save_user(user)
    return jsonify({"ok": True, "message": "KYC verified", "user": user})


def _vudy_request(method, path, json_body=None):
    """Llama a la API Vudy. Devuelve (ok, data o error_msg)."""
    if not VUDY_API_KEY:
        return False, "VUDY not configured"
    if not VUDY_API_URL:
        return False, "VUDY_API_URL not configured"
    try:
        import requests
        url = f"{VUDY_API_URL.rstrip('/')}{path}"
        r = requests.request(
            method,
            url,
            headers={"Authorization": f"Bearer {VUDY_API_KEY}", "Content-Type": "application/json"},
            json=json_body,
            timeout=15,
        )
        if r.status_code in (200, 201):
            return True, r.json() if r.content else {}
        return False, r.text or f"HTTP {r.status_code}"
    except Exception as e:
        return False, str(e)


@app.route("/vudy/deposit", methods=["POST"])
def vudy_deposit():
    """Guardar pisto en Vudy: envía amount desde el usuario a Vudy."""
    data = request.get_json() or {}
    user_id = data.get("user_id")
    amount = data.get("amount")
    if user_id is None or amount is None:
        return jsonify({"error": "user_id and amount required"}), 400
    try:
        amount = float(amount)
    except (TypeError, ValueError):
        return jsonify({"error": "amount must be a number"}), 400
    if amount <= 0:
        return jsonify({"error": "amount must be positive"}), 400
    user = db.get_user_by_id(user_id)
    if not user:
        return jsonify({"error": "user not found"}), 404
    balance = user.get("balance", 0)
    if balance < amount:
        return jsonify({"error": "insufficient balance", "balance": balance}), 400
    if VUDY_API_URL:
        ok, result = _vudy_request("POST", "/deposit", {"user_id": user_id, "amount": amount})
        if not ok:
            return jsonify({"error": "Vudy deposit failed", "detail": result}), 502
    user["balance"] = balance - amount
    user["vudy_balance"] = user.get("vudy_balance", 0) + amount
    db.save_user(user)
    return jsonify({"ok": True, "message": "deposit sent to Vudy", "user": user})


@app.route("/vudy/withdraw", methods=["POST"])
def vudy_withdraw():
    """Jalar pisto desde Vudy: trae amount desde Vudy al usuario."""
    data = request.get_json() or {}
    user_id = data.get("user_id")
    amount = data.get("amount")
    if user_id is None or amount is None:
        return jsonify({"error": "user_id and amount required"}), 400
    try:
        amount = float(amount)
    except (TypeError, ValueError):
        return jsonify({"error": "amount must be a number"}), 400
    if amount <= 0:
        return jsonify({"error": "amount must be positive"}), 400
    user = db.get_user_by_id(user_id)
    if not user:
        return jsonify({"error": "user not found"}), 404
    vudy_balance = user.get("vudy_balance", 0)
    if vudy_balance < amount:
        return jsonify({"error": "insufficient Vudy balance", "vudy_balance": vudy_balance}), 400
    if VUDY_API_URL:
        ok, result = _vudy_request("POST", "/withdraw", {"user_id": user_id, "amount": amount})
        if not ok:
            return jsonify({"error": "Vudy withdraw failed", "detail": result}), 502
    user["vudy_balance"] = vudy_balance - amount
    user["balance"] = user.get("balance", 0) + amount
    db.save_user(user)
    return jsonify({"ok": True, "message": "withdraw from Vudy", "user": user})


if __name__ == "__main__":
    db._load()  # crea data.json si no existe
    app.run(host="0.0.0.0", port=5000, debug=True)  # debug=False si hay PermissionError en /dev/shm
