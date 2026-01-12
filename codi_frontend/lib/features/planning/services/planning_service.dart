/// Planning service for API communication
library;

import 'package:dio/dio.dart';

import '../../../core/api/dio_client.dart';
import '../models/implementation_plan_model.dart';

/// Service for managing implementation plans via API
class PlanningService {
  /// Create a new implementation plan
  Future<ImplementationPlan> createPlan({
    required String userRequest,
    required int projectId,
  }) async {
    try {
      final response = await DioClient.dio.post(
        '/plans',
        data: {
          'user_request': userRequest,
          'project_id': projectId,
        },
      );

      return ImplementationPlan.fromJson(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throw Exception(
        e.response?.data?['detail'] ?? 'Failed to create plan: ${e.message}',
      );
    }
  }

  /// Get a specific plan by ID
  Future<ImplementationPlan> getPlan(int planId) async {
    try {
      final response = await DioClient.dio.get('/plans/$planId');
      return ImplementationPlan.fromJson(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throw Exception(
        e.response?.data?['detail'] ?? 'Failed to get plan: ${e.message}',
      );
    }
  }

  /// Get all plans for a project
  Future<List<ImplementationPlan>> getProjectPlans(int projectId) async {
    try {
      final response = await DioClient.dio.get('/plans/project/$projectId');
      final List<dynamic> data = response.data as List<dynamic>;
      return data
          .map((json) =>
              ImplementationPlan.fromJson(json as Map<String, dynamic>))
          .toList();
    } on DioException catch (e) {
      throw Exception(
        e.response?.data?['detail'] ?? 'Failed to get plans: ${e.message}',
      );
    }
  }

  /// Get tasks for a plan
  Future<List<PlanTask>> getTasks(int planId) async {
    try {
      final response = await DioClient.dio.get('/plans/$planId/tasks');
      final List<dynamic> data = response.data as List<dynamic>;
      return data
          .map((json) => PlanTask.fromJson(json as Map<String, dynamic>))
          .toList();
    } on DioException catch (e) {
      throw Exception(
        e.response?.data?['detail'] ?? 'Failed to get tasks: ${e.message}',
      );
    }
  }

  /// Approve a plan
  Future<ImplementationPlan> approvePlan({
    required int planId,
    String? comment,
  }) async {
    try {
      final response = await DioClient.dio.post(
        '/plans/$planId/approve',
        data: comment != null ? {'comment': comment} : {},
      );
      return ImplementationPlan.fromJson(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throw Exception(
        e.response?.data?['detail'] ?? 'Failed to approve plan: ${e.message}',
      );
    }
  }

  /// Reject a plan
  Future<ImplementationPlan> rejectPlan({
    required int planId,
    String? comment,
  }) async {
    try {
      final response = await DioClient.dio.post(
        '/plans/$planId/reject',
        data: comment != null ? {'comment': comment} : {},
      );
      return ImplementationPlan.fromJson(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throw Exception(
        e.response?.data?['detail'] ?? 'Failed to reject plan: ${e.message}',
      );
    }
  }

  /// Get markdown content for a plan
  Future<String> getPlanMarkdown(int planId) async {
    try {
      final response = await DioClient.dio.get('/plans/$planId/markdown');
      return response.data['markdown'] as String;
    } on DioException catch (e) {
      throw Exception(
        e.response?.data?['detail'] ?? 'Failed to get markdown: ${e.message}',
      );
    }
  }

  /// Get walkthrough content for a completed plan
  Future<String> getWalkthrough(int planId) async {
    try {
      final response = await DioClient.dio.get('/plans/$planId/walkthrough');
      return response.data['markdown'] as String;
    } on DioException catch (e) {
      throw Exception(
        e.response?.data?['detail'] ??
            'Failed to get walkthrough: ${e.message}',
      );
    }
  }

  /// Update task completion status
  Future<PlanTask> updateTask({
    required int planId,
    required int taskId,
    required bool completed,
  }) async {
    try {
      final response = await DioClient.dio.patch(
        '/plans/$planId/tasks/$taskId',
        data: {'completed': completed},
      );
      return PlanTask.fromJson(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throw Exception(
        e.response?.data?['detail'] ?? 'Failed to update task: ${e.message}',
      );
    }
  }
}
