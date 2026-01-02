/// Commit panel controller for Git operations
library;

import 'package:flutter/material.dart';
import 'package:get/get.dart';

import '../../../core/utils/logger.dart';
import '../models/file_node.dart';
import '../services/editor_service.dart';
import 'editor_controller.dart';
import 'file_tree_controller.dart';

/// Controller for managing commit panel state and Git operations
class CommitPanelController extends GetxController {
  final EditorService _editorService = EditorService();

  // State
  final isExpanded = false.obs;
  final modifiedFiles = <FileNode>[].obs;
  final selectedFiles = <String>{}.obs;
  final commitMessage = ''.obs;
  final currentBranch = 'main'.obs;
  final branches = <String>[].obs;
  final isCommitting = false.obs;
  final createNewBranch = false.obs;
  final newBranchName = ''.obs;

  final messageController = TextEditingController();
  final branchNameController = TextEditingController();

  @override
  void onInit() {
    super.onInit();
    loadBranches();
  }

  /// Load branches from API
  Future<void> loadBranches() async {
    try {
      final editorController = Get.find<EditorController>();
      final projectId = editorController.currentProject.value?.id;
      if (projectId == null) return;

      final response = await _editorService.listBranches(projectId);

      if (response != null && response['branches'] != null) {
        branches.value = (response['branches'] as List)
            .map((b) => b['name'] as String)
            .toList();

        final defaultBranch = response['default_branch'] as String?;
        if (defaultBranch != null) {
          currentBranch.value = defaultBranch;
        }
      }
    } catch (e) {
      AppLogger.error('Failed to load branches', error: e);
    }
  }

  /// Load modified files from file tree
  void loadModifiedFiles() {
    if (Get.isRegistered<FileTreeController>()) {
      final fileTreeController = Get.find<FileTreeController>();
      modifiedFiles.value = fileTreeController.findModifiedFiles();

      // Select all by default
      selectedFiles.assignAll(modifiedFiles.map((f) => f.path).toSet());
    }
  }

  /// Toggle file selection
  void toggleFileSelection(String path) {
    if (selectedFiles.contains(path)) {
      selectedFiles.remove(path);
    } else {
      selectedFiles.add(path);
    }
  }

  /// Select all files
  void selectAll() {
    selectedFiles.assignAll(modifiedFiles.map((f) => f.path).toSet());
  }

  /// Deselect all files
  void deselectAll() {
    selectedFiles.clear();
  }

  /// Commit selected files
  Future<void> commit() async {
    if (selectedFiles.isEmpty) {
      Get.snackbar(
        'No Files Selected',
        'Please select at least one file to commit',
        snackPosition: SnackPosition.BOTTOM,
        backgroundColor: const Color(0xFFF59E0B),
        colorText: Colors.white,
      );
      return;
    }

    if (commitMessage.value.isEmpty) {
      Get.snackbar(
        'Commit Message Required',
        'Please enter a commit message',
        snackPosition: SnackPosition.BOTTOM,
        backgroundColor: const Color(0xFFF59E0B),
        colorText: Colors.white,
      );
      return;
    }

    try {
      isCommitting.value = true;

      final editorController = Get.find<EditorController>();
      final projectId = editorController.currentProject.value?.id;
      if (projectId == null) return;

      // Get file contents for selected files
      final List<Map<String, dynamic>> files = [];
      for (var path in selectedFiles) {
        final file = modifiedFiles.firstWhere((f) => f.path == path);
        final content = await _editorService.readFile(projectId, path);

        if (content != null) {
          files.add({
            'path': path,
            'content': content['content'],
            'sha': file.sha,
          });
        }
      }

      final branchName =
          createNewBranch.value ? newBranchName.value : currentBranch.value;

      final response = await _editorService.commitMultipleFiles(
        projectId,
        files,
        commitMessage.value,
        branchName,
        createNewBranch: createNewBranch.value,
        baseBranch: currentBranch.value,
      );

      if (response != null && response['success'] == true) {
        Get.snackbar(
          '✅ Committed',
          'Successfully committed ${selectedFiles.length} file(s)',
          duration: const Duration(seconds: 3),
          snackPosition: SnackPosition.BOTTOM,
          backgroundColor: const Color(0xFF10B981),
          colorText: Colors.white,
        );

        // Reset state
        messageController.clear();
        branchNameController.clear();
        commitMessage.value = '';
        newBranchName.value = '';
        createNewBranch.value = false;
        selectedFiles.clear();

        // Refresh file tree
        if (Get.isRegistered<FileTreeController>()) {
          await Get.find<FileTreeController>().loadFileTree();
        }
        loadModifiedFiles();

        // Collapse panel
        isExpanded.value = false;
      }
    } catch (e) {
      AppLogger.error('Failed to commit', error: e);
      Get.snackbar(
        'Commit Failed',
        'Failed to commit changes: $e',
        snackPosition: SnackPosition.BOTTOM,
        backgroundColor: const Color(0xFFEF4444),
        colorText: Colors.white,
      );
    } finally {
      isCommitting.value = false;
    }
  }

  /// Create a new branch
  Future<void> createBranch(String branchName) async {
    try {
      final editorController = Get.find<EditorController>();
      final projectId = editorController.currentProject.value?.id;
      if (projectId == null) return;

      final response = await _editorService.createBranch(
        projectId,
        branchName,
        currentBranch.value,
      );

      if (response != null && response['success'] == true) {
        await loadBranches();
        currentBranch.value = branchName;

        Get.snackbar(
          'Branch Created',
          'Successfully created branch: $branchName',
          snackPosition: SnackPosition.BOTTOM,
          backgroundColor: const Color(0xFF10B981),
          colorText: Colors.white,
        );
      }
    } catch (e) {
      AppLogger.error('Failed to create branch', error: e);
      Get.snackbar(
        'Error',
        'Failed to create branch: $e',
        snackPosition: SnackPosition.BOTTOM,
        backgroundColor: const Color(0xFFEF4444),
        colorText: Colors.white,
      );
    }
  }

  @override
  void onClose() {
    messageController.dispose();
    branchNameController.dispose();
    super.onClose();
  }
}
