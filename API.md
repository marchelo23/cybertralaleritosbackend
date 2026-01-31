# Cybertralaleritos Backend — Documentación

Documentación del proyecto y de los endpoints de la API.

---

## 1. Descripción del proyecto

**Cybertralaleritos Backend** es un MVP de fintech de préstamos P2P (peer-to-peer). Permite:

- **Login** por email (simulado).
- **Perfil de usuario** (saldo, límite de crédito).
- **Solicitar préstamos** (prestatarios) respetando límite de crédito.
- **Pagar préstamos** y subir el límite según pagos exitosos.
- **KYC** (verificación de identidad / DUI) vía API Vudy.
- **Depósito y retiro** de fondos en/desde Vudy (guardar/jalar pisto).

**Persistencia:** archivo local `data.json` (sin base de datos SQL).

**Stack:** Flask, Flask-CORS, python-dotenv, gunicorn, requests.

---

## 2. Arquitectura

```
backend/
├── app.py          # Rutas y lógica de la API
├── db.py           # Lectura/escritura de data.json
├── data.json       # Datos (usuarios, préstamos)
├── wsgi.py         # Entrada para Gunicorn (opcional)
├── requirements.txt
├── .env            # Variables de entorno (no se sube)
└── API.md          # Esta documentación
```

- **app.py:** define todos los endpoints y reglas de negocio.
- **db.py:** carga/guarda `data.json`; si no existe, crea datos dummy (1 inversionista, 1 prestatario).

---

## 3. Variables de entorno

| Variable        | Descripción |
|----------------|-------------|
| `VUDY`         | API key de Vudy (KYC y depósito/retiro). |
| `VUDY_API_URL` | (Opcional) URL base de la API Vudy. Si no se setea, se usa modo simulado/local. |
| `KYC_REQUIRED` | `1` = exigir usuario con KYC verificado para solicitar préstamos; `0` = no exigir. |
| `SECRET_KEY`   | (Opcional) Para sesiones/extensiones Flask. |
| `DEBUG`        | (Opcional) `1` para modo debug. |

---

## 4. Modelos de datos

### Usuario (`user`)

| Campo               | Tipo   | Descripción |
|---------------------|--------|-------------|
| `id`                | int    | ID único. |
| `email`             | string | Email (login). |
| `type`              | string | `"investor"` o `"borrower"`. |
| `balance`           | float  | Saldo (inversionista). |
| `rate`              | float  | Tasa (inversionista). |
| `credit_limit`      | float  | Límite de crédito (prestatario). |
| `successful_payments`| int    | Cantidad de préstamos pagados (prestatario). |
| `kyc_verified`      | bool   | Si pasó verificación KYC. |
| `vudy_balance`      | float  | Saldo “en Vudy” (depósitos menos retiros). |

### Préstamo (`loan`)

| Campo        | Tipo   | Descripción |
|--------------|--------|-------------|
| `id`         | int    | ID único. |
| `borrower_id`| int    | ID del prestatario. |
| `investor_id`| int    | ID del inversionista. |
| `amount`     | float  | Monto. |
| `status`     | string | `"active"` o `"paid"`. |

---

## 5. Base URL

- **Local:** `http://127.0.0.1:5000`
- **Render:** `https://cybertralaleritosbackend-1.onrender.com` (o la URL de tu servicio)

Todas las rutas devuelven **JSON**. Cabecera recomendada: `Content-Type: application/json`.

---

## 6. Endpoints

### 6.1 Raíz y salud

#### `GET /`

Información básica de la API.

**Respuesta 200**

```json
{
  "message": "Cybertralaleritos API",
  "docs": "POST /login, GET /user/<id>, ..."
}
```

---

#### `GET /healthz`

Health check (p. ej. para Render).

**Respuesta 200**

```json
{
  "status": "ok"
}
```

---

### 6.2 Autenticación y usuario

#### `POST /login`

Login por email (simulado). Devuelve el usuario si existe.

**Body (JSON)**

| Campo   | Tipo   | Requerido | Descripción |
|---------|--------|-----------|-------------|
| `email` | string | Sí        | Email del usuario. |

**Ejemplo**

```json
{
  "email": "borrower@test.com"
}
```

**Respuesta 200** — Usuario encontrado

```json
{
  "id": 2,
  "email": "borrower@test.com",
  "type": "borrower",
  "credit_limit": 40,
  "successful_payments": 0,
  "kyc_verified": false
}
```

**Respuesta 400** — Falta email

```json
{
  "error": "email required"
}
```

**Respuesta 404** — Usuario no encontrado

```json
{
  "error": "user not found"
}
```

---

#### `GET /user/<id>`

Obtiene el perfil y estado del usuario (saldo, límite, etc.).

**Parámetros de ruta**

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `id`      | int  | ID del usuario. |

**Respuesta 200**

```json
{
  "id": 2,
  "email": "borrower@test.com",
  "type": "borrower",
  "credit_limit": 40,
  "successful_payments": 0,
  "kyc_verified": false
}
```

**Respuesta 404**

```json
{
  "error": "user not found"
}
```

---

### 6.3 Préstamos

#### `POST /request_loan`

Solicita un préstamo (solo prestatarios). Se valida `amount <= credit_limit` y que el inversionista tenga saldo.

**Body (JSON)**

| Campo    | Tipo  | Requerido | Descripción |
|----------|-------|-----------|-------------|
| `user_id`| int   | Sí        | ID del prestatario. |
| `amount` | float | Sí        | Monto a solicitar. |

**Ejemplo**

```json
{
  "user_id": 2,
  "amount": 30
}
```

**Respuesta 200**

```json
{
  "ok": true,
  "loan": {
    "id": 1,
    "borrower_id": 2,
    "investor_id": 1,
    "amount": 30,
    "status": "active"
  }
}
```

**Posibles errores**

- **400** — `user_id and amount required`, `amount must be a number`, `amount must be positive`, `amount exceeds credit_limit` (incluye `credit_limit` en el body).
- **403** — `KYC verification required before requesting a loan` (si `KYC_REQUIRED=1` y el usuario no está verificado).
- **404** — `user not found`.
- **400** — `only borrowers can request loans`, `insufficient investor funds`.

---

#### `POST /pay_loan`

Marca un préstamo como pagado y actualiza el límite del prestatario:  
`nuevo_límite = anterior + (15 + 5 * pagos_exitosos)`, con tope 500.

**Body (JSON)**

| Campo    | Tipo | Requerido | Descripción |
|----------|-----|-----------|-------------|
| `user_id`| int | Sí        | ID del prestatario. |
| `loan_id`| int | Sí        | ID del préstamo. |

**Ejemplo**

```json
{
  "user_id": 2,
  "loan_id": 1
}
```

**Respuesta 200**

```json
{
  "ok": true,
  "user": { ... },
  "loan": {
    "id": 1,
    "borrower_id": 2,
    "investor_id": 1,
    "amount": 30,
    "status": "paid"
  }
}
```

**Posibles errores**

- **400** — `user_id and loan_id required`, `loan does not belong to this user`, `loan already paid`.
- **404** — `user not found`, `loan not found`.

---

### 6.4 KYC (Vudy)

#### `POST /kyc/verify`

Verificación de identidad (KYC) con DUI/documento. Usa la API Vudy si está configurada; si no, en desarrollo acepta DUI no vacío (≥4 caracteres).

**Body (JSON)**

| Campo         | Tipo   | Requerido | Descripción |
|---------------|--------|-----------|-------------|
| `user_id`     | int    | Sí        | ID del usuario. |
| `dui`         | string | Sí*       | Número de documento (DUI). |
| `document_id` | string | No        | Alias de `dui`. |

**Ejemplo**

```json
{
  "user_id": 2,
  "dui": "12345678-9"
}
```

**Respuesta 200** — Verificado o ya estaba verificado

```json
{
  "ok": true,
  "message": "KYC verified",
  "user": { ... }
}
```

**Posibles errores**

- **400** — `user_id required`, `KYC verification failed` (incluye `detail`).
- **404** — `user not found`.

---

### 6.5 Vudy — Depósito y retiro

#### `POST /vudy/deposit`

Guarda pisto en Vudy: resta `amount` del `balance` del usuario y lo suma a `vudy_balance`. Si está configurada `VUDY_API_URL`, además llama a la API Vudy.

**Body (JSON)**

| Campo    | Tipo  | Requerido | Descripción |
|----------|-------|-----------|-------------|
| `user_id`| int   | Sí        | ID del usuario. |
| `amount` | float | Sí        | Monto a depositar. |

**Ejemplo**

```json
{
  "user_id": 1,
  "amount": 100
}
```

**Respuesta 200**

```json
{
  "ok": true,
  "message": "deposit sent to Vudy",
  "user": { ... }
}
```

**Posibles errores**

- **400** — `user_id and amount required`, `amount must be a number`, `amount must be positive`, `insufficient balance` (incluye `balance`).
- **404** — `user not found`.
- **502** — `Vudy deposit failed` (si la API Vudy falla).

---

#### `POST /vudy/withdraw`

Jala pisto desde Vudy: resta `amount` de `vudy_balance` y lo suma al `balance` del usuario. Si está configurada `VUDY_API_URL`, además llama a la API Vudy.

**Body (JSON)**

| Campo    | Tipo  | Requerido | Descripción |
|----------|-------|-----------|-------------|
| `user_id`| int   | Sí        | ID del usuario. |
| `amount` | float | Sí        | Monto a retirar. |

**Ejemplo**

```json
{
  "user_id": 1,
  "amount": 50
}
```

**Respuesta 200**

```json
{
  "ok": true,
  "message": "withdraw from Vudy",
  "user": { ... }
}
```

**Posibles errores**

- **400** — `user_id and amount required`, `amount must be a number`, `amount must be positive`, `insufficient Vudy balance` (incluye `vudy_balance`).
- **404** — `user not found`.
- **502** — `Vudy withdraw failed` (si la API Vudy falla).

---

## 7. Resumen de endpoints

| Método | Ruta            | Descripción |
|--------|-----------------|-------------|
| GET    | `/`             | Info de la API. |
| GET    | `/healthz`      | Health check. |
| POST   | `/login`        | Login por email. |
| GET    | `/user/<id>`    | Perfil de usuario. |
| POST   | `/request_loan` | Solicitar préstamo. |
| POST   | `/pay_loan`     | Pagar préstamo. |
| POST   | `/kyc/verify`   | Verificación KYC (DUI). |
| POST   | `/vudy/deposit` | Guardar pisto en Vudy. |
| POST   | `/vudy/withdraw`| Jalar pisto desde Vudy. |

---

## 8. Formato de errores

Las respuestas de error son JSON con al menos:

```json
{
  "error": "mensaje corto"
}
```

Algunos endpoints añaden campos extra (p. ej. `credit_limit`, `balance`, `detail`).

**Códigos HTTP habituales**

- **400** — Bad Request (validación, datos incorrectos).
- **403** — Forbidden (p. ej. KYC requerido).
- **404** — Not Found (usuario o préstamo no existe).
- **502** — Bad Gateway (fallo al llamar a la API Vudy).

---

## 9. Despliegue (Render)

- **Build command:** `pip install -r requirements.txt`
- **Start command:** `gunicorn app:app`
- **Health Check Path:** `/healthz`

Variables de entorno recomendadas en Render: `VUDY`, `VUDY_API_URL` (opcional), `KYC_REQUIRED` (opcional).

---

## 10. Datos de prueba (data.json)

Por defecto se crean:

- **Usuario 1 (inversionista):** `investor@test.com`, balance 5000, tasa 3.6 %, `vudy_balance` 0.
- **Usuario 2 (prestatario):** `borrower@test.com`, `credit_limit` 40, `successful_payments` 0, `kyc_verified` false.

Si borras `data.json` y reinicias, se regenera con estos datos.
