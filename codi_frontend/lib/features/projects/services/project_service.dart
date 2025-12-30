/// Project service for API calls
library;

import '../../../core/api/api_client.dart';
import '../../../core/constants/api_endpoints.dart';
import '../models/project_model.dart';

/// Project service for API interactions
class ProjectService {
  /// Get all projects for current user
  Future<List<ProjectModel>> getProjects({int skip = 0, int limit = 20}) async {
    final response = await ApiClient.get<Map<String, dynamic>>(
      ApiEndpoints.projects,
      queryParameters: {'skip': skip, 'limit': limit},
    );

    if (response.success && response.data != null) {
      final projects = (response.data!['projects'] as List)
          .map((json) => ProjectModel.fromJson(json as Map<String, dynamic>))
          .toList();
      return projects;
    }
    return [];
  }

  /// Get a single project by ID
  Future<ProjectModel?> getProject(int id) async {
    final response = await ApiClient.get<Map<String, dynamic>>(
      ApiEndpoints.projectById(id),
    );

    if (response.success && response.data != null) {
      return ProjectModel.fromJson(response.data!);
    }
    return null;
  }

  /// Create a new project
  Future<ProjectModel?> createProject(CreateProjectRequest request) async {
    final response = await ApiClient.post<Map<String, dynamic>>(
      ApiEndpoints.projects,
      data: request.toJson(),
    );

    if (response.success && response.data != null) {
      return ProjectModel.fromJson(response.data!);
    }
    return null;
  }

  /// Update a project
  Future<ProjectModel?> updateProject(int id, Map<String, dynamic> data) async {
    final response = await ApiClient.patch<Map<String, dynamic>>(
      ApiEndpoints.projectById(id),
      data: data,
    );

    if (response.success && response.data != null) {
      return ProjectModel.fromJson(response.data!);
    }
    return null;
  }

  /// Delete (archive) a project
  Future<bool> deleteProject(int id) async {
    final response = await ApiClient.delete<void>(
      ApiEndpoints.projectById(id),
    );
    return response.success;
  }

  /// Get project files
  Future<List<Map<String, dynamic>>> getProjectFiles(int id, {String path = ''}) async {
    final response = await ApiClient.get<Map<String, dynamic>>(
      ApiEndpoints.projectFiles(id),
      queryParameters: {'path': path},
    );

    if (response.success && response.data != null) {
      return (response.data!['files'] as List)
          .map((f) => f as Map<String, dynamic>)
          .toList();
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
