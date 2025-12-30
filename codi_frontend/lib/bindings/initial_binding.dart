/// Initial dependency injection binding
library;

import 'package:get/get.dart';

import '../core/api/websocket_client.dart';
import '../features/auth/controllers/auth_controller.dart';

/// Initial binding for app-wide dependencies
class InitialBinding extends Bindings {
  @override
  void dependencies() {
    // Register global services
    Get.put(WebSocketClient(), permanent: true);
    
    // Register auth controller (global)
    Get.put(AuthController(), permanent: true);
  }
}
