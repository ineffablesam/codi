/// Opik trace models for monitoring AI operations
library;

/// Evaluation score for a trace
class EvaluationModel {
  final String id;
  final String traceId;
  final String metricName;
  final double score;
  final String? reason;
  final Map<String, dynamic>? metaData;
  final DateTime createdAt;

  EvaluationModel({
    required this.id,
    required this.traceId,
    required this.metricName,
    required this.score,
    this.reason,
    this.metaData,
    required this.createdAt,
  });

  factory EvaluationModel.fromJson(Map<String, dynamic> json) {
    return EvaluationModel(
      id: json['id'] as String,
      traceId: json['trace_id'] as String,
      metricName: json['metric_name'] as String,
      score: (json['score'] as num).toDouble(),
      reason: json['reason'] as String?,
      metaData: json['meta_data'] as Map<String, dynamic>?,
      createdAt: DateTime.parse(json['created_at'] as String),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'trace_id': traceId,
      'metric_name': metricName,
      'score': score,
      'reason': reason,
      'meta_data': metaData,
      'created_at': createdAt.toIso8601String(),
    };
  }
}

/// AI operation trace
class TraceModel {
  final String id;
  final int userId;
  final int? projectId;
  final String? parentTraceId;
  final String traceType;
  final String name;
  final DateTime startTime;
  final DateTime? endTime;
  final int? durationMs;
  final Map<String, dynamic>? inputData;
  final Map<String, dynamic>? outputData;
  final Map<String, dynamic>? metaData;
  final List<String>? tags;
  final DateTime createdAt;
  final List<EvaluationModel>? evaluations;

  // Session tracking
  String? get sessionId => metaData?['session_id'] as String?;
  String? get userPrompt => metaData?['user_prompt'] as String?;

  // Computed properties for UI
  String get summaryText {
    final tool = metaData?['tool'] as String? ?? traceType;
    if (outputData != null && outputData!['result'] != null) {
      final result = outputData!['result'].toString();
      return result.length > 100 ? '${result.substring(0, 100)}...' : result;
    }
    return name;
  }

  String get confidenceLevel {
    final score = averageScore;
    if (score == null) return 'Medium';
    if (score >= 0.8) return 'High';
    if (score >= 0.5) return 'Medium';
    return 'Low';
  }

  TraceModel({
    required this.id,
    required this.userId,
    this.projectId,
    this.parentTraceId,
    required this.traceType,
    required this.name,
    required this.startTime,
    this.endTime,
    this.durationMs,
    this.inputData,
    this.outputData,
    this.metaData,
    this.tags,
    required this.createdAt,
    this.evaluations,
  });

  factory TraceModel.fromJson(Map<String, dynamic> json) {
    return TraceModel(
      id: json['id'] as String,
      userId: json['user_id'] as int,
      projectId: json['project_id'] as int?,
      parentTraceId: json['parent_trace_id'] as String?,
      traceType: json['trace_type'] as String,
      name: json['name'] as String,
      startTime: DateTime.parse(json['start_time'] as String),
      endTime: json['end_time'] != null
          ? DateTime.parse(json['end_time'] as String)
          : null,
      durationMs: json['duration_ms'] as int?,
      inputData: json['input_data'] as Map<String, dynamic>?,
      outputData: json['output_data'] as Map<String, dynamic>?,
      metaData: json['meta_data'] as Map<String, dynamic>?,
      tags: (json['tags'] as List?)?.cast<String>(),
      createdAt: DateTime.parse(json['created_at'] as String),
      evaluations: (json['evaluations'] as List?)
          ?.map((e) => EvaluationModel.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'user_id': userId,
      'project_id': projectId,
      'parent_trace_id': parentTraceId,
      'trace_type': traceType,
      'name': name,
      'start_time': startTime.toIso8601String(),
      'end_time': endTime?.toIso8601String(),
      'duration_ms': durationMs,
      'input_data': inputData,
      'output_data': outputData,
      'meta_data': metaData,
      'tags': tags,
      'created_at': createdAt.toIso8601String(),
      'evaluations': evaluations?.map((e) => e.toJson()).toList(),
    };
  }

  // Helper getters
  bool get isSuccess =>
      metaData?['status'] == 'success' || metaData?['status'] == null;

  bool get hasError => metaData?['status'] == 'error';

  double? get averageScore {
    if (evaluations == null || evaluations!.isEmpty) return null;
    final sum = evaluations!.fold<double>(0, (acc, e) => acc + e.score);
    return sum / evaluations!.length;
  }

  String get statusText {
    if (hasError) return 'Error';
    if (isSuccess) return 'Success';
    return 'Unknown';
  }

  String get durationText {
    if (durationMs == null) return 'N/A';
    if (durationMs! < 1000) return '${durationMs}ms';
    return '${(durationMs! / 1000).toStringAsFixed(2)}s';
  }

  String get toolName {
    return metaData?['tool'] as String? ?? traceType;
  }
}

/// Trace list response with pagination
class TraceListResponse {
  final List<TraceModel> traces;
  final int total;
  final int page;
  final int pageSize;

  TraceListResponse({
    required this.traces,
    required this.total,
    required this.page,
    required this.pageSize,
  });

  factory TraceListResponse.fromJson(Map<String, dynamic> json) {
    return TraceListResponse(
      traces: (json['traces'] as List)
          .map((e) => TraceModel.fromJson(e as Map<String, dynamic>))
          .toList(),
      total: json['total'] as int,
      page: json['page'] as int,
      pageSize: json['page_size'] as int,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'traces': traces.map((e) => e.toJson()).toList(),
      'total': total,
      'page': page,
      'page_size': pageSize,
    };
  }
}

/// Project statistics for Opik dashboard
class ProjectStatsModel {
  final int totalTraces;
  final int successfulTraces;
  final double successRate;
  final int averageDurationMs;
  final Map<String, int> traceTypes;
  final Map<String, int> scoreDistribution;
  final int totalEvaluations;

  ProjectStatsModel({
    required this.totalTraces,
    required this.successfulTraces,
    required this.successRate,
    required this.averageDurationMs,
    required this.traceTypes,
    required this.scoreDistribution,
    required this.totalEvaluations,
  });

  factory ProjectStatsModel.fromJson(Map<String, dynamic> json) {
    return ProjectStatsModel(
      totalTraces: json['total_traces'] as int,
      successfulTraces: json['successful_traces'] as int,
      successRate: (json['success_rate'] as num).toDouble(),
      averageDurationMs: json['average_duration_ms'] as int,
      traceTypes: Map<String, int>.from(json['trace_types'] as Map),
      scoreDistribution:
          Map<String, int>.from(json['score_distribution'] as Map),
      totalEvaluations: json['total_evaluations'] as int,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'total_traces': totalTraces,
      'successful_traces': successfulTraces,
      'success_rate': successRate,
      'average_duration_ms': averageDurationMs,
      'trace_types': traceTypes,
      'score_distribution': scoreDistribution,
      'total_evaluations': totalEvaluations,
    };
  }

  // Helper getters
  String get averageDurationText {
    if (averageDurationMs < 1000) {
      return '${averageDurationMs}ms';
    }
    return '${(averageDurationMs / 1000).toStringAsFixed(2)}s';
  }

  String get successRateText => '${(successRate * 100).toStringAsFixed(1)}%';
}

/// Group of traces by session (user prompt)
class TraceSessionGroup {
  final String sessionId;
  final String? userPrompt;
  final int totalTools;
  final int successCount;
  final int failureCount;
  final int totalDurationMs;
  final DateTime startTime;
  final DateTime? endTime;
  final List<Map<String, dynamic>> traces;

  TraceSessionGroup({
    required this.sessionId,
    this.userPrompt,
    required this.totalTools,
    required this.successCount,
    required this.failureCount,
    required this.totalDurationMs,
    required this.startTime,
    this.endTime,
    required this.traces,
  });

  factory TraceSessionGroup.fromJson(Map<String, dynamic> json) {
    return TraceSessionGroup(
      sessionId: json['session_id'] as String,
      userPrompt: json['user_prompt'] as String?,
      totalTools: json['total_tools'] as int,
      successCount: json['success_count'] as int,
      failureCount: json['failure_count'] as int,
      totalDurationMs: json['total_duration_ms'] as int,
      startTime: DateTime.parse(json['start_time'] as String),
      endTime: json['end_time'] != null
          ? DateTime.parse(json['end_time'] as String)
          : null,
      traces: List<Map<String, dynamic>>.from(json['traces'] as List),
    );
  }

  double get successRate => totalTools > 0 ? successCount / totalTools : 0.0;
}

/// Grouped traces response
class GroupedTracesResponse {
  final int totalSessions;
  final List<TraceSessionGroup> sessions;

  GroupedTracesResponse({
    required this.totalSessions,
    required this.sessions,
  });

  factory GroupedTracesResponse.fromJson(Map<String, dynamic> json) {
    return GroupedTracesResponse(
      totalSessions: json['total_sessions'] as int,
      sessions: (json['sessions'] as List)
          .map((e) => TraceSessionGroup.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }
}

/// Suggestion for a failed trace
class TraceSuggestion {
  final String traceId;
  final bool hasError;
  final String? errorMessage;
  final String? suggestion;
  final String? category;
  final String? confidence;

  TraceSuggestion({
    required this.traceId,
    required this.hasError,
    this.errorMessage,
    this.suggestion,
    this.category,
    this.confidence,
  });

  factory TraceSuggestion.fromJson(Map<String, dynamic> json) {
    return TraceSuggestion(
      traceId: json['trace_id'] as String,
      hasError: json['has_error'] as bool,
      errorMessage: json['error_message'] as String?,
      suggestion: json['suggestion'] as String?,
      category: json['category'] as String?,
      confidence: json['confidence'] as String?,
    );
  }
}
