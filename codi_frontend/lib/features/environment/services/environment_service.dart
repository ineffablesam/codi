import 'package:get/get.dart';

import '../../../core/api/api_client.dart';
import '../models/environment_variable.dart';

class EnvironmentService extends GetxService {
  /// List all environment variables for a project
  Future<List<EnvironmentVariable>> listVariables(
    int projectId, {
    String? context,
  }) async {
    try {
      final queryParams = context != null ? {'context': context} : null;
      final response = await ApiClient.get(
        '/projects/$projectId/environment',
        queryParameters: queryParams,
      );

      if (!response.success) {
        throw Exception(response.error ?? 'Unknown error');
      }

      final List variables = response.data['variables'] as List;
      return variables
          .map((v) => EnvironmentVariable.fromJson(v as Map<String, dynamic>))
          .toList();
    } catch (e) {
      throw Exception('Failed to load environment variables: $e');
    }
  }

  /// Create a new environment variable
  Future<EnvironmentVariable> createVariable(
    int projectId,
    EnvironmentVariableCreate variable,
  ) async {
    try {
      final response = await ApiClient.post(
        '/projects/$projectId/environment',
        data: variable.toJson(),
      );

      if (!response.success) {
        throw Exception(response.error ?? 'Unknown error');
      }

      return EnvironmentVariable.fromJson(response.data as Map<String, dynamic>);
    } catch (e) {
      throw Exception('Failed to create environment variable: $e');
    }
  }

  /// Update an environment variable
  Future<EnvironmentVariable> updateVariable(
    int projectId,
    int variableId,
    EnvironmentVariableUpdate update,
  ) async {
    try {
      final response = await ApiClient.patch(
        '/projects/$projectId/environment/$variableId',
        data: update.toJson(),
      );

      if (!response.success) {
        throw Exception(response.error ?? 'Unknown error');
      }

      return EnvironmentVariable.fromJson(response.data as Map<String, dynamic>);
    } catch (e) {
      throw Exception('Failed to update environment variable: $e');
    }
  }

  /// Delete an environment variable
  Future<void> deleteVariable(int projectId, int variableId) async {
    try {
      final response = await ApiClient.delete('/projects/$projectId/environment/$variableId');
      if (!response.success) {
        throw Exception(response.error ?? 'Unknown error');
      }
    } catch (e) {
      throw Exception('Failed to delete environment variable: $e');
    }
  }

  /// Sync environment variables to .env file
  Future<Map<String, dynamic>> syncToFile(
    int projectId, {
    String? context,
    bool includeSecrets = true,
  }) async {
    try {
      final response = await ApiClient.post(
        '/projects/$projectId/environment/sync',
        data: {
          if (context != null) 'context': context,
          'include_secrets': includeSecrets,
        },
      );

      if (!response.success) {
        throw Exception(response.error ?? 'Unknown error');
      }

      return response.data as Map<String, dynamic>;
    } catch (e) {
      throw Exception('Failed to sync environment variables: $e');
    }
  }

  /// Ensure default environment variables exist
  Future<List<EnvironmentVariable>> ensureDefaults(int projectId) async {
    try {
      final response = await ApiClient.post(
        '/projects/$projectId/environment/ensure-defaults',
      );

      if (!response.success) {
        throw Exception(response.error ?? 'Unknown error');
      }

      final List variables = response.data['variables'] as List;
      return variables
          .map((v) => EnvironmentVariable.fromJson(v as Map<String, dynamic>))
          .toList();
    } catch (e) {
      throw Exception('Failed to ensure defaults: $e');
    }
  }
}
