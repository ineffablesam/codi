/// Deployment service
library;

import '../../../core/api/api_client.dart';
import '../models/deployment_model.dart';

/// Deployment service for API calls
class DeploymentService {
  /// Get deployments for a project
  Future<List<DeploymentModel>> getDeployments(int projectId, {int limit = 20}) async {
    final response = await ApiClient.get<Map<String, dynamic>>(
      '/projects/$projectId/deployments',
      queryParameters: {'limit': limit},
    );

    if (response.success && response.data != null) {
      return (response.data!['deployments'] as List?)
              ?.map((d) => DeploymentModel.fromJson(d as Map<String, dynamic>))
              .toList() ??
          [];
    }
    return [];
  }

  /// Get a specific deployment
  Future<DeploymentModel?> getDeployment(int projectId, int deploymentId) async {
    final response = await ApiClient.get<Map<String, dynamic>>(
      '/projects/$projectId/deployments/$deploymentId',
    );

    if (response.success && response.data != null) {
      return DeploymentModel.fromJson(response.data!);
    }
    return null;
  }
}
