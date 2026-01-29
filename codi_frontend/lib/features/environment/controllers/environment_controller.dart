import 'package:flutter/material.dart';
import 'package:get/get.dart';

import '../models/environment_variable.dart';
import '../services/environment_service.dart';

class EnvironmentController extends GetxController {
  final EnvironmentService _service = Get.find<EnvironmentService>();

  final RxList<EnvironmentVariable> variables = <EnvironmentVariable>[].obs;
  final Rxn<String> selectedContext = Rxn<String>();
  final isLoading = false.obs;
  final Rxn<String> error = Rxn<String>();

  int? projectId;

  @override
  void onInit() {
    super.onInit();
    projectId = int.tryParse(Get.parameters['id'] ?? '');
    if (projectId != null) {
      loadVariables();
    }
  }

  /// Load environment variables
  Future<void> loadVariables() async {
    if (projectId == null) return;

    isLoading.value = true;
    error.value = null;

    try {
      final result = await _service.listVariables(
        projectId!,
        context: selectedContext.value,
      );
      variables.value = result;
    } catch (e) {
      error.value = e.toString();
    } finally {
      isLoading.value = false;
    }
  }

  /// Set context filter
  void setContext(String? context) {
    selectedContext.value = context;
    loadVariables();
  }

  /// Create a new variable
  Future<void> createVariable(EnvironmentVariableCreate variable) async {
    if (projectId == null) return;

    try {
      await _service.createVariable(projectId!, variable);
      await loadVariables();
      Get.snackbar(
        'Success',
        'Created ${variable.key}',
        snackPosition: SnackPosition.BOTTOM,
      );
    } catch (e) {
      Get.snackbar(
        'Error',
        'Failed to create variable: $e',
        snackPosition: SnackPosition.BOTTOM,
        backgroundColor: Get.theme.colorScheme.error,
        colorText: Get.theme.colorScheme.onError,
      );
    }
  }

  /// Update an existing variable
  Future<void> updateVariable(
    int variableId,
    EnvironmentVariableUpdate update,
  ) async {
    if (projectId == null) return;

    try {
      await _service.updateVariable(projectId!, variableId, update);
      await loadVariables();
      Get.snackbar(
        'Success',
        'Variable updated',
        snackPosition: SnackPosition.BOTTOM,
      );
    } catch (e) {
      Get.snackbar(
        'Error',
        'Failed to update variable: $e',
        snackPosition: SnackPosition.BOTTOM,
        backgroundColor: Get.theme.colorScheme.error,
        colorText: Get.theme.colorScheme.onError,
      );
    }
  }

  /// Delete a variable
  Future<void> deleteVariable(int variableId, String key) async {
    if (projectId == null) return;

    // Confirm deletion
    final confirm = await Get.dialog<bool>(
      AlertDialog(
        title: const Text('Delete Variable'),
        content: Text('Are you sure you want to delete $key?'),
        actions: [
          TextButton(
            onPressed: () => Get.back(result: false),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Get.back(result: true),
            style: TextButton.styleFrom(
                foregroundColor: Get.theme.colorScheme.error),
            child: const Text('Delete'),
          ),
        ],
      ),
    );

    if (confirm != true) return;

    try {
      await _service.deleteVariable(projectId!, variableId);
      await loadVariables();
      Get.snackbar(
        'Success',
        'Deleted $key',
        snackPosition: SnackPosition.BOTTOM,
      );
    } catch (e) {
      Get.snackbar(
        'Error',
        'Failed to delete variable: $e',
        snackPosition: SnackPosition.BOTTOM,
        backgroundColor: Get.theme.colorScheme.error,
        colorText: Get.theme.colorScheme.onError,
      );
    }
  }

  /// Sync variables to .env file
  Future<void> syncToFile() async {
    if (projectId == null) return;

    try {
      final result = await _service.syncToFile(
        projectId!,
        context: selectedContext.value,
        includeSecrets: true,
      );

      Get.snackbar(
        'Success',
        'Synced ${result['synced_count']} variables to ${result['file_path']}',
        snackPosition: SnackPosition.BOTTOM,
      );
    } catch (e) {
      Get.snackbar(
        'Error',
        'Failed to sync: $e',
        snackPosition: SnackPosition.BOTTOM,
        backgroundColor: Get.theme.colorScheme.error,
        colorText: Get.theme.colorScheme.onError,
      );
    }
  }
}
