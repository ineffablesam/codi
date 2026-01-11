# Codi v2 - Git-Driven Containerized Runtime

## Overview

Codi v2 uses **local Git repositories** and **Docker containers** for on-premise deployments with automatic subdomain routing via **Traefik**.

```
┌─────────────────────────────────────────────────────────────┐
│                     Codi Architecture                        │
├─────────────────────────────────────────────────────────────┤
│  User Request → Backend API → Build Image → Create Container │
│                                     ↓                        │
│               Traefik ← Labels ← Container (project.codi.local)│
└─────────────────────────────────────────────────────────────┘
```

---

## Quick Start

### 1. Prerequisites

```bash
# Install Docker
brew install docker docker-compose

# Add local DNS (resolves *.codi.local)
echo "127.0.0.1 codi.local" | sudo tee -a /etc/hosts
echo "127.0.0.1 api.codi.local" | sudo tee -a /etc/hosts
```

For wildcard subdomain resolution, install dnsmasq:

```bash
brew install dnsmasq
echo "address=/.codi.local/127.0.0.1" >> /opt/homebrew/etc/dnsmasq.conf
sudo brew services start dnsmasq
```

### 2. Start Services

```bash
cd codi-backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install docker GitPython pyyaml

# Run migrations
alembic upgrade head

# Start with Docker Compose (includes Traefik)
docker compose up -d

# OR start manually for development:
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
celery -A app.tasks.celery_app worker --loglevel=info
```

---

## Architecture

### Components

| Component | Purpose | Port |
|-----------|---------|------|
| **Traefik** | Reverse proxy, subdomain routing | 80, 8080 (dashboard) |
| **FastAPI** | Backend API | 8000 |
| **Celery** | Background tasks | - |
| **PostgreSQL** | Database | 5432 |
| **Redis** | Cache, message broker | 6379 |

### Key Services

| Service | File | Description |
|---------|------|-------------|
| `LocalGitService` | `git_service.py` | Git operations via GitPython |
| `DockerService` | `docker_service.py` | Container lifecycle management |
| `TraefikService` | `traefik_service.py` | Subdomain routing labels |
| `FrameworkDetector` | `framework_detector.py` | Auto-detect Flutter/Next.js/React |

---

## API Endpoints

### Containers

```
POST   /api/v1/containers          - Create container
GET    /api/v1/containers/{id}     - Get container
POST   /api/v1/containers/{id}/start|stop|restart
DELETE /api/v1/containers/{id}     - Remove
GET    /api/v1/containers/{id}/logs?tail=100
GET    /api/v1/containers/{id}/stats
WS     /api/v1/containers/{id}/logs/stream
```

### Deployments

```
POST   /api/v1/deployments         - Create deployment
GET    /api/v1/deployments/{id}    - Get deployment
GET    /api/v1/deployments/project/{id} - List project deployments
POST   /api/v1/deployments/{id}/redeploy
DELETE /api/v1/deployments/{id}
```

---

## URL Scheme

| Type | URL Pattern | Example |
|------|-------------|---------|
| Production | `{project-slug}.codi.local` | `my-app.codi.local` |
| Preview | `{project-slug}-preview-{branch}.codi.local` | `my-app-preview-feature-x.codi.local` |
| API | `api.codi.local` | `api.codi.local/docs` |

---

## Development Workflow

### Creating a Deployment

```bash
# Via API
curl -X POST http://localhost:8000/api/v1/deployments \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"project_id": 1, "branch": "main"}'
```

### Viewing Logs

```bash
# Get recent logs
curl http://localhost:8000/api/v1/containers/{id}/logs?tail=50

# Stream logs (WebSocket)
wscat -c ws://localhost:8000/api/v1/containers/{id}/logs/stream
```

### Container Stats

```bash
curl http://localhost:8000/api/v1/containers/{id}/stats
# Returns: cpu_percent, memory_usage_mb, network bytes
```

---

## Directory Structure

```
/var/codi/repos/           # Git repositories
  └── {user_id}/
      └── {project-slug}/  # Project files

codi-backend/
  ├── app/
  │   ├── services/
  │   │   ├── docker_service.py    # Container lifecycle
  │   │   ├── traefik_service.py   # Routing labels
  │   │   ├── git_service.py       # Local Git ops
  │   │   └── framework_detector.py
  │   ├── models/
  │   │   ├── container.py         # Container model
  │   │   └── deployment.py        # Deployment model
  │   ├── api/
  │   │   ├── containers.py        # Container endpoints
  │   │   └── deployments.py       # Deployment endpoints
  │   └── agents/
  │       └── container_manager.py # ContainerManagerAgent
  └── docker-compose.yml           # Infrastructure
```

---

## Troubleshooting

### DNS Not Resolving

```bash
# Check dnsmasq
scutil --dns | grep codi

# Verify /etc/hosts
cat /etc/hosts | grep codi
```

### Docker Container Issues

```bash
# Check Traefik dashboard
open http://localhost:8080

# List Codi containers
docker ps --filter "label=codi.project.slug"

# View container logs
docker logs codi-my-app -f
```

### Database Migration

```bash
# Reset migrations
alembic downgrade -1
alembic upgrade head
```
