---
title: Next.js App Router
priority: critical
---

# Next.js App Router Rules

## Use App Router (Not Pages Router)
- Files go in `app/` directory
- `page.tsx` for routes
- `layout.tsx` for shared layouts
- `loading.tsx` for loading states
- `error.tsx` for error boundaries

## Server vs Client Components
- Components are Server Components by default
- Add `'use client'` at top of file for Client Components
- Use Client Components for: interactivity, hooks, browser APIs
- Use Server Components for: data fetching, sensitive operations

## Data Fetching
```typescript
// Server Component
async function Page() {
  const data = await fetch('https://api.example.com/data')
  return <div>{data}</div>
}
```

## Routing
- Folders define routes
- () groups don't create routes
- [param] for dynamic routes
- [...slug] for catch-all routes
