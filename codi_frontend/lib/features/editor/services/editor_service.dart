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

  Future<Map<String, dynamic>?> getTaskStatus(int projectId, String taskId) async {
    final response = await ApiClient.get<Map<String, dynamic>>(
      ApiEndpoints.agentTaskStatus(projectId, taskId),
    );

    return response.success ? response.data : null;
  }

  /// Stop a running task
  Future<bool> stopTask(String projectId, String taskId) async {
    final response = await ApiClient.post<Map<String, dynamic>>(
      ApiEndpoints.agentTaskStop(projectId, taskId),
    );

    return response.success;
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

  /// Get project files (flat list)
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

  /// Get file content (legacy)
  Future<String?> getFileContent(int projectId, String filePath) async {
    final response = await ApiClient.get<Map<String, dynamic>>(
      ApiEndpoints.projectFile(projectId, filePath),
    );

    if (response.success && response.data != null) {
      return response.data!['content'] as String?;
    }
    return null;
  }

  // === NEW CODE EDITOR APIs ===

  /// Get file tree (hierarchical)
  Future<Map<String, dynamic>?> getFileTree(int projectId, {String? branch}) async {
    final response = await ApiClient.get<Map<String, dynamic>>(
      ApiEndpoints.projectFilesTree(projectId),
      queryParameters: branch != null ? {'branch': branch} : null,
    );

    return response.success ? response.data : null;
  }

  /// Read file with SHA
  Future<Map<String, dynamic>?> readFile(int projectId, String filePath, {String? branch}) async {
    final response = await ApiClient.get<Map<String, dynamic>>(
      ApiEndpoints.projectFilesRead(projectId),
      queryParameters: {
        'file_path': filePath,
        if (branch != null) 'branch': branch,
      },
    );

    return response.success ? response.data : null;
  }

  /// Update file content
  Future<Map<String, dynamic>?> updateFile(
    int projectId,
    String filePath,
    String content,
    String message,
    String? sha, {
    String? branch,
  }) async {
    final response = await ApiClient.put<Map<String, dynamic>>(
      ApiEndpoints.projectFilesUpdate(projectId),
      data: {
        'file_path': filePath,
        'content': content,
        'message': message,
        if (sha != null) 'sha': sha,
        if (branch != null) 'branch': branch,
      },
    );

    return response.success ? response.data : null;
  }

  /// Get commit history
  Future<Map<String, dynamic>?> getCommitHistory(
    int projectId, {
    int page = 1,
    int perPage = 20,
    String? branch,
    String? filePath,
  }) async {
    final response = await ApiClient.get<Map<String, dynamic>>(
      ApiEndpoints.projectCommits(projectId),
      queryParameters: {
        'page': page,
        'per_page': perPage,
        if (branch != null) 'branch': branch,
        if (filePath != null) 'file_path': filePath,
      },
    );

    return response.success ? response.data : null;
  }

  /// Commit multiple files
  Future<Map<String, dynamic>?> commitMultipleFiles(
    int projectId,
    List<Map<String, dynamic>> files,
    String message,
    String branch, {
    bool createNewBranch = false,
    String? baseBranch,
  }) async {
    final response = await ApiClient.post<Map<String, dynamic>>(
      ApiEndpoints.projectCommitsMulti(projectId),
      data: {
        'files': files,
        'message': message,
        'branch': branch,
        'create_branch': createNewBranch,
        if (baseBranch != null) 'base_branch': baseBranch,
      },
    );

    return response.success ? response.data : null;
  }

  /// List branches
  Future<Map<String, dynamic>?> listBranches(int projectId) async {
    final response = await ApiClient.get<Map<String, dynamic>>(
      ApiEndpoints.projectBranches(projectId),
    );

    return response.success ? response.data : null;
  }

  /// Create branch
  Future<Map<String, dynamic>?> createBranch(
    int projectId,
    String branchName,
    String baseBranch,
  ) async {
    final response = await ApiClient.post<Map<String, dynamic>>(
      ApiEndpoints.projectBranches(projectId),
      data: {
        'branch_name': branchName,
        'base_branch': baseBranch,
      },
    );

    return response.success ? response.data : null;
  }
}

