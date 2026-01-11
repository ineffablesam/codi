# Codi Platform - Complete Setup & Documentation

## Quick Commands

```bash
# Backend
python -m venv venv
source venv/bin/activate 
celery -A app.tasks.celery_app worker --loglevel=debug
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
ngrok http 8000
```

---

## Overview

**Codi** is an AI-powered development platform with:
- **Python FastAPI Backend** - Multi-agent orchestration system with 15 specialized agents
- **Flutter Mobile App** - iOS/Android app with real-time agent chat and embedded preview

---

## 🤖 Multi-Agent Orchestration System

Codi uses a sophisticated multi-agent architecture powered by **Google Gemini 3**.

```
                    ┌─────────────┐
                    │  CONDUCTOR  │ ← Master orchestrator (Gemini 3 Pro)
                    └──────┬──────┘
                           │
       ┌───────────────────┼───────────────────┐
       │                   │                   │
       ▼                   ▼                   ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  Pre-Planning │    │  Specialized  │    │   Platform   │
└──────────────┘    └──────────────┘    └──────────────┘
    Analyst             Sage              FlutterEngineer
    Strategist          Scholar           ReactEngineer
                        Scout             NextjsEngineer
                        Artisan           CodeReviewer
                        Scribe            GitOperator
                        Vision            BuildDeploy
```

### Agent Categories

| Category | Agents | Purpose |
|----------|--------|---------|
| **Orchestration** | Conductor, Strategist, Analyst | Task planning & delegation |
| **Specialized** | Sage, Scholar, Scout, Artisan, Scribe, Vision | Domain expertise |
| **Platform** | FlutterEngineer, ReactEngineer, NextjsEngineer | Code generation |
| **Operations** | CodeReviewer, GitOperator, BuildDeploy, Memory | DevOps & quality |

### Key Features
- **Intelligent Delegation**: Conductor routes tasks to best-fit agents
- **Background Execution**: Parallel processing with concurrency control
- **Session Continuity**: Context preserved across interactions
- **Real-time Streaming**: WebSocket updates for all activities

---

## Project Structure

```
codi/
├── codi-backend/              # Python FastAPI backend
│   ├── app/
│   │   ├── agents/            # Multi-agent orchestration
│   │   │   ├── platform/      # Platform-specific agents
│   │   │   ├── tools/         # Delegation tools
│   │   │   ├── conductor.py   # Master orchestrator
│   │   │   ├── sage.py        # Strategic advisor
│   │   │   ├── scout.py       # Fast search
│   │   │   └── ...            # Other agents
│   │   ├── api/               # REST API routes
│   │   ├── models/            # SQLAlchemy models
│   │   ├── schemas/           # Pydantic schemas
│   │   ├── services/          # GitHub, encryption
│   │   ├── workflows/         # LangGraph state machine
│   │   ├── websocket/         # Real-time WebSocket
│   │   └── tasks/             # Celery async tasks
│   └── docker-compose.yml
│
└── codi_frontend/             # Flutter mobile app
    └── lib/
        ├── core/              # API, storage, utils
        └── features/
            ├── auth/          # GitHub OAuth
            ├── projects/      # Project CRUD
            └── editor/        # Preview + Agent Chat
```

---

## Quick Start

### Prerequisites
- Python 3.11+
- Flutter 3.5+
- PostgreSQL 14+
- Redis 7+

### 1. Backend Setup

```bash
cd codi-backend
python -m venv venv
source venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
# Edit .env with your GEMINI_API_KEY and other values

alembic upgrade head

# Terminal 1: Celery worker
celery -A app.tasks.celery_app.celery_app worker --loglevel=info

# Terminal 2: API server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Frontend Setup

```bash
cd codi_frontend
flutter pub get
cp .env.example .env
flutter run
```

---

## AI Model Configuration

Codi supports **Gemini 3** with flexible configuration:

```bash
# .env
GEMINI_API_KEY=your_gemini_api_key
FORCE_GEMINI_OVERALL=true  # Use Gemini 3 for all agents
```

### Model Assignment
| Agent | Model | Purpose |
|-------|-------|---------|
| Conductor, Sage | `gemini-3-pro-preview` | Advanced reasoning |
| All others | `gemini-3-flash-preview` | Fast execution |

> ⚠️ **Important**: Gemini 3 requires `temperature=1.0` (default). Lower values cause looping.

---

## WebSocket Protocol

Connect: `wss://your-api/agents/{project_id}/ws?token={jwt}`

### Message Types

| Type | Direction | Description |
|------|-----------|-------------|
| `agent_status` | → Client | Agent started/completed |
| `file_operation` | → Client | File created/updated |
| `llm_stream` | → Client | Streaming LLM response |
| `background_task_started` | → Client | Parallel task launched |
| `background_task_progress` | → Client | Task progress update |
| `background_task_completed` | → Client | Task finished |
| `delegation_status` | → Client | Agent→Agent delegation |
| `user_message` | → Server | User chat message |

---

## API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/auth/github` | Get GitHub OAuth URL |
| GET | `/auth/github/callback` | OAuth callback |
| GET | `/auth/me` | Get current user |

### Projects
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/projects` | List projects |
| POST | `/projects` | Create project |
| GET | `/projects/{id}/files` | List files |

### Agents
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/agents/{project_id}/task` | Submit task |
| WS | `/agents/{project_id}/ws` | Real-time updates |

---

## Environment Variables

### Backend (.env)
```env
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/codi

# Redis
REDIS_URL=redis://localhost:6379/0

# GitHub OAuth
GITHUB_CLIENT_ID=your_client_id
GITHUB_CLIENT_SECRET=your_secret

# AI (Gemini 3)
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-3-flash-preview
FORCE_GEMINI_OVERALL=true

# Security
SECRET_KEY=your-256-bit-secret
ENCRYPTION_KEY=your-fernet-key
```

### Frontend (.env)
```env
API_BASE_URL=http://localhost:8000
WS_BASE_URL=ws://localhost:8000
GITHUB_CLIENT_ID=your_client_id
```

---

## Docker Deployment

```bash
cd codi-backend
docker-compose up -d --build
```

Services: `api`, `celery`, `postgres`, `redis`

---

## Architecture

```
┌─────────────────────┐      ┌──────────────────────────────────┐
│   Flutter Mobile    │◄────►│         FastAPI Backend          │
│   (iOS/Android)     │ WS   │                                  │
│                     │      │  ┌─────────────────────────────┐ │
│ ┌─────────────────┐ │      │  │   Multi-Agent Orchestrator  │ │
│ │  Agent Chat     │ │      │  │                             │ │
│ │  (WebSocket)    │ │      │  │  Conductor → Specialized    │ │
│ └─────────────────┘ │      │  │      ↓          Agents      │ │
│                     │      │  │  Strategist    (Sage,       │ │
│ ┌─────────────────┐ │      │  │  Analyst       Scout, etc.) │ │
│ │ WebView Preview │ │      │  │      ↓                      │ │
│ │ (Deployed URL)  │ │      │  │  Platform Engineers         │ │
│ └─────────────────┘ │      │  │  (Flutter, React, Next.js)  │ │
└─────────────────────┘      │  └─────────────────────────────┘ │
                             │                                  │
                             │  ┌──────┐ ┌───────┐ ┌────────┐  │
                             │  │Celery│ │Postgres│ │ Redis  │  │
                             │  └──────┘ └───────┘ └────────┘  │
                             └──────────────────────────────────┘
                                           │
                                           ▼
                             ┌──────────────────────────────────┐
                             │           GitHub API             │
                             │  (OAuth, Repos, Actions, Pages)  │
                             └──────────────────────────────────┘
```

---

## Documentation

- **Backend API**: http://localhost:8000/docs
- **Agent Architecture**: `codi-backend/app/agents/AGENT_README.md`

---

## Support

Check logs at:
- Backend: `uvicorn` terminal
- Celery: `celery` worker terminal  
- Frontend: `flutter run` console
