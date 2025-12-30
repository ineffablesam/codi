/// Auth controller with GetX
library;

import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../../config/routes.dart';
import '../../../core/constants/app_colors.dart';
import '../../../core/storage/shared_prefs.dart';
import '../../../core/utils/logger.dart';
import '../models/user_model.dart';
import '../services/auth_service.dart';
import '../widgets/github_auth_webview.dart';
import '../../../config/env.dart';

/// Authentication controller managing user auth state
class AuthController extends GetxController {
  final AuthService _authService = AuthService();

  // State
  final Rx<UserModel?> currentUser = Rx<UserModel?>(null);
  final isLoading = false.obs;
  final isLoggedIn = false.obs;
  final errorMessage = RxnString();

  @override
  void onInit() {
    super.onInit();
    _checkAuthState();
  }

  /// Check if user is already logged in
  Future<void> _checkAuthState() async {
    final token = SharedPrefs.getToken();
    if (token != null && token.isNotEmpty) {
      isLoggedIn.value = true;
      await _loadCurrentUser();
    }
  }

  /// Load current user from API
  Future<void> _loadCurrentUser() async {
    try {
      final user = await _authService.getCurrentUser();
      if (user != null) {
        currentUser.value = user;
        isLoggedIn.value = true;
      } else {
        // Token is invalid
        await _handleInvalidToken();
      }
    } catch (e) {
      AppLogger.error('Failed to load user', error: e);
      await _handleInvalidToken();
    }
  }

  Future<void> _handleInvalidToken() async {
    await SharedPrefs.clearUserSession();
    isLoggedIn.value = false;
    currentUser.value = null;
  }

  /// Initiate GitHub OAuth login
  Future<void> loginWithGitHub() async {
    isLoading.value = true;
    errorMessage.value = null;

    try {
      final url = await _authService.getGitHubOAuthUrl();
      if (url != null) {
        // Show WebView for authentication
        final result = await Get.to<Map<String, String>?>(
          () => GitHubAuthWebView(
            authUrl: url,
            callbackUrl: Environment.githubRedirectUri,
          ),
          fullscreenDialog: true,
        );

        if (result != null && result.containsKey('code') && result.containsKey('state')) {
          final code = result['code']!;
          final state = result['state']!;
          await handleOAuthCallback(code, state);
        } else {
          // User closed the WebView without completing login
          AppLogger.info('User cancelled GitHub login');
        }
      } else {
        errorMessage.value = 'Failed to get login URL';
      }
    } catch (e) {
      AppLogger.error('GitHub login failed', error: e);
      errorMessage.value = 'Login failed. Please try again.';
    } finally {
      isLoading.value = false;
    }
  }

  /// Handle OAuth callback (called after user returns from browser)
  Future<void> handleOAuthCallback(String code, String state) async {
    isLoading.value = true;
    errorMessage.value = null;

    try {
      final tokenResponse =
          await _authService.exchangeCodeForToken(code, state);

      if (tokenResponse != null) {
        // Save session
        await SharedPrefs.saveUserSession(
          token: tokenResponse.accessToken,
          userId: tokenResponse.user.id,
          username: tokenResponse.user.githubUsername,
          avatarUrl: tokenResponse.user.githubAvatarUrl,
        );

        currentUser.value = tokenResponse.user;
        isLoggedIn.value = true;

        // Navigate to projects
        Get.offAllNamed(AppRoutes.projects);

        _showSnackbar(
          'Welcome!',
          'Logged in as ${tokenResponse.user.displayName}',
          backgroundColor: AppColors.success,
        );
      } else {
        errorMessage.value = 'Authentication failed';
      }
    } catch (e) {
      AppLogger.error('OAuth callback failed', error: e);
      errorMessage.value = 'Authentication failed. Please try again.';
    } finally {
      isLoading.value = false;
    }
  }

  /// Complete login with token (for testing/dev)
  Future<void> completeLoginWithToken(String token, UserModel user) async {
    await SharedPrefs.saveUserSession(
      token: token,
      userId: user.id,
      username: user.githubUsername,
      avatarUrl: user.githubAvatarUrl,
    );

    currentUser.value = user;
    isLoggedIn.value = true;

    Get.offAllNamed(AppRoutes.projects);
  }

  /// Logout
  Future<void> logout() async {
    try {
      await _authService.logout();
    } catch (e) {
      AppLogger.warning('Logout API call failed', error: e);
    }

    await SharedPrefs.clearUserSession();
    currentUser.value = null;
    isLoggedIn.value = false;

    Get.offAllNamed(AppRoutes.login);
  }

  /// Confirm logout with dialog
  Future<void> confirmLogout() async {
    final result = await Get.dialog<bool>(
      AlertDialog(
        title: const Text('Log Out'),
        content: const Text('Are you sure you want to log out?'),
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
            child: const Text('Log Out'),
          ),
        ],
      ),
    );

    if (result == true) {
      await logout();
    }
  }

  void _showSnackbar(String title, String message, {Color? backgroundColor}) {
    Get.snackbar(
      title,
      message,
      duration: const Duration(seconds: 3),
      snackPosition: SnackPosition.BOTTOM,
      backgroundColor: backgroundColor ?? AppColors.primary,
      colorText: Colors.white,
      margin: const EdgeInsets.all(16),
    );
  }
}
