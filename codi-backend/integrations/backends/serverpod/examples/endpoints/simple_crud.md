---
name: Simple CRUD Endpoint
description: Basic endpoint with database operations
tags: [crud, database, beginner]
---

```dart
// File: lib/src/endpoints/user_endpoint.dart
import 'package:serverpod/serverpod.dart';
import '../generated/protocol.dart';

class UserEndpoint extends Endpoint {
  // Get all users
  Future<List<User>> getAllUsers(Session session) async {
    return await User.db.find(session);
  }
  
  // Get user by ID
  Future<User?> getUser(Session session, int userId) async {
    return await User.db.findById(session, userId);
  }
  
  // Create user
  Future<User> createUser(Session session, User user) async {
    return await User.db.insertRow(session, user);
  }
  
  // Update user
  Future<User> updateUser(Session session, User user) async {
    return await User.db.updateRow(session, user);
  }
  
  // Delete user
  Future<void> deleteUser(Session session, int userId) async {
    var user = await User.db.findById(session, userId);
    if (user != null) {
      await User.db.deleteRow(session, user);
    }
  }
}
```
