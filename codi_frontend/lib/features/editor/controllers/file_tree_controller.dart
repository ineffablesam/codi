/// File tree controller for managing file hierarchy
library;

import 'package:flutter/material.dart';
import 'package:get/get.dart';

import '../../../core/utils/logger.dart';
import '../models/file_node.dart';
import '../services/editor_service.dart';
import 'code_editor_controller.dart';
import 'editor_controller.dart';

/// Controller for managing file tree state
class FileTreeController extends GetxController {
  final EditorService _editorService = EditorService();

  // State
  final fileTree = <FileNode>[].obs;
  final isLoading = false.obs;
  final selectedFile = Rxn<FileNode>();
  final searchQuery = ''.obs;
  final showHiddenFiles = false.obs;

  /// Get filtered tree based on search query
  List<FileNode> get filteredTree {
    if (searchQuery.value.isEmpty) {
      return fileTree;
    }
    return _filterNodes(fileTree, searchQuery.value);
  }

  @override
  void onInit() {
    super.onInit();
    loadFileTree();
  }

  /// Load file tree from API
  Future<void> loadFileTree() async {
    try {
      isLoading.value = true;

      final editorController = Get.find<EditorController>();
      final projectId = editorController.currentProject.value?.id;
      if (projectId == null) {
        AppLogger.warning('No project ID available for file tree');
        return;
      }

      final response = await _editorService.getFileTree(projectId);

      if (response != null && response['tree'] != null) {
        final treeList = (response['tree'] as List)
            .map((node) => FileNode.fromJson(node as Map<String, dynamic>))
            .toList();
        fileTree.value = treeList;
        AppLogger.info('Loaded file tree with ${treeList.length} root items');
      }
    } catch (e) {
      AppLogger.error('Failed to load file tree', error: e);
      Get.snackbar(
        'Error',
        'Failed to load file tree: $e',
        snackPosition: SnackPosition.BOTTOM,
        backgroundColor: const Color(0xFFEF4444),
        colorText: Colors.white,
      );
    } finally {
      isLoading.value = false;
    }
  }

  /// Refresh file tree
  Future<void> refreshFileTree() async {
    await loadFileTree();
    Get.snackbar(
      'Refreshed',
      'File tree updated',
      duration: const Duration(seconds: 2),
      snackPosition: SnackPosition.BOTTOM,
    );
  }

  /// Toggle node expansion
  void toggleNode(FileNode node) {
    node.isExpanded.toggle();
  }

  /// Expand all directories
  void expandAll() {
    _expandRecursive(fileTree);
  }

  /// Collapse all directories
  void collapseAll() {
    _collapseRecursive(fileTree);
  }

  void _expandRecursive(List<FileNode> nodes) {
    for (var node in nodes) {
      if (node.isDirectory) {
        node.isExpanded.value = true;
        _expandRecursive(node.children);
      }
    }
  }

  void _collapseRecursive(List<FileNode> nodes) {
    for (var node in nodes) {
      if (node.isDirectory) {
        node.isExpanded.value = false;
        _collapseRecursive(node.children);
      }
    }
  }

  /// Select a file for editing
  void selectFile(FileNode node) {
    if (node.isFile) {
      selectedFile.value = node;
      // Notify code editor to load file
      if (Get.isRegistered<CodeEditorController>()) {
        Get.find<CodeEditorController>().loadFile(node);
      }
    } else {
      toggleNode(node);
    }
  }

  /// Filter nodes by search query
  List<FileNode> _filterNodes(List<FileNode> nodes, String query) {
    final List<FileNode> filtered = [];
    final lowerQuery = query.toLowerCase();

    for (var node in nodes) {
      if (node.name.toLowerCase().contains(lowerQuery)) {
        filtered.add(node);
      } else if (node.isDirectory) {
        final filteredChildren = _filterNodes(node.children, query);
        if (filteredChildren.isNotEmpty) {
          filtered.add(FileNode(
            path: node.path,
            name: node.name,
            type: node.type,
            children: filteredChildren,
            expanded: true,
          ));
        }
      }
    }

    return filtered;
  }

  /// Find modified files in tree
  List<FileNode> findModifiedFiles() {
    return _findModifiedFilesRecursive(fileTree);
  }

  List<FileNode> _findModifiedFilesRecursive(List<FileNode> nodes) {
    final List<FileNode> modified = [];

    for (var node in nodes) {
      if (node.isFile && node.modified) {
        modified.add(node);
      } else if (node.isDirectory) {
        modified.addAll(_findModifiedFilesRecursive(node.children));
      }
    }

    return modified;
  }
}

