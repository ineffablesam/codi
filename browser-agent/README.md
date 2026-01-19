# Codi Browser Agent Service

Browser automation service for Codi using [agent-browser](https://github.com/vercel-labs/agent-browser).

## Overview

This service provides:
- **REST API** for browser control (navigate, click, type, scroll, etc.)
- **Screenshot endpoint** for AI vision-based automation
- **Accessibility snapshot** for reliable element targeting with @refs
- **WebSocket streaming** for live browser preview in Flutter app

## API Endpoints

### Sessions

```bash
# Create session
POST /session
{
  "initial_url": "https://google.com",
  "viewport": { "width": 1280, "height": 720 }
}

# Get session info
GET /session/:id

# Get screenshot (base64 PNG)
GET /session/:id/screenshot

# Get accessibility snapshot with @refs
GET /session/:id/snapshot

# Execute command
POST /session/:id/command
{
  "command": "click",
  "args": { "selector": "@e5" }
}

# Close session
DELETE /session/:id

# List all sessions
GET /sessions
```

### Commands

| Command | Args | Description |
|---------|------|-------------|
| `navigate` | `url` | Navigate to URL |
| `click` | `selector` | Click element |
| `fill` | `selector`, `text` | Clear and fill input |
| `type` | `selector`, `text` | Type into element |
| `press` | `key` | Press key (Enter, Tab, etc.) |
| `scroll` | `direction`, `amount` | Scroll page |
| `wait` | `selector` or `ms` | Wait for element/time |
| `get_text` | `selector` | Extract text |
| `hover` | `selector` | Hover element |
| `back` | - | Navigate back |
| `forward` | - | Navigate forward |
| `reload` | - | Reload page |

### WebSocket Streaming

Connect to `ws://localhost:3001/stream?session=SESSION_ID` for live screenshots.

## Development

```bash
npm install
npm run dev
```

## Docker

```bash
docker build -t codi-browser-agent .
docker run -p 3001:3001 codi-browser-agent
```
