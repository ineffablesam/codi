# Knowledge Pack Authoring Guide

Quick reference for creating new integration packs.

## Structure

```
integrations/<type>/<technology>/
├── pack.yaml                 # Required: Metadata
├── rules/                    # Required: Rules by category
│   ├── architecture.md
│   ├── *.md
├── templates/               # Optional: Code templates
│   └── *.tpl
├── examples/                # Optional: Code examples
│   └── category/
│       └── *.md
└── pitfalls/                # Optional: Common mistakes
    ├── agent_traps.md       # LLM-specific mistakes
    └── common_failures.md
```

## pack.yaml Format

```yaml
name: technology_name
version: 1.0.0
pack_type: frontend|backend|deployment
description: "Short description"
compatibility:
  tool: "version_constraint"
tags: [tag1, tag2]
```

## Rules Format

**With frontmatter:**
```markdown
---
title: Rule Title
priority: critical|high|medium|low
---

# Rule Content

Use markdown for rules.
```

**Without frontmatter:**
```markdown
# Rule Title

Content (defaults to medium priority)
```

## Templates Format

```
{{variable_name}} placeholders get replaced
```

Create `.meta.yaml` alongside for metadata:
```yaml
description: "Template description"
```

## Examples Format

```markdown
---
name: Example Name
description: What this demonstrates
tags: [tag1, tag2]
---

```code here```
```

## Pitfalls Format

```yaml
---
- title: "Pitfall title"
  description: "What goes wrong"
  wrong: "Don't do this"
  correct: "Do this instead"
---
```

## Priority Guidelines

- **CRITICAL**: Must follow or code won't work
- **HIGH**: Strong recommendation, avoid if possible
- **MEDIUM**: Best practice
- **LOW**: Nice to have

## Tips

1. Keep rules focused - one concept per file
2. Use agent_traps.md for LLM-specific mistakes
3. Include code examples in rules
4. Test your pack with validation script
