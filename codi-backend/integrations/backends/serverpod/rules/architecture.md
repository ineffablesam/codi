---
title: Serverpod Architecture
priority: critical
---

# Serverpod Architecture Rules

## Project Structure
- **Server Code**: All backend logic goes in `<project>_server/` package
- **Client Code**: Auto-generated client goes in `<project>_client/` package
- **Shared Models**: Protocol definitions in `<project>_server/lib/src/protocol/` as YAML files

## Protocol Files (Models & Endpoints)
- Define models in `protocol/*.yaml` files
- Models MUST extend `SerializableModel` (auto-generated)
- Run `serverpod generate` after editing protocol files
- NEVER manually edit generated files in `lib/src/generated/`

## Endpoints
- Endpoints are Dart classes extending `Endpoint`
- Located in `lib/src/endpoints/`
- Each public method becomes an RPC callable from client
- Return types MUST be serializable (protocol models, primitives, or Lists/Maps of these)

## Database Integration
- Database models defined in protocol with `table:` directive
- Use `session.db` for database queries
- Always use parameterized queries (built-in via ORM)
- Migrations managed via `serverpod create-migration`

## Session Management
- Every endpoint method receives a `Session` object
- Use `session.auth` for authentication context
- Use `session.db` for database operations
- Use `session.messages` for WebSocket streaming
