import 'package:get/get.dart';

import '../../../core/api/api_service.dart';
import '../../../core/utils/logger.dart';
import 'editor_controller.dart';
import 'file_tree_controller.dart';

/// Controller for Git branch management
class BranchController extends GetxController {
  late final EditorController _editorController;
  late final FileTreeController _fileTreeController;
  final ApiService _apiService = Get.find<ApiService>();

  // State
  final branches = <String>[].obs;
  final currentBranch = 'main'.obs;
  final isLoading = false.obs;
  final error = RxnString();

  // Selected branch for preview
  final previewBranch = RxnString();

  @override
  void onInit() {
    super.onInit();
    _editorController = Get.find<EditorController>();
    _fileTreeController = Get.find<FileTreeController>();

    // Load branches when project changes
    ever(_editorController.currentProject, (project) {
      if (project != null) {
        loadBranches();
      }
    });

    // Initial load
    if (_editorController.currentProject.value != null) {
      loadBranches();
    }
  }

  /// Load branches from API
  Future<void> loadBranches() async {
    final projectId = _editorController.currentProject.value?.id;
    if (projectId == null) return;

    try {
      isLoading.value = true;
      error.value = null;

      final response = await _apiService.get('/projects/$projectId/branches');
      
      if (response.data != null) {
        final data = response.data as Map<String, dynamic>;
        branches.value = List<String>.from(data['branches'] ?? ['main']);
        currentBranch.value = data['current_branch'] ?? 'main';
      }
    } catch (e) {
      AppLogger.error('Failed to load branches', error: e);
      error.value = 'Failed to load branches';
      // Default to main if API fails
      branches.value = ['main'];
    } finally {
      isLoading.value = false;
    }
  }

  /// Switch to a different branch
  Future<bool> switchBranch(String branch) async {
    final projectId = _editorController.currentProject.value?.id;
    if (projectId == null) return false;

    try {
      isLoading.value = true;
      error.value = null;

      final response = await _apiService.post(
        '/projects/$projectId/branches/checkout',
        queryParameters: {'branch': branch},
      );

      if (response.statusCode == 200) {
        currentBranch.value = branch;
        
        // Refresh file tree for new branch
        _fileTreeController.refreshFileTree();
        
        AppLogger.info('Switched to branch: $branch');
        return true;
      }
    } catch (e) {
      AppLogger.error('Failed to switch branch', error: e);
      error.value = 'Failed to switch branch';
    } finally {
      isLoading.value = false;
    }
    return false;
  }

  /// Create a new branch
  Future<bool> createBranch(String branchName, {String baseRef = 'HEAD'}) async {
    final projectId = _editorController.currentProject.value?.id;
    if (projectId == null) return false;

    try {
      isLoading.value = true;
      error.value = null;

      final response = await _apiService.post(
        '/projects/$projectId/branches',
        data: {
          'branch_name': branchName,
          'base_ref': baseRef,
        },
      );

      if (response.statusCode == 200) {
        // Reload branches to include the new one
        await loadBranches();
        AppLogger.info('Created branch: $branchName');
        return true;
      }
    } catch (e) {
      AppLogger.error('Failed to create branch', error: e);
      error.value = 'Failed to create branch';
    } finally {
      isLoading.value = false;
    }
    return false;
  }

  /// Create preview for a specific branch
  Future<String?> createPreviewDeployment(String branch) async {
    final projectId = _editorController.currentProject.value?.id;
    if (projectId == null) return null;

    try {
      isLoading.value = true;
      
      final response = await _apiService.post(
        '/deployments',
        data: {
          'project_id': projectId,
          'is_preview': true,
          'branch': branch,
        },
      );

      if (response.statusCode == 200) {
        final data = response.data as Map<String, dynamic>;
        final url = data['url'] as String?;
        previewBranch.value = branch;
        return url;
      }
    } catch (e) {
      AppLogger.error('Failed to create preview deployment', error: e);
      error.value = 'Failed to create preview';
    } finally {
      isLoading.value = false;
    }
    return null;
  }
}
