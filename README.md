# Cybertralaleritos Backend

API backend en Flask (MVP Fintech P2P). Persistencia en `data.json`. KYC con API Vudy (DUI/identidad).

## Requisitos

- Python 3.10+
- [GitHub CLI](https://cli.github.com/) (opcional)

## Entorno local

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
cp .env.example .env
pip install -r requirements.txt
python app.py
```

API en `http://127.0.0.1:5000`.

## Despliegue en Render

1. Conecta el repo de GitHub a Render (Web Service).
2. **Build Command:** `pip install -r requirements.txt`
3. **Start Command:** `gunicorn wsgi:app`
4. En **Environment** añade las variables que necesites:
   - `VUDY` – API key de Vudy (KYC).
   - `VUDY_API_URL` – (opcional) URL base de la API Vudy.
   - `KYC_REQUIRED` – `1` para exigir KYC antes de solicitar préstamos.

Render usa `wsgi:app` para evitar el conflicto entre el archivo `app.py` y el paquete `app/`.

## Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | /login | Body: `{ "email": "..." }` → devuelve usuario |
| GET | /user/<id> | Perfil y estado (saldo, límite) |
| POST | /request_loan | Body: `{ "user_id", "amount" }` |
| POST | /pay_loan | Body: `{ "user_id", "loan_id" }` |
| POST | /kyc/verify | Body: `{ "user_id", "dui" }` – verificación KYC con Vudy (DUI) |

## KYC (Vudy)

- Variable de entorno `VUDY`: API key de Vudy.
- Si no configuras `VUDY_API_URL`, en desarrollo se acepta cualquier DUI no vacío (≥4 caracteres) como verificado.
- Si configuras `VUDY_API_URL`, el backend llama a `POST {VUDY_API_URL}/verify` con `Authorization: Bearer {VUDY}` y body `{ "user_id", "dui" }`.

## Docker (opcional)

```bash
cp .env.example .env
docker compose up --build
```

## Repo

```bash
git remote add origin https://github.com/marchelo23/cybertralaleritosbackend.git
git push -u origin main
```
