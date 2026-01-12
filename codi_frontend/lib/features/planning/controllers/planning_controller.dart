/// Planning controller for managing implementation plans
library;

import 'dart:async';

import 'package:flutter/material.dart';
import 'package:get/get.dart';

import '../../../core/api/websocket_client.dart';
import '../../../core/constants/app_colors.dart';
import '../../../core/utils/logger.dart';
import '../models/implementation_plan_model.dart';
import '../services/planning_service.dart';

/// Controller for managing implementation plans with TODO tracking
class PlanningController extends GetxController {
  final PlanningService _planningService = PlanningService();
  WebSocketClient? _wsClient;

  // Observable state
  final currentPlan = Rxn<ImplementationPlan>();
  final tasks = <PlanTask>[].obs;
  final isLoadingPlan = false.obs;
  final isSubmitting = false.obs;
  final projectPlans = <ImplementationPlan>[].obs;

  // Stream subscription
  StreamSubscription<Map<String, dynamic>>? _wsSubscription;

  @override
  void onInit() {
    super.onInit();
    _setupWebSocketListeners();
  }

  void _setupWebSocketListeners() {
    try {
      _wsClient = Get.find<WebSocketClient>();
      _wsSubscription = _wsClient?.messageStream.listen(_handleMessage);
    } catch (e) {
      AppLogger.warning('WebSocketClient not registered, skipping listener setup');
    }
  }

  void _handleMessage(Map<String, dynamic> data) {
    final type = data['type'] as String?;
    if (type == null) return;

    switch (type) {
      case 'plan_ready':
        _handlePlanReady(data);
        break;
      case 'task_updated':
        _handleTaskUpdated(data);
        break;
      case 'walkthrough_ready':
        _handleWalkthroughReady(data);
        break;
      case 'plan_approved':
        _handlePlanApproved(data);
        break;
      case 'plan_rejected':
        _handlePlanRejected(data);
        break;
    }
  }

  /// Create a new implementation plan
  Future<void> createPlan(String userRequest, int projectId) async {
    try {
      isLoadingPlan.value = true;

      final plan = await _planningService.createPlan(
        userRequest: userRequest,
        projectId: projectId,
      );

      currentPlan.value = plan;
      tasks.value = plan.tasks;

      // Navigate to plan review screen
      Get.toNamed('/plan-review', arguments: {'planId': plan.id});
    } catch (e) {
      AppLogger.error('Failed to create plan', error: e);
      Get.snackbar(
        'Error',
        'Failed to create plan: $e',
        snackPosition: SnackPosition.BOTTOM,
        backgroundColor: AppColors.error,
        colorText: Colors.white,
      );
    } finally {
      isLoadingPlan.value = false;
    }
  }

  /// Load a plan by ID
  Future<void> loadPlan(int planId) async {
    try {
      isLoadingPlan.value = true;

      final plan = await _planningService.getPlan(planId);
      currentPlan.value = plan;
      tasks.value = plan.tasks;
    } catch (e) {
      AppLogger.error('Failed to load plan', error: e);
      Get.snackbar(
        'Error',
        'Failed to load plan: $e',
        snackPosition: SnackPosition.BOTTOM,
        backgroundColor: AppColors.error,
        colorText: Colors.white,
      );
    } finally {
      isLoadingPlan.value = false;
    }
  }

  /// Load all plans for a project
  Future<void> loadProjectPlans(int projectId) async {
    try {
      isLoadingPlan.value = true;

      final plans = await _planningService.getProjectPlans(projectId);
      projectPlans.value = plans;
    } catch (e) {
      AppLogger.error('Failed to load project plans', error: e);
    } finally {
      isLoadingPlan.value = false;
    }
  }

  /// Approve the current plan
  Future<void> approvePlan({String? comment}) async {
    if (currentPlan.value == null) return;

    try {
      isSubmitting.value = true;

      await _planningService.approvePlan(
        planId: currentPlan.value!.id,
        comment: comment,
      );

      Get.back(); // Close plan review screen

      Get.snackbar(
        '✅ Plan Approved',
        'Implementation has started!',
        snackPosition: SnackPosition.TOP,
        backgroundColor: AppColors.success,
        colorText: Colors.white,
        duration: const Duration(seconds: 3),
      );
    } catch (e) {
      AppLogger.error('Failed to approve plan', error: e);
      Get.snackbar(
        'Error',
        'Failed to approve plan: $e',
        snackPosition: SnackPosition.BOTTOM,
        backgroundColor: AppColors.error,
        colorText: Colors.white,
      );
    } finally {
      isSubmitting.value = false;
    }
  }

  /// Reject the current plan
  Future<void> rejectPlan({String? comment}) async {
    if (currentPlan.value == null) return;

    try {
      isSubmitting.value = true;

      await _planningService.rejectPlan(
        planId: currentPlan.value!.id,
        comment: comment,
      );

      Get.back(); // Close plan review screen

      Get.snackbar(
        'Plan Declined',
        comment ?? 'Feel free to request changes or a new plan.',
        snackPosition: SnackPosition.TOP,
        backgroundColor: AppColors.warning,
        colorText: Colors.white,
        duration: const Duration(seconds: 3),
      );

      currentPlan.value = null;
    } catch (e) {
      AppLogger.error('Failed to reject plan', error: e);
      Get.snackbar(
        'Error',
        'Failed to reject plan: $e',
        snackPosition: SnackPosition.BOTTOM,
        backgroundColor: AppColors.error,
        colorText: Colors.white,
      );
    } finally {
      isSubmitting.value = false;
    }
  }

  void _handlePlanReady(Map<String, dynamic> data) {
    final planId = data['plan_id'] as int?;
    final markdown = data['markdown_content'] as String?;

    if (planId == null) return;

    AppLogger.info('Plan ready: $planId');

    // Load full plan details
    loadPlan(planId);

    // Navigate to plan review screen
    Get.toNamed('/plan-review', arguments: {'planId': planId});
  }

  void _handleTaskUpdated(Map<String, dynamic> data) {
    final taskId = data['task_id'] as int?;
    final completed = data['completed'] as bool?;
    final progress = data['progress'] as num?;

    if (taskId == null || completed == null) return;

    // Update task in list
    final taskIndex = tasks.indexWhere((t) => t.id == taskId);
    if (taskIndex != -1) {
      tasks[taskIndex] = tasks[taskIndex].copyWith(
        completed: completed,
        completedAt: completed ? DateTime.now() : null,
      );
      tasks.refresh();
    }

    // Update plan progress
    if (currentPlan.value != null && progress != null) {
      final completedCount = completed
          ? currentPlan.value!.completedTasks + 1
          : currentPlan.value!.completedTasks - 1;

      currentPlan.value = currentPlan.value!.copyWith(
        completedTasks: completedCount,
        progress: progress.toDouble(),
      );
    }
  }

  void _handleWalkthroughReady(Map<String, dynamic> data) {
    final walkthrough = data['walkthrough_content'] as String?;
    final planId = data['plan_id'] as int?;

    if (walkthrough == null || planId == null) return;

    // Navigate to walkthrough screen
    Get.toNamed('/walkthrough', arguments: {
      'planId': planId,
      'content': walkthrough,
    });

    Get.snackbar(
      '🎉 Implementation Complete!',
      'View the walkthrough to see what was built',
      snackPosition: SnackPosition.TOP,
      backgroundColor: AppColors.success,
      colorText: Colors.white,
      duration: const Duration(seconds: 5),
    );
  }

  void _handlePlanApproved(Map<String, dynamic> data) {
    final planId = data['plan_id'] as int?;
    if (currentPlan.value?.id == planId) {
      currentPlan.value = currentPlan.value?.copyWith(
        status: 'approved',
        approvedAt: DateTime.now(),
      );
    }
  }

  void _handlePlanRejected(Map<String, dynamic> data) {
    final planId = data['plan_id'] as int?;
    if (currentPlan.value?.id == planId) {
      currentPlan.value = currentPlan.value?.copyWith(
        status: 'rejected',
        rejectedAt: DateTime.now(),
      );
    }
  }

  /// Get markdown content for current plan
  Future<String?> getPlanMarkdown() async {
    if (currentPlan.value == null) return null;

    try {
      return await _planningService.getPlanMarkdown(currentPlan.value!.id);
    } catch (e) {
      AppLogger.error('Failed to get markdown', error: e);
      return null;
    }
  }

  /// Get walkthrough for current plan
  Future<String?> getWalkthrough() async {
    if (currentPlan.value == null) return null;

    try {
      return await _planningService.getWalkthrough(currentPlan.value!.id);
    } catch (e) {
      AppLogger.error('Failed to get walkthrough', error: e);
      return null;
    }
  }

  @override
  void onClose() {
    _wsSubscription?.cancel();
    super.onClose();
  }
}
