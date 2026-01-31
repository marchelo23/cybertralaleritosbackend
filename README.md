# Cybertralaleritos Backend

API backend en Flask con Docker.

## Requisitos

- Python 3.12+
- Docker y Docker Compose (opcional)
- [GitHub CLI](https://cli.github.com/) (para conectar al repo)

## Conexión al repositorio (GitHub CLI)

Si aún no estás autenticado:

```bash
gh auth login -h github.com
```

Si el proyecto ya está en tu máquina y quieres vincularlo al repo remoto:

```bash
git init
git remote add origin https://github.com/marchelo23/cybertralaleritosbackend.git
git branch -M main
git add .
git commit -m "Initial Flask + Docker setup"
git push -u origin main
```

Para clonar el repo en otra carpeta:

```bash
gh repo clone marchelo23/cybertralaleritosbackend
cd cybertralaleritosbackend
```

## Entorno local (sin Docker)

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
cp .env.example .env
pip install -r requirements.txt
flask --app wsgi run
```

API en `http://127.0.0.1:5000`. Endpoints: `GET /api/`, `GET /api/health`.

## Con Docker

```bash
cp .env.example .env
docker compose up --build
```

API en `http://localhost:5000`.

## Endpoints

| Método | Ruta         | Descripción      |
|--------|--------------|------------------|
| GET    | /api/        | Mensaje de bienvenida |
| GET    | /api/health  | Health check     |
