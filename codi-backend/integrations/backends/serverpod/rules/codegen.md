---
title: Code Generation
priority: critical
---

# Code Generation Rules

## CRITICAL: Always Regenerate After Changes

1. **After editing ANY protocol file**: Run `serverpod generate`
2. **After database model changes**: Run `serverpod create-migration <name>`
3. **Client must be rebuilt**: After server changes, regenerate client with `serverpod generate --client`

## Protocol File Format
```yaml
class: Example
table: example  # Optional: creates database table
fields:
  name: String
  age: int?  # '?' makes it nullable
  createdAt: DateTime
```

## Generated Files - DO NOT EDIT
- `lib/src/generated/` - Auto-generated from protocol
- `lib/src/protocol/protocol.dart` - Index file
- Client package - Fully auto-generated

## Custom Code
- Put custom logic in `lib/src/endpoints/`
- Extend generated models (if needed) in separate files
- Never modify generated code directly
