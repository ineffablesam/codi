/// Deployments controller
library;

import 'package:get/get.dart';

import '../../../core/utils/logger.dart';
import '../models/deployment_model.dart';
import '../services/deployment_service.dart';

/// Deployments list controller
class DeploymentsController extends GetxController {
  final DeploymentService _service = DeploymentService();

  // State
  final deployments = <DeploymentModel>[].obs;
  final isLoading = false.obs;
  final errorMessage = RxnString();
  
  int? _projectId;

  /// Load deployments for a project
  Future<void> loadDeployments(int projectId) async {
    _projectId = projectId;
    isLoading.value = true;
    errorMessage.value = null;

    try {
      final result = await _service.getDeployments(projectId);
      deployments.value = result;
    } catch (e) {
      AppLogger.error('Failed to load deployments', error: e);
      errorMessage.value = 'Failed to load deployments';
    } finally {
      isLoading.value = false;
    }
  }

  /// Refresh deployments
  Future<void> refresh() async {
    if (_projectId != null) {
      await loadDeployments(_projectId!);
    }
  }
}
