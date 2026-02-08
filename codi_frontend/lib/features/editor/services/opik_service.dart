/// Opik API service for trace monitoring
library;

import 'package:codi_frontend/core/api/api_client.dart';
import 'package:codi_frontend/features/editor/models/opik_models.dart';

class OpikService {
  OpikService._();

  /// Get traces for a project with optional filtering
  static Future<TraceListResponse?> getProjectTraces({
    required int projectId,
    int page = 1,
    int pageSize = 20,
    String? traceType,
    double? minScore,
  }) async {
    final queryParams = {
      'project_id': projectId,
      'page': page,
      'page_size': pageSize,
      if (traceType != null) 'trace_type': traceType,
      if (minScore != null) 'min_score': minScore,
    };

    final response = await ApiClient.get<TraceListResponse>(
      '/opik/traces',
      queryParameters: queryParams,
      fromJson: (json) =>
          TraceListResponse.fromJson(json as Map<String, dynamic>),
    );

    return response.data;
  }

  /// Get detailed information about a specific trace
  static Future<TraceModel?> getTraceDetails(String traceId) async {
    final response = await ApiClient.get<TraceModel>(
      '/opik/traces/$traceId/details',
      fromJson: (json) => TraceModel.fromJson(json as Map<String, dynamic>),
    );

    return response.data;
  }

  /// Get statistics for a project
  static Future<ProjectStatsModel?> getProjectStats(int projectId) async {
    final response = await ApiClient.get<ProjectStatsModel>(
      '/opik/projects/$projectId/stats',
      fromJson: (json) =>
          ProjectStatsModel.fromJson(json as Map<String, dynamic>),
    );

    return response.data;
  }

  /// Get traces grouped by session (user prompts)
  static Future<GroupedTracesResponse?> getGroupedTraces(int projectId) async {
    final response = await ApiClient.get<GroupedTracesResponse>(
      '/opik/traces/grouped',
      queryParameters: {'project_id': projectId},
      fromJson: (json) =>
          GroupedTracesResponse.fromJson(json as Map<String, dynamic>),
    );

    return response.data;
  }

  /// Get traces filtered by session ID
  static Future<TraceListResponse?> getSessionTraces({
    required int projectId,
    required String sessionId,
    int page = 1,
    int pageSize = 50,
  }) async {
    final queryParams = {
      'project_id': projectId,
      'session_id': sessionId,
      'page': page,
      'page_size': pageSize,
    };

    final response = await ApiClient.get<TraceListResponse>(
      '/opik/traces',
      queryParameters: queryParams,
      fromJson: (json) =>
          TraceListResponse.fromJson(json as Map<String, dynamic>),
    );

    return response.data;
  }

  /// Get suggestions for a failed trace
  static Future<TraceSuggestion?> getTraceSuggestions(String traceId) async {
    final response = await ApiClient.get<TraceSuggestion>(
      '/opik/traces/$traceId/suggestions',
      fromJson: (json) =>
          TraceSuggestion.fromJson(json as Map<String, dynamic>),
    );

    return response.data;
  }
}
