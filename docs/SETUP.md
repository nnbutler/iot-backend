# Developer Setup Guide

## Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Docker Desktop | Latest | [docker.com/get-started](https://www.docker.com/get-started) |
| Python | 3.11+ | System or [pyenv](https://github.com/pyenv/pyenv) |
| Node.js | 18+ | See note below |
| Git | Any | System |

### Node.js on WSL2 (important)

If you're on Windows with WSL2, **do not rely on the Windows Node.js installation**. The Windows `node`/`npm` binaries are reachable from WSL but they spawn `CMD.EXE` for lifecycle scripts, which cannot handle UNC paths (`\\wsl.localhost\...`) — `npm test`, `npm run dev`, etc. will fail.

Install Node natively inside WSL using [nvm](https://github.com/nvm-sh/nvm):

```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
# Restart your terminal, then:
nvm install 20
nvm use 20
node --version   # should show v20.x.x
```

Verify you're using the WSL-native binary, not the Windows one:

```bash
which node   # should be /home/<user>/.nvm/versions/node/v20.x.x/bin/node
             # NOT /mnt/c/Program Files/nodejs/node.exe
```

---

## Quick Start (Docker)

The fastest way to get everything running:

```bash
# 1. Copy the environment file
cp .env.example .env          # or create .env — see Environment Variables below

# 2. Start all services
docker compose up --build

# Services:
#   postgres  → localhost:5432
#   backend   → localhost:8000
#   frontend  → localhost:5173
```

---

## Environment Variables

Create a `.env` file in the project root:

```env
DB_USER=postgres
DB_PASSWORD=postgres
DB_NAME=device_manager
DATABASE_URL=postgresql+psycopg://postgres:postgres@postgres:5432/device_manager
```

For local (non-Docker) backend development, change the host:

```env
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/device_manager
```

---

## Backend (Python / FastAPI)

### Local setup

```bash
cd backend
python -m venv venv
source venv/bin/activate      # Windows WSL: same command
pip install -r requirements.txt
```

### Run locally

Requires a running PostgreSQL instance (Docker is easiest):

```bash
docker compose up postgres -d
uvicorn app.main:app --reload --port 8000
```

### Run tests

```bash
cd backend
pytest
pytest --cov=app tests/        # with coverage
```

### Linting / formatting

```bash
ruff check .
black .
mypy app/
```

---

## Frontend (React / Vite)

### Local setup

Requires Node 18+ (see WSL note above).

```bash
cd frontend
npm install
```

### Run dev server

```bash
npm run dev
# App available at http://localhost:5173
```

The Vite config binds to `0.0.0.0` so it's accessible from the Windows browser when running in WSL.

### Run tests

```bash
npm test
```

Tests use Jest + React Testing Library. To run in watch mode:

```bash
npm run test:watch
```

### Build for production

```bash
npm run build
```

---

## Database

The database schema and seed data are applied automatically when the `postgres` container first starts via `scripts/init-db.sql`.

To reset the database (wipe volume and re-init):

```bash
docker compose down -v
docker compose up postgres -d
```

See [docs/DATABASE.md](DATABASE.md) for full schema documentation.

---

## Project Structure

```
iot-backend/
├── backend/              # FastAPI app (Python 3.11)
│   ├── app/              # Application source
│   ├── tests/            # Pytest test suite
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/             # React + Vite app
│   ├── src/
│   │   ├── api/          # Axios client
│   │   ├── components/   # Shared components
│   │   ├── pages/        # Route-level pages
│   │   └── utils/        # Pure helpers (formatting, etc.)
│   ├── package.json
│   └── Dockerfile
├── scripts/
│   └── init-db.sql       # Schema + seed data
├── docs/
│   ├── SETUP.md          # This file
│   ├── DATABASE.md       # Schema reference
│   └── PLAN.md
└── docker-compose.yml
```

---

## Common Issues

**`npm test` fails with "UNC paths are not supported"**
You're using the Windows Node.js from WSL. See the [Node.js on WSL2](#nodejs-on-wsl2-important) section above.

**`npm test` fails with "jest: command not found"**
Run `npm install` first. The `node_modules` directory is not committed to git.

**Port already in use**
Check for conflicting processes: `lsof -i :8000` or `lsof -i :5173`. Stop them or change the port in `docker-compose.yml`.

**Database connection refused**
Ensure the `postgres` container is healthy before starting the backend: `docker compose up postgres -d && docker compose up backend`.
