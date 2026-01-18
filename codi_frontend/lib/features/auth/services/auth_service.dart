/// Auth service for API calls
library;

import 'package:flutter/cupertino.dart';

import '../../../core/api/api_client.dart';
import '../../../core/api/dio_client.dart';
import '../../../core/constants/api_endpoints.dart';
import '../models/user_model.dart';

/// Authentication service
class AuthService {
  /// Get GitHub OAuth URL
  Future<String?> getGitHubOAuthUrl() async {
    final response = await ApiClient.get<Map<String, dynamic>>(
      ApiEndpoints.authGitHub,
    );
    debugPrint('GitHub OAuth URL response: ${response.data.toString()}');
    if (response.success && response.data != null) {
      return response.data!['url'] as String?;
    }
    return null;
  }

  /// Exchange GitHub code for token
  Future<TokenResponse?> exchangeCodeForToken(String code, String state) async {
    try {
      final response = await DioClient.dio.get(
        ApiEndpoints.authGitHubCallback,
        queryParameters: {
          'code': code,
          'state': state,
        },
      );

      return TokenResponse.fromJson(response.data as Map<String, dynamic>);
    } catch (e) {
      return null;
    }
  }

  /// Get current user
  Future<UserModel?> getCurrentUser() async {
    final response = await ApiClient.get<Map<String, dynamic>>(
      ApiEndpoints.authMe,
    );

    if (response.success && response.data != null) {
      return UserModel.fromJson(response.data!);
    }
    return null;
  }

  /// Logout
  Future<bool> logout() async {
    final response = await ApiClient.post<Map<String, dynamic>>(
      ApiEndpoints.authLogout,
    );
    return response.success;
  }

  /// Complete onboarding
  Future<bool> completeOnboarding({
    required String name,
    required String whatBringsYou,
    required String codingExperience,
  }) async {
    final response = await ApiClient.patch<Map<String, dynamic>>(
      '${ApiEndpoints.authMe}/onboarding',
      data: {
        'name': name,
        'what_brings_you': whatBringsYou,
        'coding_experience': codingExperience,
      },
    );
    return response.success;
  }
}
