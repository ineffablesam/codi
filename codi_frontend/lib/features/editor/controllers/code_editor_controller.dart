/// Code editor controller with flutter_code_editor
library;

import 'package:flutter/material.dart';
import 'package:flutter_code_editor/flutter_code_editor.dart';
import 'package:get/get.dart';
import 'package:highlight/languages/dart.dart';
import 'package:highlight/languages/json.dart';
import 'package:highlight/languages/yaml.dart';
import 'package:highlight/languages/markdown.dart';
import 'package:highlight/languages/xml.dart';
import 'package:highlight/languages/javascript.dart';
import 'package:highlight/languages/python.dart';
import 'package:highlight/languages/kotlin.dart';
import 'package:highlight/languages/swift.dart';
import 'package:highlight/languages/css.dart';
import 'package:highlight/highlight.dart' as hl;

import '../../../core/utils/logger.dart';
import '../models/file_node.dart';
import '../services/editor_service.dart';
import 'editor_controller.dart';
import 'file_tree_controller.dart';

/// Controller for the code editor with syntax highlighting
class CodeEditorController extends GetxController {
  final EditorService _editorService = EditorService();

  late CodeController codeController;
  final currentFile = Rxn<FileNode>();
  final currentFileSha = RxnString();
  final isLoading = false.obs;
  final isSaving = false.obs;
  final hasUnsavedChanges = false.obs;
  final originalContent = ''.obs;

  @override
  void onInit() {
    super.onInit();
    codeController = CodeController(
      text: '',
      language: dart,
    );

    // Listen for content changes
    codeController.addListener(_onContentChanged);
  }

  void _onContentChanged() {
    if (currentFile.value != null) {
      hasUnsavedChanges.value = codeController.text != originalContent.value;
    }
  }

  /// Load file content into the editor
  Future<void> loadFile(FileNode file) async {
    try {
      isLoading.value = true;
      currentFile.value = file;

      final editorController = Get.find<EditorController>();
      final projectId = editorController.currentProject.value?.id;
      if (projectId == null) return;

      final response = await _editorService.readFile(projectId, file.path);

      if (response != null) {
        final content = response['content'] as String? ?? '';
        final sha = response['sha'] as String?;

        originalContent.value = content;
        currentFileSha.value = sha;

        // Update code controller with content and language
        codeController.removeListener(_onContentChanged);
        codeController = CodeController(
          text: content,
          language: _getLanguageFromExtension(file.name),
        );
        codeController.addListener(_onContentChanged);

        hasUnsavedChanges.value = false;
        AppLogger.info('Loaded file: ${file.path}');
      }
    } catch (e) {
      AppLogger.error('Failed to load file', error: e);
      Get.snackbar(
        'Error',
        'Failed to load file: $e',
        snackPosition: SnackPosition.BOTTOM,
        backgroundColor: const Color(0xFFEF4444),
        colorText: Colors.white,
      );
    } finally {
      isLoading.value = false;
    }
  }

  /// Save the current file
  Future<void> saveFile() async {
    if (currentFile.value == null || !hasUnsavedChanges.value) return;

    try {
      isSaving.value = true;

      final editorController = Get.find<EditorController>();
      final projectId = editorController.currentProject.value?.id;
      if (projectId == null) return;

      final response = await _editorService.updateFile(
        projectId,
        currentFile.value!.path,
        codeController.text,
        'Update ${currentFile.value!.name}',
        currentFileSha.value,
      );

      if (response != null && response['success'] == true) {
        originalContent.value = codeController.text;
        hasUnsavedChanges.value = false;

        // Update SHA
        currentFileSha.value = response['new_sha'] as String?;

        Get.snackbar(
          'Saved',
          'File saved successfully',
          duration: const Duration(seconds: 2),
          snackPosition: SnackPosition.BOTTOM,
          backgroundColor: const Color(0xFF10B981),
          colorText: Colors.white,
        );

        // Refresh file tree
        if (Get.isRegistered<FileTreeController>()) {
          Get.find<FileTreeController>().loadFileTree();
        }
      }
    } catch (e) {
      AppLogger.error('Failed to save file', error: e);
      Get.snackbar(
        'Error',
        'Failed to save file: $e',
        snackPosition: SnackPosition.BOTTOM,
        backgroundColor: const Color(0xFFEF4444),
        colorText: Colors.white,
      );
    } finally {
      isSaving.value = false;
    }
  }

  /// Get language mode from file extension
  hl.Mode _getLanguageFromExtension(String filename) {
    final ext = filename.split('.').last.toLowerCase();
    switch (ext) {
      case 'dart':
        return dart;
      case 'json':
        return json;
      case 'yaml':
      case 'yml':
        return yaml;
      case 'md':
        return markdown;
      case 'xml':
      case 'plist':
        return xml;
      case 'js':
      case 'jsx':
        return javascript;
      case 'py':
        return python;
      case 'kt':
        return kotlin;
      case 'swift':
        return swift;
      case 'css':
      case 'scss':
        return css;
      default:
        return dart; // Default to dart
    }
  }

  /// Get current content
  String get content => codeController.text;

  /// Clear the editor
  void clearEditor() {
    currentFile.value = null;
    currentFileSha.value = null;
    originalContent.value = '';
    hasUnsavedChanges.value = false;
    codeController.text = '';
  }

  @override
  void onClose() {
    codeController.dispose();
    super.onClose();
  }
}

