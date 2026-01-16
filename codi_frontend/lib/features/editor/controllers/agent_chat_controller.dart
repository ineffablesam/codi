/// Agent chat controller - simplified
library;

import 'dart:async';

import 'package:flutter/material.dart';
import 'package:get/get.dart';

import '../../../core/api/websocket_client.dart';
import '../../../core/constants/app_colors.dart';
import '../../../core/utils/logger.dart';
import '../models/agent_message_model.dart';
import '../services/editor_service.dart';
import 'editor_controller.dart';
import 'preview_controller.dart';

/// Controller for agent chat panel
class AgentChatController extends GetxController {
  final EditorService _editorService = EditorService();
  late final WebSocketClient _webSocketClient;
  late final EditorController _editorController;
  
  final ScrollController scrollController = ScrollController();
  final TextEditingController textController = TextEditingController();
  
  StreamSubscription? _messageSubscription;

  // State
  final messages = <AgentMessage>[].obs;
  final isAgentWorking = false.obs;
  final isTyping = false.obs;
  final isSending = false.obs;
  final currentTaskId = RxnString();

  @override
  void onInit() {
    super.onInit();
    _webSocketClient = Get.find<WebSocketClient>();
    _editorController = Get.find<EditorController>();
    _subscribeToMessages();
  }

  /// Subscribe to WebSocket messages
  void _subscribeToMessages() {
    _messageSubscription = _webSocketClient.messageStream.listen(
      _handleMessage,
      onError: (error) {
        AppLogger.error('WebSocket stream error', error: error);
      },
    );
  }

  /// Handle incoming WebSocket message
  void _handleMessage(Map<String, dynamic> data) {
    final messageType = data['type'] as String?;
    
    // Skip ping/pong
    if (messageType == 'ping' || messageType == 'pong') return;

    // Parse message
    final message = AgentMessage.fromWebSocket(data);

    // Update controller states based on message type
    switch (message.type) {
      case MessageType.agentResponse:
      case MessageType.conversationalResponse:
        // Chat response - display and stop working
        addMessage(message);
        isTyping.value = false;
        isAgentWorking.value = false;
        break;

      case MessageType.agentStatus:
        addMessage(message);
        if (message.status == 'started' || message.status == 'thinking') {
          isAgentWorking.value = true;
          isTyping.value = true;
          _editorController.setAgentWorking(true);
        } else if (message.status == 'completed' || message.status == 'failed') {
          isAgentWorking.value = false;
          isTyping.value = false;
          _editorController.setAgentWorking(false);
        }
        break;

      case MessageType.toolExecution:
      case MessageType.toolResult:
      case MessageType.fileOperation:
      case MessageType.gitOperation:
        // Operation messages display in chat
        addMessage(message);
        break;

      case MessageType.buildProgress:
        addMessage(message);
        // Set building state on preview controller
        try {
          final previewController = Get.find<PreviewController>();
          previewController.isBuilding.value = true;
          previewController.buildStage.value = message.text;
          if (message.progress != null) {
            previewController.buildProgress.value = message.progress!;
            _editorController.updateBuildProgress(message.progress!);
          }
        } catch (_) {}
        break;

      case MessageType.deploymentComplete:
        addMessage(message);
        // Clear building state
        try {
          final previewController = Get.find<PreviewController>();
          previewController.isBuilding.value = false;
        } catch (_) {}
        
        if (message.deploymentUrl != null) {
          _editorController.updatePreviewUrl(message.deploymentUrl!);
          
          // Refresh preview
          try {
            final previewController = Get.find<PreviewController>();
            previewController.updatePreviewUrl(message.deploymentUrl!);
          } catch (_) {}

          // Show success notification
          Get.snackbar(
            ' Deployed!',
            'Your app is live',
            duration: const Duration(seconds: 5),
            snackPosition: SnackPosition.TOP,
            backgroundColor: AppColors.success,
            colorText: Colors.white,
            margin: const EdgeInsets.all(16),
            mainButton: TextButton(
              onPressed: () => Get.find<PreviewController>().openInBrowser(),
              child: const Text('Open', style: TextStyle(color: Colors.white)),
            ),
          );
        }
        break;

      case MessageType.error:
        addMessage(message);
        isAgentWorking.value = false;
        isTyping.value = false;
        _editorController.setAgentWorking(false);
        Get.snackbar(
          'Agent Error',
          message.text,
          duration: const Duration(seconds: 5),
          snackPosition: SnackPosition.TOP,
          backgroundColor: AppColors.error,
          colorText: Colors.white,
          margin: const EdgeInsets.all(16),
        );
        break;

      case MessageType.user:
        // User messages are added directly by sendMessage()
        break;
    }
  }

  /// Add message to list
  void addMessage(AgentMessage message) {
    messages.add(message);
    
    // Auto-scroll to bottom
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (scrollController.hasClients) {
        scrollController.animateTo(
          scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  /// Send user message
  Future<void> sendMessage(String text) async {
    if (text.trim().isEmpty) return;
    if (isAgentWorking.value) return;

    final trimmedText = text.trim();
    textController.clear();

    // Add user message to chat
    final userMessage = AgentMessage.user(trimmedText);
    addMessage(userMessage);

    isSending.value = true;

    try {
      final projectId = _editorController.currentProject.value?.id;
      if (projectId == null) {
        throw Exception('No project loaded');
      }

      // Send via WebSocket (this triggers the agent workflow)
      _webSocketClient.sendUserMessage(trimmedText);

    } catch (e) {
      AppLogger.error('Failed to send message', error: e);
      Get.snackbar(
        'Error',
        'Failed to send message',
        snackPosition: SnackPosition.BOTTOM,
        backgroundColor: AppColors.error,
        colorText: Colors.white,
      );
    } finally {
      isSending.value = false;
    }
  }

  /// Stop the current running task
  Future<void> stopTask() async {
    if (!isAgentWorking.value || currentTaskId.value == null) return;

    try {
      final projectId = _editorController.currentProject.value?.id;
      if (projectId == null) return;

      final taskId = currentTaskId.value!;
      AppLogger.info('Stopping task: $taskId');

      // Call high-level API to stop task
      // We'll use editorService since it handles REST calls
      await _editorService.stopTask(projectId.toString(), taskId);
      
      // Update local state proactively
      isAgentWorking.value = false;
      isTyping.value = false;
      _editorController.setAgentWorking(false);

    } catch (e) {
      AppLogger.error('Failed to stop task', error: e);
    }
  }

  /// Clear chat history
  void clearMessages() {
    messages.clear();
  }

  @override
  void onClose() {
    _messageSubscription?.cancel();
    scrollController.dispose();
    textController.dispose();
    super.onClose();
  }
}
