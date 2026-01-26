class ChatSession {
  final String id;
  final int projectId;
  final String title;
  final int messageCount;
  final DateTime? lastMessageAt;
  final DateTime createdAt;
  final bool isArchived;

  ChatSession({
    required this.id,
    required this.projectId,
    required this.title,
    required this.messageCount,
    this.lastMessageAt,
    required this.createdAt,
    this.isArchived = false,
  });

  factory ChatSession.fromJson(Map<String, dynamic> json) {
    return ChatSession(
      id: json['id'],
      projectId: json['project_id'],
      title: json['title'],
      messageCount: json['message_count'],
      lastMessageAt: json['last_message_at'] != null
          ? DateTime.parse(json['last_message_at'])
          : null,
      createdAt: DateTime.parse(json['created_at']),
      isArchived: json['archived_at'] != null,
    );
  }
}

class ChatMessage {
  final String id;
  final String sessionId;
  final String role;
  final String content;
  final Map<String, dynamic>? toolCalls;
  final DateTime createdAt;

  ChatMessage({
    required this.id,
    required this.sessionId,
    required this.role,
    required this.content,
    this.toolCalls,
    required this.createdAt,
  });

  factory ChatMessage.fromJson(Map<String, dynamic> json) {
    return ChatMessage(
      id: json['id'],
      sessionId: json['session_id'],
      role: json['role'],
      content: json['content'],
      toolCalls: json['tool_calls'],
      createdAt: DateTime.parse(json['created_at']),
    );
  }
}
