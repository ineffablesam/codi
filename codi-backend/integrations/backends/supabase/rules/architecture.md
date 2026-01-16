---
title: Supabase Client Setup
priority: critical
---

# Supabase Client Rules

## Initialization
```typescript
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
)
```

## Environment Variables
- `NEXT_PUBLIC_SUPABASE_URL`: Your Supabase project URL
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`: Public anonymous key
- `SUPABASE_SERVICE_ROLE_KEY`: Server-side secret key (NEVER expose to client)

## Row Level Security (RLS)
- ALWAYS enable RLS on tables containing user data
- Write policies for SELECT, INSERT, UPDATE, DELETE
- Use `auth.uid()` in policies to reference current user

## Database Queries
- Use `.from('table')` for queries
- Chain methods: `.select()`, `.insert()`, `.update()`, `.delete()`
- Always check for errors: `const { data, error } = await ...`
