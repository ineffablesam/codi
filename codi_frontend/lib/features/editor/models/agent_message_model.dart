/// Agent message model for chat display
library;

/// Message types matching backend WebSocket protocol
enum MessageType {
  user,
  agentStatus,
  conversationalResponse,
  fileOperation,
  toolExecution,
  gitOperation,
  buildProgress,
  buildStatus,
  deploymentComplete,
  reviewProgress,
  reviewIssue,
  error,
  userInputRequired,
  llmStream,
  // New multi-agent types
  backgroundTaskStarted,
  backgroundTaskProgress,
  backgroundTaskCompleted,
  delegationStatus,
  batchComplete,
}

/// Agent message model for chat panel display
class AgentMessage {
  final String text;
  final DateTime timestamp;
  final MessageType type;

  // Agent-specific fields
  final String? agent;
  final String? status;
  final Map<String, dynamic>? details;

  // File operation fields
  final String? operation;
  final String? filePath;
  final String? stats;

  // Git operation fields
  final String? commitSha;
  final String? branchName;
  final int? filesChanged;
  final int? insertions;
  final int? deletions;

  // Build progress fields
  final double? progress;
  final String? stage;
  final String? workflowUrl;

  // Deployment fields
  final String? deploymentUrl;
  final String? buildTime;
  final String? size;

  // Error fields
  final String? error;
  final String? errorDetails;

  // Tool execution fields
  final String? tool;

  // Review fields
  final String? severity;
  final int? line;

  // User input fields
  final String? question;
  final List<String>? options;

  // Background task fields (new for multi-agent)
  final String? taskId;
  final String? sessionId;
  final String? category;
  final String? duration;

  // Delegation fields (new for multi-agent)
  final String? fromAgent;
  final String? toAgent;
  final String? expectedOutcome;

  // Grouped progress fields (new for progressive UI)
  final List<Map<String, dynamic>>? steps;
  final bool? isWorking;

  AgentMessage({
    required this.text,
    required this.timestamp,
    required this.type,
    this.agent,
    this.status,
    this.details,
    this.operation,
    this.filePath,
    this.stats,
    this.commitSha,
    this.branchName,
    this.filesChanged,
    this.insertions,
    this.deletions,
    this.progress,
    this.stage,
    this.workflowUrl,
    this.deploymentUrl,
    this.buildTime,
    this.size,
    this.error,
    this.errorDetails,
    this.tool,
    this.severity,
    this.line,
    this.question,
    this.options,
    // Background task fields
    this.taskId,
    this.sessionId,
    this.category,
    this.duration,
    // Delegation fields
    this.fromAgent,
    this.toAgent,
    this.expectedOutcome,
    // Grouped progress fields
    this.steps,
    this.isWorking,
  });

  /// Create from WebSocket JSON
  factory AgentMessage.fromWebSocket(Map<String, dynamic> json) {
    MessageType type;
    switch (json['type']) {
      case 'agent_status':
        type = MessageType.agentStatus;
        break;
      case 'conversational_response': // New: instant chat
        type = MessageType.conversationalResponse;
        break;
      case 'file_operation':
        type = MessageType.fileOperation;
        break;
      case 'tool_execution':
        type = MessageType.toolExecution;
        break;
      case 'git_operation':
        type = MessageType.gitOperation;
        break;
      case 'build_progress':
        type = MessageType.buildProgress;
        break;
      case 'build_status':
        type = MessageType.buildStatus;
        break;
      case 'deployment_complete':
        type = MessageType.deploymentComplete;
        break;
      case 'review_progress':
        type = MessageType.reviewProgress;
        break;
      case 'review_issue':
        type = MessageType.reviewIssue;
        break;
      case 'agent_error':
        type = MessageType.error;
        break;
      case 'user_input_required':
        type = MessageType.userInputRequired;
        break;
      case 'llm_stream':
        type = MessageType.llmStream;
        break;
      case 'background_task_started':
        type = MessageType.backgroundTaskStarted;
        break;
      case 'background_task_progress':
        type = MessageType.backgroundTaskProgress;
        break;
      case 'background_task_completed':
        type = MessageType.backgroundTaskCompleted;
        break;
      case 'delegation_status':
        type = MessageType.delegationStatus;
        break;
      default:
        type = MessageType.agentStatus;
    }

    final details = json['details'] as Map<String, dynamic>?;

    // Extract text content - handle both string and list
    String messageText = '';
    if (json['type'] == 'llm_stream') {
      final chunk = json['chunk'];
      messageText = _extractText(chunk);
    } else {
      final message = json['message'];
      messageText = _extractText(message);
    }

    return AgentMessage(
      text: messageText,
      timestamp: json['timestamp'] != null
          ? DateTime.parse(json['timestamp'] as String)
          : DateTime.now(),
      type: type,
      agent: json['agent'] as String?,
      status: json['status'] as String?,
      details: details,
      operation: json['operation'] as String?,
      filePath: json['file_path'] as String?,
      stats: json['stats'] as String?,
      commitSha: json['commit_sha'] as String?,
      branchName: json['branch_name'] as String?,
      filesChanged: json['files_changed'] as int?,
      insertions: json['insertions'] as int?,
      deletions: json['deletions'] as int?,
      progress: (json['progress'] as num?)?.toDouble(),
      stage: json['stage'] as String?,
      workflowUrl: json['workflow_url'] as String?,
      deploymentUrl: json['deployment_url'] as String?,
      buildTime: details?['build_time'] as String?,
      size: details?['size'] as String?,
      error: json['error'] as String?,
      errorDetails: details?.toString(),
      tool: json['tool'] as String?,
      severity: json['severity'] as String?,
      line: json['line'] as int?,
      question: json['question'] as String?,
      options: (json['options'] as List?)?.cast<String>(),
      // Background task fields
      taskId: json['task_id'] as String?,
      sessionId: json['session_id'] as String?,
      category: json['category'] as String?,
      duration: json['duration'] as String?,
      // Delegation fields
      fromAgent: json['from_agent'] as String?,
      toAgent: json['to_agent'] as String?,
      expectedOutcome: json['expected_outcome'] as String?,
      // Grouped progress fields
      steps: (json['steps'] as List?)?.cast<Map<String, dynamic>>(),
      isWorking: json['is_working'] as bool?,
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

  /// Get formatted stats for git operations
  String get gitStats {
    if (filesChanged != null && insertions != null && deletions != null) {
      return '$filesChanged files, +$insertions/-$deletions';
    }
    if (stats != null) return stats!;
    return '';
  }

  /// Get steps from details if available
  List<String> get planSteps {
    if (details != null && details!['steps'] is List) {
      return (details!['steps'] as List).map((e) => e.toString()).toList();
    }
    return [];
  }

  /// Helper to extract text from either String or List response
  static String _extractText(dynamic content) {
    if (content == null) return '';

    if (content is String) {
      return content;
    } else if (content is List) {
      // If it's a list, join all text parts
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
