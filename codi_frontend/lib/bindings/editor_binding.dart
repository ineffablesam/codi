/// Editor feature binding
library;

import 'package:get/get.dart';

import '../features/editor/controllers/agent_chat_controller.dart';
import '../features/editor/controllers/code_editor_controller.dart';
import '../features/editor/controllers/commit_panel_controller.dart';
import '../features/editor/controllers/editor_controller.dart';
import '../features/editor/controllers/file_tree_controller.dart';
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
    // Code editor controllers
    Get.lazyPut(() => FileTreeController());
    Get.lazyPut(() => CodeEditorController());
    Get.lazyPut(() => CommitPanelController());
  }
}

