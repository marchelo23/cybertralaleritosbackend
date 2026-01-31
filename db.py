# db.py - Persistencia en data.json (sin SQL)
import json
import os

DATA_FILE = "data.json"

DUMMY = {
    "users": [
        {"id": 1, "email": "investor@test.com", "type": "investor", "balance": 5000, "rate": 3.6, "vudy_balance": 0},
        {"id": 2, "email": "borrower@test.com", "type": "borrower", "credit_limit": 40, "successful_payments": 0, "kyc_verified": False},
    ],
    "loans": [],
    "next_loan_id": 1,
}


def _load():
    if not os.path.exists(DATA_FILE):
        _save(DUMMY)
        return DUMMY.copy()
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_users():
    return _load()["users"]


def get_user_by_id(uid):
    users = get_users()
    for u in users:
        if u["id"] == uid:
            return u
    return None


def get_user_by_email(email):
    users = get_users()
    for u in users:
        if u.get("email") == email:
            return u
    return None


def save_user(user):
    data = _load()
    users = data["users"]
    for i, u in enumerate(users):
        if u["id"] == user["id"]:
            users[i] = user
            break
    else:
        users.append(user)
    data["users"] = users
    _save(data)


def get_loans():
    return _load()["loans"]


def get_loan_by_id(loan_id):
    for loan in get_loans():
        if loan["id"] == loan_id:
            return loan
    return None


def create_loan(borrower_id, amount, investor_id):
    data = _load()
    lid = data["next_loan_id"]
    loan = {
        "id": lid,
        "borrower_id": borrower_id,
        "investor_id": investor_id,
        "amount": amount,
        "status": "active",
    }
    data["loans"].append(loan)
    data["next_loan_id"] = lid + 1
    _save(data)
    return loan


def update_loan(loan):
    data = _load()
    for i, L in enumerate(data["loans"]):
        if L["id"] == loan["id"]:
            data["loans"][i] = loan
            break
    _save(data)
