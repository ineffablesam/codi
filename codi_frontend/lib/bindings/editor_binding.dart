/// Editor feature binding
library;

import 'package:get/get.dart';

import '../features/editor/controllers/agent_chat_controller.dart';
import '../features/editor/controllers/editor_controller.dart';
import '../features/editor/controllers/preview_controller.dart';
import '../features/editor/services/editor_service.dart';

/// Editor screen binding
class EditorBinding extends Bindings {
  @override
  void dependencies() {
    Get.lazyPut(() => EditorService());
    Get.lazyPut(() => EditorController());
    Get.lazyPut(() => AgentChatController());
    Get.lazyPut(() => PreviewController());
  }
}
