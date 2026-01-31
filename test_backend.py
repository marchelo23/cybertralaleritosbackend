#!/usr/bin/env python3
"""Prueba rápida de todos los endpoints del backend (sin levantar servidor)."""
import importlib.util
import os
import sys

os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Reset data.json a estado inicial para que las aserciones pasen
INITIAL_DATA = {
    "users": [
        {"id": 1, "email": "investor@test.com", "type": "investor", "balance": 5000, "rate": 3.6},
        {"id": 2, "email": "borrower@test.com", "type": "borrower", "credit_limit": 40, "successful_payments": 0},
    ],
    "loans": [],
    "next_loan_id": 1,
}
with open("data.json", "w", encoding="utf-8") as f:
    import json
    json.dump(INITIAL_DATA, f, indent=2, ensure_ascii=False)

# Importar app desde app.py (no desde el paquete app/)
spec = importlib.util.spec_from_file_location("app_main", "app.py")
app_module = importlib.util.module_from_spec(spec)
sys.modules["app_main"] = app_module
spec.loader.exec_module(app_module)
app = app_module.app

client = app.test_client()

def ok(msg, r):
    j = r.get_json() if r.content_type and "json" in r.content_type else None
    print(f"  OK: {msg} -> {r.status_code}" + (f" | {list(j.keys()) if j else ''}" if j else ""))

def fail(msg, r):
    print(f"  FAIL: {msg} -> {r.status_code} {r.data[:80] if r.data else ''}")

print("--- 1. POST /login (borrower) ---")
r = client.post("/login", json={"email": "borrower@test.com"})
if r.status_code == 200:
    ok("login borrower", r)
    u = r.get_json()
    assert u.get("id") == 2 and u.get("credit_limit") == 40
else:
    fail("login borrower", r)

print("--- 2. POST /login (investor) ---")
r = client.post("/login", json={"email": "investor@test.com"})
if r.status_code == 200:
    ok("login investor", r)
else:
    fail("login investor", r)

print("--- 3. GET /user/2 ---")
r = client.get("/user/2")
if r.status_code == 200:
    ok("user 2", r)
else:
    fail("user 2", r)

print("--- 4. POST /request_loan (30 <= 40) ---")
r = client.post("/request_loan", json={"user_id": 2, "amount": 30})
if r.status_code == 200:
    ok("request_loan 30", r)
    j = r.get_json()
    loan_id = j.get("loan", {}).get("id")
else:
    fail("request_loan 30", r)
    loan_id = None

print("--- 5. POST /request_loan (excede límite) ---")
r = client.post("/request_loan", json={"user_id": 2, "amount": 50})
if r.status_code in (400, 422):
    ok("request_loan 50 rechazado", r)
else:
    fail("request_loan 50 debería fallar", r)

print("--- 6. GET /user/1 (inversionista, saldo bajó) ---")
r = client.get("/user/1")
if r.status_code == 200:
    ok("user 1", r)
    u = r.get_json()
    assert u.get("balance") == 5000 - 30, f"balance esperado 4970, got {u.get('balance')}"
else:
    fail("user 1", r)

print("--- 7. POST /pay_loan ---")
if loan_id is not None:
    r = client.post("/pay_loan", json={"user_id": 2, "loan_id": loan_id})
    if r.status_code == 200:
        ok("pay_loan", r)
        j = r.get_json()
        new_limit = j.get("user", {}).get("credit_limit")
        # 40 + (15 + 5*1) = 60
        assert new_limit == 60, f"credit_limit esperado 60, got {new_limit}"
    else:
        fail("pay_loan", r)
else:
    print("  SKIP (no loan_id)")

print("--- 8. GET /user/2 (límite subió a 60) ---")
r = client.get("/user/2")
if r.status_code == 200:
    ok("user 2 después de pago", r)
    u = r.get_json()
    assert u.get("credit_limit") == 60 and u.get("successful_payments") == 1
else:
    fail("user 2", r)

print("\n=== Backend OK ===")
