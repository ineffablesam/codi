/// Agent message model for chat display
library;

/// Message types matching backend WebSocket protocol
enum MessageType {
  user,
  agentStatus,
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
  });

  /// Create from WebSocket JSON
  factory AgentMessage.fromWebSocket(Map<String, dynamic> json) {
    MessageType type;
    switch (json['type']) {
      case 'agent_status':
        type = MessageType.agentStatus;
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
      default:
        type = MessageType.agentStatus;
    }

    final details = json['details'] as Map<String, dynamic>?;

    return AgentMessage(
      text: (json['type'] == 'llm_stream' ? json['chunk'] : json['message']) as String? ?? '',
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
}
