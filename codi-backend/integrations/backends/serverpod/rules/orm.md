---
title: ORM & Database
priority: high
---

# ORM and Database Rules

## Defining Database Models
```yaml
class: User
table: user  # This creates the table
fields:
  email: String
  name: String
  createdAt: DateTime
indexes:
  email_idx:
    fields: email
    unique: true
```

## Querying
```dart
// Find by ID
var user = await User.db.findById(session, userId);

// Find all
var users = await User.db.find(session);

// Find with filter
var users = await User.db.find(
  session,
  where: (t) => t.email.equals('test@example.com'),
);

// Insert
var user = User(email: 'test@test.com', name: 'Test');
await User.db.insertRow(session, user);

// Update
user.name = 'Updated';
await User.db.updateRow(session, user);

// Delete
await User.db.deleteRow(session, user);
```

## Relationships
- Define relations in protocol with `relation:` field
- Serverpod handles joins automatically
- Use `include:` parameter to load related data

## Transactions
```dart
await session.db.transaction((transaction) async {
  // All operations use transaction
  await User.db.insertRow(session, user);
  await Profile.db.insertRow(session, profile);
});
```
