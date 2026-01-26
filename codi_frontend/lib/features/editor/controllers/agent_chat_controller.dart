/// Agent chat controller - simplified
library;

import 'dart:async';

import 'package:flutter/material.dart';
import 'package:get/get.dart';

import '../../../core/api/websocket_client.dart';
import '../../../core/constants/app_colors.dart';
import '../../../core/utils/logger.dart';
import '../../planning/controllers/planning_controller.dart';
import '../../projects/controllers/project_setup_controller.dart';
import '../models/agent_message_model.dart';
import '../models/chat_session_model.dart';
import '../services/chat_service.dart';
import '../services/editor_service.dart';
import 'browser_agent_controller.dart';
import 'editor_controller.dart';
import 'multi_chat_controller.dart';
import 'preview_controller.dart';

/// Controller for agent chat panel
class AgentChatController extends GetxController {
  final EditorService _editorService = EditorService();
  late final WebSocketClient _webSocketClient;
  late final EditorController _editorController;

  final ScrollController scrollController = ScrollController();
  final TextEditingController textController = TextEditingController();
  final focusNode = FocusNode();
  StreamSubscription? _messageSubscription;

  // State
  final messages = <AgentMessage>[].obs;
  final isAgentWorking = false.obs;
  final isTyping = false.obs;
  final isSending = false.obs;
  final currentTaskId = RxnString();
  final isInputBlocked = false.obs;

  // Multi-chat integration
  final currentSessionId = RxnString();
  final ChatService _chatService = Get.put(ChatService());
  late final MultiChatController _multiChatController;
  late final ProjectSetupController _projectSetupController;

  final isChatListDrawerOpen = false.obs;
  final currentChatTitle = ''.obs;

  // Track when work started and if tools have been used (to distinguish quick conversations)
  final Rxn<DateTime> workingStartTime = Rxn<DateTime>();
  final hasToolActivity = false.obs;
  final showGeneratingIndicator = false.obs;
  Timer? _generatingTimer;

  // Browser agent mode
  final isBrowserAgentMode = false.obs;

  // Plan approval state
  final currentPendingPlanId = RxnInt();
  final isAwaitingApproval = false.obs;

  final isFocused = false.obs;

  @override
  void onInit() {
    super.onInit();
    _webSocketClient = Get.find<WebSocketClient>();
    _editorController = Get.find<EditorController>();
    _subscribeToMessages();
    focusNode.addListener(() {
      isFocused.value = focusNode.hasFocus;
    });

    // Initialize controllers lazily
    _multiChatController = Get.put(MultiChatController());
    _projectSetupController = Get.put(ProjectSetupController());

    // Listen to setup stage to block input
    ever(_projectSetupController.isInitialSetup, (isInitial) {
      isInputBlocked.value = isInitial || isAgentWorking.value;
    });

    // Also block/unblock based on agent working state
    ever(isAgentWorking, (working) {
      isInputBlocked.value =
          working || _projectSetupController.isInitialSetup.value;
    });
    // Periodically check if we should show the generating indicator
    _generatingTimer = Timer.periodic(const Duration(seconds: 1), (_) {
      _updateGeneratingStatus();
    });
  }

  void _updateGeneratingStatus() {
    if (!isAgentWorking.value || isAwaitingApproval.value) {
      showGeneratingIndicator.value = false;
      return;
    }

    final startTime = workingStartTime.value;
    if (startTime == null) {
      showGeneratingIndicator.value = false;
      return;
    }

    final elapsed = DateTime.now().difference(startTime).inSeconds;

    // Show if tools are active OR if it's been more than 20 seconds
    // to distinguish long-running tasks from quick conversations
    showGeneratingIndicator.value = hasToolActivity.value || elapsed >= 20;
  }

  // Add these methods
  void toggleChatListDrawer() {
    isChatListDrawerOpen.value = !isChatListDrawerOpen.value;
  }

  void openChatListDrawer() {
    isChatListDrawerOpen.value = true;
  }

  void closeChatListDrawer() {
    isChatListDrawerOpen.value = false;
  }

  void updateCurrentChatTitle(String title) {
    currentChatTitle.value = title;
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

  /// Toggle browser agent mode
  void toggleBrowserAgentMode() {
    isBrowserAgentMode.toggle();

    // Auto-switch to browser tab when enabling browser mode
    if (isBrowserAgentMode.value) {
      _editorController.setTab(EditorTab.browser);
    }
  }

  /// Handle incoming WebSocket message
  void _handleMessage(Map<String, dynamic> data) {
    final messageType = data['type'] as String?;

    // Skip ping/pong and browser frames (frames are handled by BrowserAgentController)
    if (messageType == 'ping' ||
        messageType == 'pong' ||
        messageType == 'browser_frame' ||
        messageType == "browser_url_changed") {
      return;
    }

    // Parse message
    final message = AgentMessage.fromWebSocket(data);

    // Update controller states based on message type
    switch (message.type) {
      case MessageType.taskSubmitted:
        // Task was submitted to queue - store the task ID for stopping
        if (message.taskId != null) {
          currentTaskId.value = message.taskId;
        }
        isAgentWorking.value = true;
        break;

      case MessageType.agentResponse:
      case MessageType.conversationalResponse:
        // Chat response - display and stop working
        addMessage(message);
        isTyping.value = false;
        isAgentWorking.value = false;
        currentTaskId.value = null; // Clear task ID when done
        _editorController.setAgentWorking(false);
        break;

      case MessageType.agentStatus:
        // Only add thinking/planning status if we don't already have one showing
        if (message.status == 'started' ||
            message.status == 'thinking' ||
            message.status == 'planning') {
          // Check if we already have a thinking indicator
          final hasThinking = messages.any((m) =>
              m.type == MessageType.agentStatus &&
              (m.status == 'thinking' ||
                  m.status == 'started' ||
                  m.status == 'planning'));
          if (!hasThinking) {
            addMessage(message);
          }
          isAgentWorking.value = true;
          isTyping.value = true;
          // Track when work started
          workingStartTime.value ??= DateTime.now();
          _editorController.setAgentWorking(true);
        } else if (message.status == 'completed' ||
            message.status == 'failed' ||
            message.status == 'stopped') {
          // But show "failed" so user knows if something went wrong
          if (message.status == 'failed') {
            addMessage(message);
          } else {
            // For completed/stopped, we don't add a new message,
            // but we MUST remove the previous "thinking/started" indication
            messages.removeWhere((m) =>
                m.type == MessageType.agentStatus &&
                (m.status == 'thinking' ||
                    m.status == 'started' ||
                    m.status == 'planning'));
          }
          isAgentWorking.value = false;
          isTyping.value = false;
          currentTaskId.value = null; // Clear task ID on completion
          // Reset tracking
          workingStartTime.value = null;
          hasToolActivity.value = false;
          _editorController.setAgentWorking(false);
        } else {
          // Other status types (executing, awaiting_approval, etc.)
          addMessage(message);
        }
        break;

      case MessageType.toolExecution:
      case MessageType.toolResult:
      case MessageType.fileOperation:
      case MessageType.gitOperation:
        // Mark that we have tool activity (not just a quick conversation)
        hasToolActivity.value = true;
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
        // Reset tracking
        currentTaskId.value = null;
        isAgentWorking.value = false;
        isTyping.value = false;
        workingStartTime.value = null;
        hasToolActivity.value = false;
        _editorController.setAgentWorking(false);
        break;

      case MessageType.error:
        addMessage(message);
        isAgentWorking.value = false;
        isTyping.value = false;
        currentTaskId.value = null; // Clear task ID on error
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

      case MessageType.planCreated:
        // Plan created - show in chat and wait for approval
        addMessage(message);
        currentPendingPlanId.value = message.planId;
        isAwaitingApproval.value = true;
        isTyping.value = false;
        // Keep isAgentWorking true because agent is waiting for approval

        // Set plan data in PlanningController for review screen
        if (message.planId != null && message.planMarkdown != null) {
          try {
            final planningController = Get.find<PlanningController>();
            planningController.setFromAgentData(
              planId: message.planId!,
              markdown: message.planMarkdown!,
              userRequest: message.userRequest,
            );
          } catch (_) {
            // PlanningController not registered, navigation will load from API
          }
        }
        break;

      case MessageType.planApproved:
        addMessage(message);
        currentPendingPlanId.value = null;
        isAwaitingApproval.value = false;
        // Agent continues working after approval
        isTyping.value = true;
        break;

      case MessageType.planRejected:
        addMessage(message);
        currentPendingPlanId.value = null;
        isAwaitingApproval.value = false;
        isAgentWorking.value = false;
        isTyping.value = false;
        _editorController.setAgentWorking(false);
        break;

      case MessageType.walkthroughReady:
        addMessage(message);
        // Navigate to walkthrough screen with confetti celebration
        if (message.walkthroughContent != null) {
          Get.toNamed('/walkthrough', arguments: {
            'planId': message.planId,
            'content': message.walkthroughContent,
          });
        }
        break;

      case MessageType.taskSubmitted:
        // Show thinking indicator instead of "task submitted" text
        // Add a synthetic thinking status message that will be replaced when response arrives
        final thinkingMessage = AgentMessage(
          text: '',
          timestamp: DateTime.now(),
          type: MessageType.agentStatus,
          status: 'thinking',
        );
        addMessage(thinkingMessage);
        isAgentWorking.value = true;
        isTyping.value = true;
        _editorController.setAgentWorking(true);
        break;

      case MessageType.browserAction:
        // Show browser navigation/action in chat
        addMessage(message);
        hasToolActivity.value = true;
        break;

      case MessageType.browserStatus:
        // Show browser lifecycle events
        if (message.status == 'started') {
          addMessage(message);
          isAgentWorking.value = true;
          isTyping.value = true;
        } else if (message.status == 'completed' || message.status == 'error') {
          addMessage(message);
          isAgentWorking.value = false;
          isTyping.value = false;
          currentTaskId.value = null;
          _editorController.setAgentWorking(false);
        }

        // Forward URL updates to browser controller
        if (message.browserUrl != null) {
          try {
            final browserController = Get.find<BrowserAgentController>();
            browserController.currentUrl.value = message.browserUrl!;
          } catch (_) {
            // BrowserAgentController not registered, ignore
          }
        }
        break;

      case MessageType.user:
        // User messages are added directly by sendMessage()
        break;
    }
  }

  /// Add message to list
  void addMessage(AgentMessage message) {
    // Auto-collapse previous tool execution messages
    if (message.type == MessageType.toolExecution ||
        message.type == MessageType.toolResult) {
      for (int i = messages.length - 1; i >= 0; i--) {
        if (messages[i].type == MessageType.toolExecution ||
            messages[i].type == MessageType.toolResult) {
          messages[i].isCollapsed = true;
        }
      }
    }

    // Remove previous thinking messages when a new substantive message arrives
    if (message.type != MessageType.agentStatus ||
        (message.status != 'thinking' &&
            message.status != 'started' &&
            message.status != 'planning')) {
      messages.removeWhere((m) =>
          m.type == MessageType.agentStatus &&
          (m.status == 'thinking' ||
              m.status == 'started' ||
              m.status == 'planning'));
    }

    // Skip empty tool results to reduce clutter
    if (message.type == MessageType.toolResult) {
      final result = message.toolResult;
      if (result == null ||
          result.trim().isEmpty ||
          result == 'Success' ||
          result == 'Done') {
        // Don't add empty/trivial results, just return
        return;
      }
    }

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

      // Send via WebSocket with browser mode flag and session ID
      _webSocketClient.sendMessage({
        'type': 'user_message',
        'message': trimmedText,
        'project_id': projectId,
        'browser_mode': isBrowserAgentMode.value,
        'session_id': currentSessionId.value,
      });
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
    if (!isAgentWorking.value) return;

    // 1. IMPROVEMENT: Reset UI state IMMEDIATELY (Instant Stop)
    isAgentWorking.value = false;
    isTyping.value = false;
    _editorController.setAgentWorking(false);

    // Explicitly remove any "Thinking..." messages right away
    messages.removeWhere((m) =>
        m.type == MessageType.agentStatus &&
        (m.status == 'thinking' ||
            m.status == 'started' ||
            m.status == 'planning'));

    // 2. Stop coding agent if taskId exists
    if (currentTaskId.value != null) {
      try {
        final projectId = _editorController.currentProject.value?.id;
        if (projectId != null) {
          final taskId = currentTaskId.value!;
          AppLogger.info('Stopping coding task: $taskId');
          // Fire and forget - don't await to keep UI responsive
          _editorService.stopTask(projectId.toString(), taskId);
        }
      } catch (e) {
        AppLogger.error('Failed to stop coding task', error: e);
      }
    }

    // 3. Stop browser agent if active
    try {
      final browserController = Get.find<BrowserAgentController>();
      if (browserController.isSessionActive.value) {
        // Use clearSession() to fully reset UI (hide frame, show placeholder)
        // and close backend session instanty for "Instant Stop" feel
        browserController.clearSession();
      }
    } catch (e) {
      // BrowserController not found or other error
    }
  }

  /// Clear chat history
  void clearMessages() {
    messages.clear();
  }

  /// Approve the pending plan
  Future<void> approvePlan({String? comment}) async {
    if (currentPendingPlanId.value == null) return;

    final planId = currentPendingPlanId.value!;
    AppLogger.info('Approving plan: $planId');

    _webSocketClient.sendMessage({
      'type': 'plan_approval',
      'plan_id': planId,
      'approved': true,
      'comment': comment ?? 'Plan approved',
    });

    isAwaitingApproval.value = false;
  }

  /// Reject the pending plan
  Future<void> rejectPlan({String? comment}) async {
    if (currentPendingPlanId.value == null) return;

    final planId = currentPendingPlanId.value!;
    AppLogger.info('Rejecting plan: $planId');

    _webSocketClient.sendMessage({
      'type': 'plan_approval',
      'plan_id': planId,
      'approved': false,
      'comment': comment ?? 'Plan rejected',
    });

    isAwaitingApproval.value = false;
    currentPendingPlanId.value = null;
  }

  /// Switch to a different chat session
  Future<void> switchSession(ChatSession session) async {
    currentSessionId.value = session.id;
    messages.clear();

    // Load messages from API
    try {
      final history = await _chatService.getMessages(session.id);

      // Convert API messages to AgentMessage format
      final convertedMessages = history.map((m) {
        if (m.role == 'user') {
          return AgentMessage.user(m.content);
        } else {
          // Assistant message
          return AgentMessage(
            text: m.content,
            timestamp: m.createdAt,
            type: MessageType.agentResponse,
            toolResult: m.toolCalls != null ? m.toolCalls.toString() : null,
          );
        }
      }).toList();

      messages.addAll(convertedMessages);
    } catch (e) {
      AppLogger.error('Failed to load chat history', error: e);
    }
  }

  @override
  void onClose() {
    _generatingTimer?.cancel();
    _messageSubscription?.cancel();
    focusNode.dispose();
    scrollController.dispose();
    textController.dispose();
    super.onClose();
  }
}
