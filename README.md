# Codi Platform - Complete Setup & Documentation

Commands
Celery : celery -A app.tasks.celery_app worker --loglevel=debug
Uvicorn: uvicorn app.main:app --reload --host 0.0.0.0 --port 8000;
Ngrok: ngrok http 8000

## Overview

**Codi** is an AI-powered Flutter development platform with:
- **Python FastAPI Backend** - 6 LangGraph agents for code generation, review, git ops, and deployment
- **Flutter Mobile App** - iOS/Android app with real-time agent chat and embedded preview

---

## Project Structure

```
codi-v2/
├── codi-backend/          # Python FastAPI backend
│   ├── app/
│   │   ├── agents/        # 6 LangGraph agents
│   │   ├── api/           # REST API routes
│   │   ├── models/        # SQLAlchemy models
│   │   ├── schemas/       # Pydantic schemas
│   │   ├── services/      # GitHub, encryption services
│   │   ├── workflows/     # LangGraph state machine
│   │   ├── websocket/     # Real-time WebSocket
│   │   ├── tasks/         # Celery async tasks
│   │   └── utils/         # Logging, security
│   ├── alembic/           # Database migrations
│   ├── tests/
│   └── docker-compose.yml
│
└── codi_frontend/         # Flutter mobile app
    └── lib/
        ├── config/        # Theme, routes, env
        ├── core/          # API, storage, utils
        ├── features/
        │   ├── auth/      # GitHub OAuth
        │   ├── projects/  # Project CRUD
        │   ├── editor/    # Preview + Chat
        │   ├── deployments/
        │   └── settings/
        └── shared/        # Reusable widgets
```

---

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+ (for npm)
- Flutter 3.5+
- PostgreSQL 14+
- Redis 7+
- Git

### 1. Backend Setup

```bash
cd codi-backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env

# Edit .env with your values:
# - DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/codi
# - REDIS_URL=redis://localhost:6379/0
# - GITHUB_CLIENT_ID=your_github_oauth_app_id
# - GITHUB_CLIENT_SECRET=your_github_oauth_app_secret
# - GOOGLE_API_KEY=your_gemini_api_key
# - SECRET_KEY=your_jwt_secret_key

# Run database migrations
alembic upgrade head

# Start Celery worker (new terminal)
celery -A app.tasks.celery_app.celery_app worker --loglevel=info

# Start backend server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Frontend Setup

```bash
cd codi_frontend

# Get dependencies
flutter pub get

# Copy environment file
cp .env.example .env

# Edit .env with your values:
# - API_BASE_URL=http://localhost:8000
# - WS_BASE_URL=ws://localhost:8000
# - GITHUB_CLIENT_ID=your_github_oauth_app_id

# Run on simulator/device
flutter run
```

---

## API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/auth/github` | Get GitHub OAuth URL |
| GET | `/auth/github/callback` | OAuth callback, returns JWT |
| GET | `/auth/me` | Get current user |
| POST | `/auth/logout` | Logout (client discards token) |

### Projects
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/projects` | List user projects |
| POST | `/projects` | Create project + GitHub repo |
| GET | `/projects/{id}` | Get project details |
| PATCH | `/projects/{id}` | Update project |
| DELETE | `/projects/{id}` | Delete project (soft) |
| GET | `/projects/{id}/files` | List repository files |
| GET | `/projects/{id}/files/{path}` | Get file content |

### Agents
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/agents/{project_id}/task` | Submit agent task |
| GET | `/agents/{project_id}/task/{id}` | Get task status |
| GET | `/agents/{project_id}/history` | Get operation history |
| WS | `/agents/{project_id}/ws` | WebSocket for real-time updates |

---

## WebSocket Protocol

Connect to: `wss://your-api/agents/{project_id}/ws?token={jwt}`

### Message Types (Backend → Frontend)

| Type | Description |
|------|-------------|
| `agent_status` | Agent started/completed/failed |
| `file_operation` | File created/updated/deleted |
| `tool_execution` | Agent using a tool |
| `git_operation` | Branch/commit/push |
| `build_progress` | Build percentage |
| `build_status` | Build triggered/complete |
| `deployment_complete` | Deployment success with URL |
| `review_progress` | Code review status |
| `review_issue` | Review found issue |
| `agent_error` | Agent error occurred |
| `user_input_required` | Agent needs user input |

### Message Types (Frontend → Backend)

| Type | Description |
|------|-------------|
| `user_message` | User chat message |
| `user_input_response` | Reply to input request |
| `ping` | Keep-alive ping |

---

## Agents

| Agent | Responsibility |
|-------|----------------|
| **Planner** | Breaks user request into steps |
| **Flutter Engineer** | Writes Dart/Flutter code |
| **Code Reviewer** | Reviews code quality |
| **Git Operator** | Git branch/commit/push |
| **Build & Deploy** | Triggers CI/CD, deploys |
| **Memory** | Logs operation history |

---

## Environment Variables

### Backend (.env)
```env
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/codi

# Redis
REDIS_URL=redis://localhost:6379/0

# GitHub OAuth App
GITHUB_CLIENT_ID=your_github_oauth_client_id
GITHUB_CLIENT_SECRET=your_github_oauth_client_secret

# LLM (Google Gemini)
GOOGLE_API_KEY=your_gemini_api_key
LLM_MODEL=gemini-2.0-flash

# Security
SECRET_KEY=your-256-bit-secret-key
ENCRYPTION_KEY=your-32-byte-fernet-key

# App
APP_ENV=development
DEBUG=true
```

### Frontend (.env)
```env
API_BASE_URL=http://localhost:8000
WS_BASE_URL=ws://localhost:8000
GITHUB_CLIENT_ID=your_github_oauth_client_id
```

---

## Docker Deployment

```bash
cd codi-backend

# Build and start all services
docker-compose up -d --build

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

Services started:
- `api` - FastAPI backend on port 8000
- `celery` - Celery worker
- `postgres` - PostgreSQL database
- `redis` - Redis cache

---

## Testing

### Backend Tests
```bash
cd codi-backend
pytest tests/ -v
```

### Frontend Tests
```bash
cd codi_frontend
flutter test
```

### Verify Build
```bash
# Backend
cd codi-backend && python -c "from app.main import app; print('Backend OK')"

# Frontend
cd codi_frontend && flutter analyze
```

---

## Architecture

```
┌─────────────────────┐      ┌──────────────────────────────────┐
│   Flutter Mobile    │◄────►│         FastAPI Backend          │
│   (iOS/Android)     │ HTTP │                                  │
│                     │ WS   │  ┌─────────────────────────────┐ │
│ ┌─────────────────┐ │      │  │     LangGraph Workflow      │ │
│ │  Agent Chat     │ │      │  │  ┌────────┐ ┌────────────┐  │ │
│ │  (WebSocket)    │ │      │  │  │Planner │→│Flutter Eng │  │ │
│ └─────────────────┘ │      │  │  └────────┘ └────────────┘  │ │
│                     │      │  │       ↓           ↓         │ │
│ ┌─────────────────┐ │      │  │  ┌────────┐ ┌────────────┐  │ │
│ │ WebView Preview │ │      │  │  │Reviewer│→│Git Operator│  │ │
│ │ (Deployed URL)  │ │      │  │  └────────┘ └────────────┘  │ │
│ └─────────────────┘ │      │  │       ↓           ↓         │ │
└─────────────────────┘      │  │  ┌────────────────────────┐ │ │
                             │  │  │   Build & Deploy       │ │ │
                             │  │  └────────────────────────┘ │ │
                             │  └─────────────────────────────┘ │
                             │                                  │
                             │  ┌──────┐  ┌───────┐  ┌───────┐ │
                             │  │Celery│  │Postgres│  │ Redis │ │
                             │  └──────┘  └───────┘  └───────┘ │
                             └──────────────────────────────────┘
                                           │
                                           ▼
                             ┌──────────────────────────────────┐
                             │           GitHub API             │
                             │  (OAuth, Repos, Files, Actions)  │
                             └──────────────────────────────────┘
```

---

## File Count Summary

| Component | Files |
|-----------|-------|
| Backend Python | 40+ |
| Frontend Dart | 53 |
| **Total** | **93+** |

---

## Support

For issues: Check logs at:
- Backend: `uvicorn` terminal output
- Celery: `celery` worker terminal
- Frontend: `flutter run` console

