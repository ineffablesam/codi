import 'package:get/get.dart';
import 'package:flutter/material.dart';
import '../models/chat_session_model.dart';
import '../services/chat_service.dart';
import 'editor_controller.dart';
import 'agent_chat_controller.dart';

class MultiChatController extends GetxController {
  final ChatService _chatService = Get.put(ChatService());
  final EditorController _editorController = Get.find<EditorController>();
  
  // State
  final sessions = <ChatSession>[].obs;
  final activeSession = Rxn<ChatSession>();
  final isLoading = false.obs;

  @override
  void onInit() {
    super.onInit();
    // Load sessions when project changes
    ever(_editorController.currentProject, (project) {
      if (project != null) {
        loadSessions();
      } else {
        sessions.clear();
        activeSession.value = null;
      }
    });
  }

  Future<void> loadSessions() async {
    final projectId = _editorController.currentProject.value?.id;
    if (projectId == null) return;

    isLoading.value = true;
    try {
      final list = await _chatService.getSessions(projectId);
      sessions.value = list;
      
      // Auto-select most recent non-archived session or create new
      if (activeSession.value == null && list.isNotEmpty) {
        await switchSession(list.first.id);
      } else if (list.isEmpty) {
        await createNewChat();
      }
    } finally {
      isLoading.value = false;
    }
  }

  Future<void> createNewChat() async {
    final projectId = _editorController.currentProject.value?.id;
    if (projectId == null) return;

    final session = await _chatService.createSession(projectId);
    if (session != null) {
      sessions.insert(0, session);
      await switchSession(session.id);
    }
  }

  Future<void> switchSession(String sessionId) async {
    final session = sessions.firstWhereOrNull((s) => s.id == sessionId);
    if (session == null) return;

    activeSession.value = session;
    
    // Notify AgentChatController to switch context
    try {
      final chatController = Get.find<AgentChatController>();
      await chatController.switchSession(session);
    } catch (_) {
      // Chat controller might not be active yet
    }
  }

  Future<void> deleteActiveSession() async {
    final session = activeSession.value;
    if (session == null) return;

    await _chatService.deleteSession(session.id);
    sessions.removeWhere((s) => s.id == session.id);
    
    if (sessions.isNotEmpty) {
      switchSession(sessions.first.id);
    } else {
      createNewChat();
    }
  }
}
