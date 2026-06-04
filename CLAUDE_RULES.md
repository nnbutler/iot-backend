# CLAUDE_RULES.md - Full Stack Python/NGINX/Docker/PostgreSQL Development

## Overview
This file defines the architectural standards, coding conventions, and operational rules for Claude-assisted development in this full-stack project. Claude must follow these rules when writing code, suggesting refactors, and creating pull requests.

---

## 1. PROJECT STRUCTURE & CONVENTIONS

### Directory Layout
```
project-root/
├── backend/                      # Python Flask/FastAPI application
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py               # App entry point
│   │   ├── config.py             # Configuration (env-aware)
│   │   ├── models/               # SQLAlchemy ORM models
│   │   ├── routes/               # API blueprints/routers
│   │   ├── services/             # Business logic layer
│   │   ├── middleware/           # Custom middleware
│   │   ├── utils/                # Helpers (validators, serializers)
│   │   └── database.py           # DB session management
│   ├── migrations/               # Alembic migrations
│   ├── tests/                    # Test suite
│   │   ├── unit/
│   │   ├── integration/
│   │   └── conftest.py           # Pytest fixtures
│   ├── requirements.txt          # Python dependencies
│   ├── .env.example              # Example env vars
│   ├── Dockerfile               # Backend container
│   └── wsgi.py                  # WSGI entry point for Gunicorn
├── nginx/
│   ├── nginx.conf               # Main NGINX config
│   ├── conf.d/
│   │   ├── upstream.conf        # Upstream backend definition
│   │   ├── server.conf          # Server block
│   │   └── ssl.conf             # SSL/TLS config (if applicable)
│   └── Dockerfile               # NGINX container
├── docker-compose.yml           # Orchestration (dev/staging)
├── docker-compose.prod.yml      # Production override
├── .dockerignore
├── .env.example
├── .github/workflows/           # CI/CD
│   ├── test.yml
│   ├── deploy.yml
│   └── claude.yml               # Claude Code GitHub Actions
├── docs/
│   ├── API.md                   # API documentation
│   ├── DATABASE.md              # Schema documentation
│   └── DEPLOYMENT.md            # Deployment guide
├── CLAUDE.md                    # Project roadmap & context
├── CLAUDE_RULES.md             # This file
└── README.md
```

### Naming Conventions
- **Python files**: `snake_case.py`
- **Python classes**: `PascalCase`
- **Python functions/variables**: `snake_case`
- **Database tables**: `snake_case` (plural preferred: `users`, `products`)
- **Database columns**: `snake_case` (use `created_at`, `updated_at` for timestamps)
- **API endpoints**: `/api/v1/resource-name` (kebab-case, plural nouns)
- **Docker images**: `project-name:service-name` or `project-name-service-name:latest`
- **Environment variables**: `SCREAMING_SNAKE_CASE`

---

## 2. PYTHON BACKEND STANDARDS

### Framework & Dependencies
- **Framework**: FastAPI (preferred) or Flask
- **ORM**: SQLAlchemy 2.0+
- **Database Driver**: `psycopg[binary]` for PostgreSQL
- **Migration Tool**: Alembic
- **API Validation**: Pydantic v2
- **Testing**: pytest + pytest-asyncio (if async)
- **Linting**: ruff (strict mode)
- **Type Checking**: mypy
- **Formatting**: black (line length: 100)

### Required Dependencies Structure (requirements.txt)
```
# Core Framework
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
pydantic-settings==2.1.0

# Database
sqlalchemy==2.0.23
alembic==1.12.1
psycopg[binary]==3.9.10

# Utilities
python-dotenv==1.0.0
python-dateutil==2.8.2

# Production Server
gunicorn==21.2.0

# Testing (dev only)
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-cov==4.1.0
pytest-mock==3.12.0

# Dev Tools
ruff==0.1.8
black==23.12.0
mypy==1.7.1
```

### Code Quality Rules

#### Imports Organization
```python
# 1. Standard library
import os
import sys
from datetime import datetime
from typing import Optional, List

# 2. Third-party packages
from fastapi import FastAPI, Depends
from sqlalchemy import Column, String
from pydantic import BaseModel, EmailStr

# 3. Local imports
from app.config import settings
from app.models import User
```

#### Type Hints (Mandatory)
```python
# ✅ CORRECT
def create_user(email: str, age: int) -> User:
    """Create a new user."""
    return User(email=email, age=age)

# ❌ WRONG
def create_user(email, age):
    return User(email=email, age=age)

# For optional types
from typing import Optional
def get_user(user_id: Optional[int] = None) -> Optional[User]:
    pass
```

#### Pydantic Models (Request/Response)
```python
# app/schemas.py
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime

class UserBase(BaseModel):
    """Base user schema."""
    email: EmailStr
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)

class UserCreate(UserBase):
    """Schema for user creation."""
    password: str = Field(..., min_length=8)

class UserResponse(UserBase):
    """Schema for user response."""
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True  # For SQLAlchemy ORM
```

#### SQLAlchemy Models
```python
# app/models/user.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from app.database import Base

class User(Base):
    """User database model."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email})>"
```

#### Route Structure (FastAPI)
```python
# app/routes/users.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.schemas import UserCreate, UserResponse
from app.services.user_service import UserService
from app.database import get_db

router = APIRouter(prefix="/api/v1/users", tags=["users"])

@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    service: UserService = Depends(lambda db=Depends(get_db): UserService(db))
) -> UserResponse:
    """Create a new user."""
    existing_user = service.get_by_email(user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )
    user = service.create(user_data)
    return user

@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db)) -> UserResponse:
    """Retrieve a user by ID."""
    user = UserService(db).get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user
```

#### Error Handling
```python
# ✅ DO: Use appropriate HTTP status codes and custom exceptions
class UserNotFoundError(Exception):
    """Raised when a user is not found."""
    pass

@router.get("/{user_id}")
def get_user(user_id: int) -> UserResponse:
    try:
        user = UserService().get_by_id(user_id)
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail="User not found")
    return user

# ❌ DON'T: Swallow exceptions silently
def get_user(user_id: int) -> UserResponse:
    try:
        user = UserService().get_by_id(user_id)
    except:
        pass  # Silent failure
```

#### Testing Standards
```python
# tests/unit/test_user_service.py
import pytest
from app.services.user_service import UserService
from app.schemas import UserCreate

@pytest.fixture
def user_service(db_session):
    """Fixture for UserService."""
    return UserService(db_session)

def test_create_user(user_service):
    """Test user creation."""
    user_data = UserCreate(
        email="test@example.com",
        first_name="John",
        last_name="Doe",
        password="securepass123"
    )
    user = user_service.create(user_data)
    
    assert user.email == "test@example.com"
    assert user.id is not None

def test_get_nonexistent_user(user_service):
    """Test retrieving a nonexistent user."""
    with pytest.raises(UserNotFoundError):
        user_service.get_by_id(9999)
```

#### Configuration Management
```python
# app/config.py
from pydantic_settings import BaseSettings
from typing import Literal

class Settings(BaseSettings):
    """Application settings from environment variables."""
    
    # Environment
    ENV: Literal["development", "testing", "production"] = "development"
    DEBUG: bool = True
    
    # Database
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/dbname"
    
    # API
    API_TITLE: str = "My API"
    API_VERSION: str = "1.0.0"
    API_PREFIX: str = "/api/v1"
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24
    
    # CORS (if needed)
    ALLOWED_ORIGINS: list = ["http://localhost:3000"]
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
```

---

## 3. DATABASE (PostgreSQL) STANDARDS

### Alembic Migration Rules
```bash
# Generate a new migration
alembic revision --autogenerate -m "Add user table"

# Apply migrations (use in Docker entrypoint)
alembic upgrade head

# Rollback one migration
alembic downgrade -1
```

### Migration File Structure
```python
# migrations/versions/001_initial_schema.py
"""Initial schema creation."""
from alembic import op
import sqlalchemy as sa

revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    """Create initial tables."""
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email', name='uq_users_email')
    )
    op.create_index('ix_users_id', 'users', ['id'], unique=True)

def downgrade() -> None:
    """Drop tables."""
    op.drop_table('users')
```

### PostgreSQL Best Practices
- Always use `TIMESTAMPTZ` (not `TIMESTAMP`) for timezone-aware timestamps
- Add `created_at` and `updated_at` to every table
- Use proper constraints: `NOT NULL`, `UNIQUE`, `CHECK`, `FOREIGN KEY`
- Index foreign keys and frequently queried columns
- Use `SERIAL` or `BIGSERIAL` for auto-incrementing IDs (or prefer `UUID`)
- Document schema in `docs/DATABASE.md`

### Sample Schema
```sql
-- users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_is_active ON users(is_active);
```

---

## 4. DOCKER & DOCKER-COMPOSE STANDARDS

### Dockerfile Best Practices (Backend)
```dockerfile
# backend/Dockerfile
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install system dependencies (minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Run migrations and start server
CMD ["sh", "-c", "alembic upgrade head && gunicorn -w 4 -b 0.0.0.0:8000 --access-logfile - app.main:app"]
```

### NGINX Dockerfile
```dockerfile
# nginx/Dockerfile
FROM nginx:1.25-alpine

# Copy NGINX config files
COPY nginx.conf /etc/nginx/nginx.conf
COPY conf.d/ /etc/nginx/conf.d/

# Expose port
EXPOSE 80 443

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost/health || exit 1

# Start NGINX
CMD ["nginx", "-g", "daemon off;"]
```

### docker-compose.yml (Development)
```yaml
version: "3.9"

services:
  postgres:
    image: postgres:15-alpine
    container_name: myapp-postgres
    environment:
      POSTGRES_USER: ${DB_USER:-postgres}
      POSTGRES_PASSWORD: ${DB_PASSWORD:-postgres}
      POSTGRES_DB: ${DB_NAME:-myapp}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER:-postgres}"]
      interval: 10s
      timeout: 5s
      retries: 5

  backend:
    build:
      context: .
      dockerfile: backend/Dockerfile
    container_name: myapp-backend
    environment:
      DATABASE_URL: postgresql://${DB_USER:-postgres}:${DB_PASSWORD:-postgres}@postgres:5432/${DB_NAME:-myapp}
      ENV: development
      DEBUG: "true"
    volumes:
      - ./backend:/app
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
    command: >
      sh -c "alembic upgrade head && 
             uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

  nginx:
    build:
      context: .
      dockerfile: nginx/Dockerfile
    container_name: myapp-nginx
    ports:
      - "80:80"
    depends_on:
      - backend
    volumes:
      - ./nginx/conf.d:/etc/nginx/conf.d
    restart: unless-stopped

volumes:
  postgres_data:
```

### NGINX Configuration Rules
```nginx
# nginx/nginx.conf
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';

    access_log /var/log/nginx/access.log main;

    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;
    client_max_body_size 10M;

    gzip on;
    gzip_vary on;
    gzip_types text/plain text/css text/xml text/javascript application/x-javascript application/xml+rss;

    include /etc/nginx/conf.d/*.conf;
}
```

```nginx
# nginx/conf.d/upstream.conf
upstream backend {
    server backend:8000;
    keepalive 32;
}
```

```nginx
# nginx/conf.d/server.conf
server {
    listen 80;
    server_name _;

    location /health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }

    location /api/ {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_buffering off;
        proxy_request_buffering off;
    }

    location / {
        # Serve frontend assets here if needed
        return 404;
    }
}
```

---

## 5. GIT & COMMIT STANDARDS

### Commit Message Format
```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types**: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `chore`

**Examples**:
```
feat(auth): add JWT token refresh endpoint
fix(user-service): handle null email gracefully
docs(api): update endpoint documentation
test(database): add migration rollback tests
chore(deps): upgrade SQLAlchemy to 2.0.23
```

### Pull Request Standards
- Link to relevant issues/tickets
- Describe what changed and why
- Include migration instructions if DB schema changed
- Ensure all tests pass before merging
- Require at least one review for production branches

---

## 6. TESTING STANDARDS

### Test Coverage Requirements
- **Minimum**: 80% code coverage for backend
- **Target**: 90%+ for critical business logic

### Test Organization
```python
# tests/conftest.py - Shared fixtures
import pytest
from app.database import Base, engine, SessionLocal
from app.main import app
from fastapi.testclient import TestClient

@pytest.fixture(scope="session")
def db():
    """Create test database."""
    Base.metadata.create_all(bind=engine)
    yield SessionLocal()
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)

@pytest.fixture
def auth_headers(client):
    """Generate authentication headers for tests."""
    response = client.post("/api/v1/auth/login", json={
        "email": "test@example.com",
        "password": "testpass123"
    })
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
```

### Unit vs Integration Tests
```python
# tests/unit/test_user_service.py - Unit (fast, mocked)
@pytest.fixture
def mock_db(mocker):
    return mocker.Mock()

def test_user_creation_validates_email(mock_db):
    service = UserService(mock_db)
    with pytest.raises(ValueError):
        service.create({"email": "invalid", "password": "x"})

# tests/integration/test_user_api.py - Integration (real DB)
def test_create_user_endpoint(client, db):
    response = client.post("/api/v1/users", json={
        "email": "new@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "password": "securepass123"
    })
    assert response.status_code == 201
    assert response.json()["email"] == "new@example.com"
```

### Running Tests
```bash
# All tests
pytest

# With coverage
pytest --cov=app --cov-report=html

# Specific test file
pytest tests/unit/test_user_service.py

# By marker
pytest -m "integration"
```

---

## 7. ENVIRONMENT VARIABLES

### .env File Structure
```env
# Environment
ENV=development
DEBUG=true

# Database
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=postgres
DB_PORT=5432
DB_NAME=myapp
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/myapp

# API
API_PORT=8000
API_HOST=0.0.0.0

# Security
SECRET_KEY=your-super-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# CORS (comma-separated)
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173

# Logging
LOG_LEVEL=INFO

# Email (if applicable)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

### Never Commit
- `.env` (commit `.env.example` instead)
- `*.key`, `*.pem` files
- `credentials.json`
- Local development secrets

---

## 8. LOGGING & MONITORING

### Logging Standards
```python
# app/utils/logger.py
import logging
from app.config import settings

def get_logger(name: str) -> logging.Logger:
    """Configure and return a logger."""
    logger = logging.getLogger(name)
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(settings.LOG_LEVEL)
    return logger

# Usage
logger = get_logger(__name__)
logger.info("User created", extra={"user_id": user.id})
logger.error("Database connection failed", exc_info=True)
```

### Structured Logging
```python
import json

def log_request(method: str, path: str, status_code: int, duration_ms: float):
    """Log request with structured format."""
    log_data = {
        "method": method,
        "path": path,
        "status": status_code,
        "duration_ms": duration_ms,
        "timestamp": datetime.utcnow().isoformat()
    }
    logger.info(json.dumps(log_data))
```

---

## 9. SECURITY STANDARDS

### Password Management
- **Never** store plain-text passwords
- Use `bcrypt` or `argon2` for hashing
- Use `secrets` module for token generation

```python
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)
```

### API Security
- Use HTTPS in production
- Implement rate limiting
- Validate all inputs with Pydantic
- Use CORS appropriately
- Add CSRF protection if needed
- Never expose sensitive data in error messages

```python
from fastapi.security import HTTPBearer, HTTPAuthCredentials

security = HTTPBearer()

@router.get("/protected")
def protected_route(credentials: HTTPAuthCredentials = Depends(security)):
    token = credentials.credentials
    # Verify token...
```

### Database Security
- Use parameterized queries (SQLAlchemy does this by default)
- Principle of least privilege for DB users
- Use SSL for database connections in production
- Regular backups and testing restore procedures

---

## 10. DEPLOYMENT & CI/CD

### GitHub Actions Workflow
```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: test_db
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.11"
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      
      - name: Lint with ruff
        run: ruff check backend/
      
      - name: Format check with black
        run: black --check backend/
      
      - name: Type check with mypy
        run: mypy backend/
      
      - name: Run tests
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test_db
        run: pytest --cov=app --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

### Production Deployment Checklist
- [ ] All tests passing
- [ ] Code reviewed and approved
- [ ] Migrations tested against production schema
- [ ] Environment variables configured
- [ ] Backups configured
- [ ] Monitoring/alerting configured
- [ ] Database credentials rotated
- [ ] HTTPS/SSL certificates valid
- [ ] Load testing completed
- [ ] Rollback plan documented

---

## 11. CLAUDE CODE RULES & PREFERENCES

### When Claude Creates or Modifies Code
1. **Always** add type hints to function signatures
2. **Always** include docstrings for classes and functions
3. **Always** use dependency injection (don't hardcode imports)
4. **Always** follow the project structure above (don't create random directories)
5. **Always** run tests after making changes: `pytest --cov=app`
6. **Always** create tests for new features before implementation (TDD style)
7. **Always** check for linting issues: `ruff check .` and `black --check .`
8. **Never** hardcode credentials or secrets
9. **Never** modify migrations after they've been committed (create new ones)
10. **Never** skip error handling or logging

### Code Review Checklist for Claude-Generated Code
- [ ] All functions have type hints
- [ ] All classes/functions have docstrings
- [ ] Error handling is explicit (no silent failures)
- [ ] Database queries use ORM (no raw SQL except migrations)
- [ ] No N+1 query issues
- [ ] Tests cover happy path + error cases
- [ ] Code follows naming conventions above
- [ ] No security vulnerabilities
- [ ] Uses dependency injection for testability
- [ ] Logging is appropriate and structured

### Pre-Commit Checklist
```bash
# Before committing, Claude should run:
black backend/
ruff check backend/ --fix
mypy backend/
pytest --cov=app --cov-report=term-missing

# Verify no uncommitted secrets
git diff --cached | grep -i "password\|secret\|key" || echo "✓ No secrets in diff"
```

---

## 12. ANTI-PATTERNS (What NOT to Do)

| ❌ Anti-Pattern | ✅ Correct Approach |
|---|---|
| `from app import *` | `from app.models import User` |
| Global variables | Use dependency injection / context |
| Bare `except:` | `except SpecificException as e:` |
| Logic in routes | Move to services layer |
| Mutable default arguments | `def func(items: list \| None = None):` |
| No database indexes | Index frequently queried columns |
| Silent test failures | Always assert with clear messages |
| Hardcoded credentials | Use environment variables |
| No logging | Comprehensive structured logging |
| Skipping migrations | Every schema change needs migration |

---

## 13. QUICK COMMANDS REFERENCE

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
python -m pytest
python -m black . --check
python -m ruff check .
python -m mypy app/

# Docker
docker-compose up -d
docker-compose logs -f backend
docker-compose down

# Database
alembic revision --autogenerate -m "your message"
alembic upgrade head
alembic downgrade -1

# Git (commit format)
git commit -m "feat(users): add email verification endpoint"
git commit -m "fix(auth): resolve JWT expiration handling"
```

---

## 14. DOCUMENTATION STANDARDS

### Docstring Format (Google Style)
```python
def create_user(email: str, password: str) -> User:
    """Create a new user account.
    
    Validates email format and password strength before creation.
    Sends welcome email to the user.
    
    Args:
        email: User's email address (must be unique).
        password: User's password (minimum 8 characters).
    
    Returns:
        User: The newly created user object.
    
    Raises:
        ValueError: If email format is invalid or already exists.
        ValueError: If password doesn't meet strength requirements.
    
    Example:
        >>> user = create_user("john@example.com", "securepass123")
        >>> user.email
        'john@example.com'
    """
```

### API Documentation
```python
@router.post(
    "/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user",
    description="Creates a new user account with the provided credentials."
)
def create_user(user_data: UserCreate) -> UserResponse:
    """Create a new user."""
    pass
```

---

## 15. SUCCESS CRITERIA FOR CLAUDE SUBMISSIONS

Every code submission from Claude should meet:

✅ **Functionality**
- Solves the stated problem
- No broken tests
- No TypeErrors or AttributeErrors at runtime

✅ **Code Quality**
- Passes `ruff check`, `black --check`, `mypy`
- 80%+ test coverage
- Clear variable/function names
- No code duplication

✅ **Maintainability**
- Docstrings present
- Type hints on all functions
- Proper error handling with logging
- Follows project structure

✅ **Security**
- No hardcoded secrets
- Input validation with Pydantic
- Proper error messages (no internal details leaked)

✅ **Documentation**
- Docstrings for public functions
- Updated relevant .md files
- Migration files (if DB changes)

---

## 16. WHEN TO ESCALATE

Claude should ask for human clarification when:
- Requirements are ambiguous or conflicting
- Security implications are unclear
- Major architectural decisions needed
- Data migration strategy required
- Production deployment decision

---

**Version**: 1.0  
**Last Updated**: January 2025  
**Maintainer**: Your Team  

When working with Claude, reference this file: *"Follow CLAUDE_RULES.md line X"* for specific standards.
