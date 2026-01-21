/// Simplified agent message model for chat display
library;

/// Message types matching simplified backend WebSocket protocol
enum MessageType {
  // Core types
  user,
  agentStatus,
  agentResponse,
  conversationalResponse,
  taskSubmitted,
  toolExecution,
  toolResult,
  
  // Operations
  fileOperation,
  gitOperation,
  buildProgress,
  deploymentComplete,
  
  // Plan workflow
  planCreated,
  planApproved,
  planRejected,
  walkthroughReady,
  
  // Browser agent
  browserAction,
  browserStatus,
  
  // Errors
  error,
}

/// Simplified agent message for chat panel
class AgentMessage {
  final String text;
  final DateTime timestamp;
  final MessageType type;
  
  // UI state for collapsible cards
  bool isCollapsed;

  // Core fields
  final String? agent;
  final String? status;
  final Map<String, dynamic>? details;

  // Tool execution
  final String? tool;
  
  // File operation
  final String? operation;
  final String? filePath;
  final String? stats;

  // Git operation
  final String? commitSha;
  final String? branchName;

  // Build/deploy
  final double? progress;
  final String? stage;
  final String? deploymentUrl;

  // Error
  final String? error;
  
  // Result
  final String? toolResult;
  
  // Plan workflow
  final int? planId;
  final String? planMarkdown;
  final String? planFilePath;
  final String? userRequest;
  final String? walkthroughContent;
  final String? taskId;
  
  // Browser agent
  final String? browserUrl;
  final String? browserAction;
  final String? pageTitle;

  AgentMessage({
    required this.text,
    required this.timestamp,
    required this.type,
    this.isCollapsed = false,
    this.agent,
    this.status,
    this.details,
    this.tool,
    this.operation,
    this.filePath,
    this.stats,
    this.commitSha,
    this.branchName,
    this.progress,
    this.stage,
    this.deploymentUrl,
    this.error,
    this.toolResult,
    this.planId,
    this.planMarkdown,
    this.planFilePath,
    this.userRequest,
    this.walkthroughContent,
    this.taskId,
    this.browserUrl,
    this.browserAction,
    this.pageTitle,
  });

  /// Create from WebSocket JSON
  factory AgentMessage.fromWebSocket(Map<String, dynamic> json) {
    MessageType type;
    switch (json['type']) {
      case 'agent_status':
        type = MessageType.agentStatus;
        break;
      case 'agent_response':
        type = MessageType.agentResponse;
        break;
      case 'conversational_response':
        type = MessageType.conversationalResponse;
        break;
      case 'tool_execution':
        type = MessageType.toolExecution;
        break;
      case 'tool_result':
        type = MessageType.toolResult;
        break;
      case 'task_submitted':
        type = MessageType.taskSubmitted;
        break;
      case 'file_operation':
        type = MessageType.fileOperation;
        break;
      case 'git_operation':
        type = MessageType.gitOperation;
        break;
      case 'build_progress':
        type = MessageType.buildProgress;
        break;
      case 'deployment_complete':
        type = MessageType.deploymentComplete;
        break;
      case 'plan_created':
        type = MessageType.planCreated;
        break;
      case 'plan_approved':
        type = MessageType.planApproved;
        break;
      case 'plan_rejected':
        type = MessageType.planRejected;
        break;
      case 'walkthrough_ready':
        type = MessageType.walkthroughReady;
        break;
      case 'browser_action':
        type = MessageType.browserAction;
        break;
      case 'browser_status':
        type = MessageType.browserStatus;
        break;
      case 'agent_error':
        type = MessageType.error;
        break;
      default:
        type = MessageType.agentStatus;
    }

    final details = json['details'] as Map<String, dynamic>?;
    String messageText = _extractText(json['message']);
    
    // Extract file_path from input if not directly provided
    final input = json['input'] as Map<String, dynamic>?;
    String? filePath = json['file_path'] as String?;
    if (filePath == null && input != null) {
      filePath = input['path'] as String?;
    }

    return AgentMessage(
      text: messageText,
      timestamp: json['timestamp'] != null
          ? DateTime.parse(json['timestamp'] as String)
          : DateTime.now(),
      type: type,
      agent: json['agent'] as String? ?? 'codi',
      status: json['status'] as String?,
      details: details,
      tool: json['tool'] as String?,
      operation: json['operation'] as String?,
      filePath: filePath,
      stats: json['stats'] as String?,
      commitSha: json['commit_sha'] as String?,
      branchName: json['branch_name'] as String?,
      progress: (json['progress'] as num?)?.toDouble(),
      stage: json['stage'] as String?,
      deploymentUrl: json['deployment_url'] as String?,
      error: json['error'] as String?,
      toolResult: json['result'] as String?,
      planId: json['plan_id'] as int?,
      planMarkdown: json['plan_markdown'] as String?,
      planFilePath: json['plan_file_path'] as String?,
      userRequest: json['user_request'] as String?,
      walkthroughContent: json['walkthrough_content'] as String?,
      taskId: json['task_id'] as String?,
      browserUrl: json['url'] as String?,
      browserAction: json['action'] as String?,
      pageTitle: json['page_title'] as String?,
    );
  }

  /// Create a user message
  factory AgentMessage.user(String text) {
    return AgentMessage(
      text: text,
      timestamp: DateTime.now(),
      type: MessageType.user,
    );
  }

  /// Helper to extract text from response
  static String _extractText(dynamic content) {
    if (content == null) return '';
    if (content is String) return content;
    if (content is List) {
      return content.map((part) {
        if (part is Map && part.containsKey('text')) {
          return part['text'].toString();
        }
        return part.toString();
      }).join(' ');
    }
    return content.toString();
  }
}
