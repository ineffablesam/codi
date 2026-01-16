---
name: User Profile Model
description: Complete user model with table definition
tags: [model, database, user]
---

```yaml
# File: protocol/user.yaml
class: User
table: user
fields:
  email: String
  name: String
  profileImageUrl: String?
  createdAt: DateTime
  updatedAt: DateTime
indexes:
  email_idx:
    fields: email
    unique: true
```

After creating this file, run:
```bash
serverpod generate
serverpod create-migration create_user_table
```
