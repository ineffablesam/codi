/// Initial dependency injection binding
library;

import 'package:get/get.dart';

import '../core/api/api_service.dart';
import '../core/api/websocket_client.dart';
import '../features/auth/controllers/auth_controller.dart';

/// Initial binding for app-wide dependencies
class InitialBinding extends Bindings {
  @override
  void dependencies() {
    // Register API service (required by controllers)
    Get.put(ApiService(), permanent: true);
    
    // Register WebSocket client
    Get.put(WebSocketClient(), permanent: true);
    
    // Register auth controller (global)
    Get.put(AuthController(), permanent: true);
  }
}
