/// Editor controller
library;

import 'package:flutter/material.dart';
import 'package:get/get.dart';

import '../../../core/api/websocket_client.dart';
import '../../../core/storage/shared_prefs.dart';
import '../../../core/utils/logger.dart';
import '../../projects/models/project_model.dart';
import '../../projects/services/project_service.dart';

/// Main editor controller managing project state
class EditorController extends GetxController {
  final ProjectService _projectService = ProjectService();
  late final WebSocketClient _webSocketClient;

  // State
  final Rx<ProjectModel?> currentProject = Rx<ProjectModel?>(null);
  final isLoading = false.obs;
  final isAgentWorking = false.obs;
  final buildProgress = 0.0.obs;
  final previewUrl = RxnString();
  final errorMessage = RxnString();

  @override
  void onInit() {
    super.onInit();
    _webSocketClient = Get.find<WebSocketClient>();
    _loadProject();
  }

  /// Load project from route parameter
  Future<void> _loadProject() async {
    final projectIdParam = Get.parameters['id'];
    if (projectIdParam == null) {
      errorMessage.value = 'No project ID provided';
      return;
    }

    final projectId = int.tryParse(projectIdParam);
    if (projectId == null) {
      errorMessage.value = 'Invalid project ID';
      return;
    }

    isLoading.value = true;
    errorMessage.value = null;

    try {
      final project = await _projectService.getProject(projectId);
      if (project != null) {
        currentProject.value = project;
        previewUrl.value = project.deploymentUrl;
        await SharedPrefs.setLastProjectId(projectId);

        // Connect to WebSocket
        await _webSocketClient.connect(projectId.toString());
      } else {
        errorMessage.value = 'Project not found';
      }
    } catch (e) {
      AppLogger.error('Failed to load project', error: e);
      errorMessage.value = 'Failed to load project';
    } finally {
      isLoading.value = false;
    }
  }

  /// Update agent working status
  void setAgentWorking(bool working) {
    isAgentWorking.value = working;
  }

  /// Update build progress
  void updateBuildProgress(double progress) {
    buildProgress.value = progress;
  }

  /// Update preview URL after deployment
  void updatePreviewUrl(String url) {
    previewUrl.value = url;
    
    // Also update project model
    if (currentProject.value != null) {
      currentProject.value = ProjectModel(
        id: currentProject.value!.id,
        name: currentProject.value!.name,
        description: currentProject.value!.description,
        githubRepoFullName: currentProject.value!.githubRepoFullName,
        githubRepoUrl: currentProject.value!.githubRepoUrl,
        githubCurrentBranch: currentProject.value!.githubCurrentBranch,
        status: 'active',
        deploymentUrl: url,
        lastBuildStatus: 'success',
        lastBuildAt: DateTime.now(),
        createdAt: currentProject.value!.createdAt,
        updatedAt: DateTime.now(),
      );
    }
  }

  /// Refresh project data
  Future<void> refresh() async {
    if (currentProject.value != null) {
      final project = await _projectService.getProject(currentProject.value!.id);
      if (project != null) {
        currentProject.value = project;
        previewUrl.value = project.deploymentUrl;
      }
    }
  }

  @override
  void onClose() {
    _webSocketClient.disconnect();
    super.onClose();
  }
}
