# app.py - Rutas y lógica fintech P2P (MVP Hackathon)
from flask import Flask, request, jsonify
from flask_cors import CORS
import db

app = Flask(__name__)
CORS(app)

INVESTOR_ID = 1  # Inversionista simulado global
CREDIT_LIMIT_CAP = 500


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


if __name__ == "__main__":
    db._load()  # crea data.json si no existe
    app.run(host="0.0.0.0", port=5000, debug=True)  # debug=False si hay PermissionError en /dev/shm
