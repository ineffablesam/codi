---
title: Flutter Widget Architecture
priority: high
---

# Flutter Architecture Rules

## Everything is a Widget
- Use StatelessWidget for static UI
- Use StatefulWidget for dynamic UI with state
- Prefer composition over inheritance

## State Management
- For simple state: setState()
- For app-wide state: Provider, Riverpod, or Bloc
- For reactive state: StreamBuilder or ValueListenableBuilder

## Common Widgets
- Container: Box model, padding, margins
- Row/Column: Flex layout
- ListView: Scrollable lists
- Stack: Overlapping widgets

## Best Practices
- Extract widgets to separate classes
- Use const constructors when possible
- Avoid deeply nested widget trees
