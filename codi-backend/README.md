# Codi Backend

Agentic AI Development Platform Backend - A production-grade multi-agent system for building Flutter applications.

## Features

- **Multi-Agent System**: 7 specialized agents orchestrated with LangGraph
  - Planner Agent: Strategic decomposition and coordination
  - Flutter Engineer Agent: Dart/Flutter code generation
  - Code Reviewer Agent: Quality assurance and validation
  - Git Operator Agent: Version control operations
  - Build & Deploy Agent: CI/CD orchestration
  - Memory Agent: Persistent state and audit trail
  - Backend Engineer Agent: Optional backend service generation

- **Real-time Updates**: WebSocket-based status updates for every agent action
- **GitHub Integration**: OAuth authentication, repository management, GitHub Actions
- **AI-Powered**: Google Gemini 2.0 Flash for intelligent code generation

## Tech Stack

- **Framework**: FastAPI with async/await
- **Agent Orchestration**: LangGraph + LangChain
- **LLM**: Google Gemini 2.0 Flash
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Caching**: Redis for sessions and rate limiting
- **Task Queue**: Celery with Redis broker
- **Authentication**: GitHub OAuth 2.0

## Quick Start

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

## API Documentation

Once running, visit:
- OpenAPI docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Environment Variables

See `.env.example` for all available configuration options.

## Development

### Running Tests

```bash
pytest tests/ -v
```

### Code Formatting

```bash
ruff format app/
ruff check app/ --fix
```

## License

MIT License - see LICENSE file for details.
