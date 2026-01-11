# Codi Backend

Agentic AI Development Platform Backend - A production-grade **multi-agent orchestration system** for building Flutter, React, and Next.js applications.

## 🚀 Features

### Multi-Agent Orchestration System

Codi uses a sophisticated multi-agent architecture with intelligent delegation and parallel execution.

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

#### Orchestration Agents
| Agent | Role |
|-------|------|
| **Conductor** | Master orchestrator - plans, delegates, coordinates all agents |
| **Strategist** | Task planner - breaks complex goals into executable steps |
| **Analyst** | Pre-planning - identifies hidden requirements & failure points |

#### Specialized Agents
| Agent | Role |
|-------|------|
| **Sage** | Strategic advisor - architecture, debugging, high-IQ reasoning |
| **Scholar** | Research specialist - docs lookup, library examples |
| **Scout** | Fast reconnaissance - codebase search, pattern matching |
| **Artisan** | UI/UX specialist - beautiful interfaces, animations |
| **Scribe** | Documentation expert - README, API docs, guides |
| **Vision** | Multimodal analysis - screenshots, PDFs, diagrams |

#### Platform Agents
| Agent | Role |
|-------|------|
| **FlutterEngineer** | Dart/Flutter code generation with anti-hallucination |
| **ReactEngineer** | React web application development |
| **NextjsEngineer** | Next.js full-stack development |
| **CodeReviewer** | Pre-commit quality validation |
| **GitOperator** | Version control operations |
| **BuildDeploy** | CI/CD orchestration |

### Key Capabilities
- **Intelligent Delegation**: Conductor routes tasks to specialized agents
- **Background Execution**: Parallel task processing with concurrency control
- **Session Continuity**: Context preserved across agent interactions
- **Real-time Updates**: WebSocket streaming for all agent activities
- **Multi-Model Support**: Gemini 3 Pro (reasoning) + Flash (speed)

## 🛠 Tech Stack

- **Framework**: FastAPI with async/await
- **Agent Orchestration**: LangGraph + LangChain
- **LLM**: Google Gemini 3 Pro & Flash
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Caching**: Redis for sessions and pub/sub
- **Task Queue**: Celery with Redis broker
- **Authentication**: GitHub OAuth 2.0

## 📦 Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 14+
- Redis 7+
- Docker & Docker Compose (optional)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/codi-app/codi-backend.git
cd codi-backend
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment:
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. Run database migrations:
```bash
alembic upgrade head
```

6. Start the server:
```bash
uvicorn app.main:app --reload
```

### Using Docker

```bash
docker-compose up -d
```

## 🔧 Configuration

### Model Configuration

Codi supports flexible model configuration:

```bash
# Use Gemini 3 for all agents (recommended)
FORCE_GEMINI_OVERALL=true

# Or use multi-model setup (requires additional API keys)
FORCE_GEMINI_OVERALL=false
OPENAI_API_KEY=your_key
ANTHROPIC_API_KEY=your_key
```

When `FORCE_GEMINI_OVERALL=true`:
- **Conductor, Sage** → `gemini-3-pro-preview` (advanced reasoning)
- **All others** → `gemini-3-flash-preview` (fast execution)

> ⚠️ **Gemini 3 Note**: Always use `temperature=1.0` (default). Lower values cause looping/degraded performance.

See `.env.example` for all configuration options.

## 📚 API Documentation

Once running, visit:
- OpenAPI docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 🧪 Development

### Running Tests

```bash
pytest tests/ -v
```

### Code Formatting

```bash
ruff format app/
ruff check app/ --fix
```

### Agent Architecture

See `app/agents/AGENT_README.md` for detailed agent documentation.

## 📄 License

MIT License - see LICENSE file for details.
