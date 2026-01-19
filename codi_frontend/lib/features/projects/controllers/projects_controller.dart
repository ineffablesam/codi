/// Projects controller
library;

import 'package:flutter/material.dart';
import 'package:get/get.dart';

import '../../../config/routes.dart';
import '../../../core/constants/app_colors.dart';
import '../../../core/storage/shared_prefs.dart';
import '../../../core/utils/logger.dart';
import '../models/project_model.dart';
import '../services/project_service.dart';

/// Projects list controller
class ProjectsController extends GetxController {
  final ProjectService _projectService = ProjectService();

  // State
  final projects = <ProjectModel>[].obs;
  final Rx<ProjectModel?> selectedProject = Rx<ProjectModel?>(null);
  final isLoading = false.obs;
  final isCreating = false.obs;
  final errorMessage = RxnString();
  final currentStatus = 'active'.obs;

  @override
  void onInit() {
    super.onInit();
    loadProjects();
  }

  /// Load all projects
  Future<void> loadProjects({String? status}) async {
    if (status != null) {
      currentStatus.value = status;
    }

    isLoading.value = true;
    errorMessage.value = null;

    try {
      final result =
          await _projectService.getProjects(status: currentStatus.value);
      projects.value = result;
    } catch (e) {
      AppLogger.error('Failed to load projects', error: e);
      errorMessage.value = 'Failed to load projects';
    } finally {
      isLoading.value = false;
    }
  }

  /// Load a specific project
  Future<void> loadProject(int id) async {
    isLoading.value = true;
    errorMessage.value = null;

    try {
      final result = await _projectService.getProject(id);
      if (result != null) {
        selectedProject.value = result;
        await SharedPrefs.setLastProjectId(id);
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

  /// Create a new project with multi-platform support
  Future<bool> createProject({
    required String name,
    String? description,
    bool isPrivate = false,
    String platformType = 'mobile',
    String framework = 'flutter',
    String? backendType,
    String? deploymentPlatform,
    String? appIdea,
  }) async {
    isCreating.value = true;
    errorMessage.value = null;

    try {
      final request = CreateProjectRequest(
        name: name,
        description: description,
        isPrivate: isPrivate,
        platformType: platformType,
        framework: framework,
        backendType: backendType,
        deploymentPlatform: deploymentPlatform,
        appIdea: appIdea,
      );

      final result = await _projectService.createProject(request);

      if (result != null) {
        if (currentStatus.value == 'active') {
          projects.insert(0, result);
        }

        Get.snackbar(
          'Success!',
          'Project "${result.name}" created with ${result.frameworkLabel}',
          snackPosition: SnackPosition.BOTTOM,
          backgroundColor: AppColors.success,
          colorText: Colors.white,
          margin: const EdgeInsets.all(16),
        );

        // Navigate to editor
        Get.toNamed(AppRoutes.editor.replaceFirst(':id', result.id.toString()));
        return true;
      } else {
        errorMessage.value = 'Failed to create project';
        return false;
      }
    } catch (e) {
      AppLogger.error('Failed to create project', error: e);
      errorMessage.value = 'Failed to create project. Please try again.';
      return false;
    } finally {
      isCreating.value = false;
    }
  }

  /// Archive a project
  Future<bool> archiveProject(int id) async {
    try {
      final success = await _projectService.archiveProject(id);

      if (success) {
        projects.removeWhere((p) => p.id == id);

        Get.snackbar(
          'Archived',
          'Project has been moved to archive',
          snackPosition: SnackPosition.BOTTOM,
          backgroundColor: AppColors.info,
          colorText: Colors.white,
          margin: const EdgeInsets.all(16),
        );
        return true;
      }
      return false;
    } catch (e) {
      AppLogger.error('Failed to archive project', error: e);
      return false;
    }
  }

  /// Restore a project
  Future<bool> restoreProject(int id) async {
    try {
      final success = await _projectService.restoreProject(id);

      if (success) {
        projects.removeWhere((p) => p.id == id);

        Get.snackbar(
          'Restored',
          'Project has been restored',
          snackPosition: SnackPosition.BOTTOM,
          backgroundColor: AppColors.success,
          colorText: Colors.white,
          margin: const EdgeInsets.all(16),
        );
        return true;
      }
      return false;
    } catch (e) {
      AppLogger.error('Failed to restore project', error: e);
      return false;
    }
  }

  /// Delete a project (Hard Delete)
  Future<bool> deleteProject(int id) async {
    try {
      final success = await _projectService.deleteProject(id);

      if (success) {
        projects.removeWhere((p) => p.id == id);

        Get.snackbar(
          'Deleted',
          'Project has been permanently deleted',
          snackPosition: SnackPosition.BOTTOM,
          backgroundColor: AppColors.textSecondary,
          colorText: Colors.white,
          margin: const EdgeInsets.all(16),
        );
        return true;
      }
      return false;
    } catch (e) {
      AppLogger.error('Failed to delete project', error: e);
      return false;
    }
  }

  /// Confirm and archive project
  Future<void> confirmArchiveProject(ProjectModel project) async {
    final result = await Get.dialog<bool>(
      AlertDialog(
        title: const Text('Archive Project'),
        content: Text(
            'Are you sure you want to archive "${project.name}"?\nIt will be hidden from the main list.'),
        actions: [
          TextButton(
            onPressed: () => Get.back(result: false),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () => Get.back(result: true),
            style: ElevatedButton.styleFrom(
              backgroundColor: AppColors.info,
            ),
            child: const Text('Archive'),
          ),
        ],
      ),
    );

    if (result == true) {
      await archiveProject(project.id);
    }
  }

  /// Confirm and restore project
  Future<void> confirmRestoreProject(ProjectModel project) async {
    final result = await Get.dialog<bool>(
      AlertDialog(
        title: const Text('Restore Project'),
        content: Text('Restore "${project.name}" to active projects?'),
        actions: [
          TextButton(
            onPressed: () => Get.back(result: false),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () => Get.back(result: true),
            style: ElevatedButton.styleFrom(
              backgroundColor: AppColors.success,
            ),
            child: const Text('Restore'),
          ),
        ],
      ),
    );

    if (result == true) {
      await restoreProject(project.id);
    }
  }

  /// Confirm and delete project
  Future<void> confirmDeleteProject(ProjectModel project) async {
    final result = await Get.dialog<bool>(
      AlertDialog(
        title: const Text('Delete Project Permanently'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Are you sure you want to delete "${project.name}"?'),
            SizedBox(height: 8),
            Text(
              'This action cannot be undone. All files, deployments, and databases associated with this project will be destroyed.',
              style: TextStyle(
                  color: AppColors.error, fontWeight: FontWeight.bold),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Get.back(result: false),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () => Get.back(result: true),
            style: ElevatedButton.styleFrom(
              backgroundColor: AppColors.error,
            ),
            child: const Text('Delete Permanently'),
          ),
        ],
      ),
    );

    if (result == true) {
      await deleteProject(project.id);
    }
  }

  /// Navigate to editor
  void openEditor(ProjectModel project) {
    if (project.status == 'archived') {
      confirmRestoreProject(project);
      return;
    }
    selectedProject.value = project;
    SharedPrefs.setLastProjectId(project.id);
    Get.toNamed(AppRoutes.editor.replaceFirst(':id', project.id.toString()));
  }

  /// Refresh projects
  Future<void> refresh() async {
    await loadProjects();
  }
}
