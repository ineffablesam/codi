/// Implementation plan model
library;

/// Model representing an implementation plan with TODO tracking
class ImplementationPlan {
  final int id;
  final int projectId;
  final String title;
  final String userRequest;
  final String status;
  final String? estimatedTime;
  final int totalTasks;
  final int completedTasks;
  final double progress;
  final String markdownContent;
  final String filePath;
  final String? walkthroughPath;
  final DateTime createdAt;
  final DateTime? approvedAt;
  final DateTime? rejectedAt;
  final DateTime? completedAt;
  final List<PlanTask> tasks;

  ImplementationPlan({
    required this.id,
    required this.projectId,
    required this.title,
    required this.userRequest,
    required this.status,
    this.estimatedTime,
    required this.totalTasks,
    required this.completedTasks,
    required this.progress,
    required this.markdownContent,
    required this.filePath,
    this.walkthroughPath,
    required this.createdAt,
    this.approvedAt,
    this.rejectedAt,
    this.completedAt,
    this.tasks = const [],
  });

  factory ImplementationPlan.fromJson(Map<String, dynamic> json) {
    return ImplementationPlan(
      id: json['id'] as int,
      projectId: json['project_id'] as int,
      title: json['title'] as String,
      userRequest: json['user_request'] as String,
      status: json['status'] as String,
      estimatedTime: json['estimated_time'] as String?,
      totalTasks: json['total_tasks'] as int,
      completedTasks: json['completed_tasks'] as int,
      progress: (json['progress'] as num).toDouble(),
      markdownContent: json['markdown_content'] as String? ?? '',
      filePath: json['file_path'] as String,
      walkthroughPath: json['walkthrough_path'] as String?,
      createdAt: DateTime.parse(json['created_at'] as String),
      approvedAt: json['approved_at'] != null
          ? DateTime.parse(json['approved_at'] as String)
          : null,
      rejectedAt: json['rejected_at'] != null
          ? DateTime.parse(json['rejected_at'] as String)
          : null,
      completedAt: json['completed_at'] != null
          ? DateTime.parse(json['completed_at'] as String)
          : null,
      tasks: (json['tasks'] as List<dynamic>?)
              ?.map((t) => PlanTask.fromJson(t as Map<String, dynamic>))
              .toList() ??
          [],
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'project_id': projectId,
        'title': title,
        'user_request': userRequest,
        'status': status,
        'estimated_time': estimatedTime,
        'total_tasks': totalTasks,
        'completed_tasks': completedTasks,
        'progress': progress,
        'markdown_content': markdownContent,
        'file_path': filePath,
        'walkthrough_path': walkthroughPath,
        'created_at': createdAt.toIso8601String(),
        'approved_at': approvedAt?.toIso8601String(),
        'rejected_at': rejectedAt?.toIso8601String(),
        'completed_at': completedAt?.toIso8601String(),
        'tasks': tasks.map((t) => t.toJson()).toList(),
      };

  ImplementationPlan copyWith({
    String? status,
    int? completedTasks,
    double? progress,
    DateTime? approvedAt,
    DateTime? rejectedAt,
    DateTime? completedAt,
    List<PlanTask>? tasks,
  }) {
    return ImplementationPlan(
      id: id,
      projectId: projectId,
      title: title,
      userRequest: userRequest,
      status: status ?? this.status,
      estimatedTime: estimatedTime,
      totalTasks: totalTasks,
      completedTasks: completedTasks ?? this.completedTasks,
      progress: progress ?? this.progress,
      markdownContent: markdownContent,
      filePath: filePath,
      walkthroughPath: walkthroughPath,
      createdAt: createdAt,
      approvedAt: approvedAt ?? this.approvedAt,
      rejectedAt: rejectedAt ?? this.rejectedAt,
      completedAt: completedAt ?? this.completedAt,
      tasks: tasks ?? this.tasks,
    );
  }

  /// Check if plan is pending user review
  bool get isPendingReview => status == 'pending_review';

  /// Check if plan is approved
  bool get isApproved => status == 'approved';

  /// Check if plan is completed
  bool get isCompleted => status == 'completed';

  /// Check if plan is in progress
  bool get isInProgress => status == 'in_progress';
}

/// Model representing a single task in an implementation plan
class PlanTask {
  final int id;
  final int planId;
  final String category;
  final String description;
  final int orderIndex;
  final bool completed;
  final DateTime? completedAt;

  PlanTask({
    required this.id,
    required this.planId,
    required this.category,
    required this.description,
    required this.orderIndex,
    required this.completed,
    this.completedAt,
  });

  factory PlanTask.fromJson(Map<String, dynamic> json) {
    return PlanTask(
      id: json['id'] as int,
      planId: json['plan_id'] as int,
      category: json['category'] as String,
      description: json['description'] as String,
      orderIndex: json['order_index'] as int,
      completed: json['completed'] as bool,
      completedAt: json['completed_at'] != null
          ? DateTime.parse(json['completed_at'] as String)
          : null,
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'plan_id': planId,
        'category': category,
        'description': description,
        'order_index': orderIndex,
        'completed': completed,
        'completed_at': completedAt?.toIso8601String(),
      };

  PlanTask copyWith({
    bool? completed,
    DateTime? completedAt,
  }) {
    return PlanTask(
      id: id,
      planId: planId,
      category: category,
      description: description,
      orderIndex: orderIndex,
      completed: completed ?? this.completed,
      completedAt: completedAt ?? this.completedAt,
    );
  }
}
