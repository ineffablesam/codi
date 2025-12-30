/// Editor service for API calls
library;

import '../../../core/api/api_client.dart';
import '../../../core/constants/api_endpoints.dart';

/// Editor service for project file and agent operations
class EditorService {
  /// Submit a task to agents
  Future<Map<String, dynamic>?> submitTask(int projectId, String message) async {
    final response = await ApiClient.post<Map<String, dynamic>>(
      ApiEndpoints.agentTask(projectId),
      data: {'message': message, 'project_id': projectId},
    );

    return response.success ? response.data : null;
  }

  /// Get task status
  Future<Map<String, dynamic>?> getTaskStatus(int projectId, String taskId) async {
    final response = await ApiClient.get<Map<String, dynamic>>(
      ApiEndpoints.agentTaskStatus(projectId, taskId),
    );

    return response.success ? response.data : null;
  }

  /// Get agent operation history
  Future<List<Map<String, dynamic>>> getAgentHistory(int projectId, {int limit = 50}) async {
    final response = await ApiClient.get<Map<String, dynamic>>(
      ApiEndpoints.agentHistory(projectId),
      queryParameters: {'limit': limit},
    );

    if (response.success && response.data != null) {
      return (response.data!['operations'] as List?)
              ?.map((o) => o as Map<String, dynamic>)
              .toList() ??
          [];
    }
    return [];
  }

  /// Get project files
  Future<List<Map<String, dynamic>>> getFiles(int projectId, {String path = ''}) async {
    final response = await ApiClient.get<Map<String, dynamic>>(
      ApiEndpoints.projectFiles(projectId),
      queryParameters: {'path': path},
    );

    if (response.success && response.data != null) {
      return (response.data!['files'] as List?)
              ?.map((f) => f as Map<String, dynamic>)
              .toList() ??
          [];
    }
    return [];
  }

  /// Get file content
  Future<String?> getFileContent(int projectId, String filePath) async {
    final response = await ApiClient.get<Map<String, dynamic>>(
      ApiEndpoints.projectFile(projectId, filePath),
    );

    if (response.success && response.data != null) {
      return response.data!['content'] as String?;
    }
    return null;
  }
}
