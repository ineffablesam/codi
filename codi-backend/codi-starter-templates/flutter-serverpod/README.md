# {{PROJECT_NAME}}

A full-stack Flutter application with Serverpod backend, auto-managed by Codi.

## Stack

- **Frontend**: Flutter Web
- **Backend**: Serverpod (Dart)
- **Database**: PostgreSQL
- **Cache**: Redis
- **Deployment**: Docker

## Project Structure

```
{{PROJECT_NAME}}/
├── {{PROJECT_NAME}}_server/    # Serverpod backend
├── {{PROJECT_NAME}}_client/    # Auto-generated client code
├── {{PROJECT_NAME}}_flutter/   # Flutter frontend
├── docker-compose.yml          # Production config
├── docker-compose.dev.yml      # Development overrides
└── .env.example                # Environment template
```

## Quick Start

### 1. Start all services

```bash
cp .env.example .env
docker-compose up -d
```

### 2. Access the application

- **Frontend**: http://localhost:3000
- **Serverpod API**: http://localhost:8080
- **Serverpod Insights**: http://localhost:8081

## Development

### Hot Reload Mode

```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

### Add a New Model

1. Create `{{PROJECT_NAME}}_server/lib/src/protocol/your_model.yaml`
2. Run code generation: `cd {{PROJECT_NAME}}_server && dart run serverpod generate`
3. Restart the server

### Add a New Endpoint

1. Create endpoint in `{{PROJECT_NAME}}_server/lib/src/endpoints/`
2. Run code generation
3. Use from Flutter: `client.yourEndpoint.methodName()`

## Database Migrations

```bash
cd {{PROJECT_NAME}}_server
dart run serverpod create-migration
dart run serverpod migrate
```

## Built with Codi

This project was generated and is managed by [Codi](https://codi.dev) - the AI-powered full-stack development platform.
