/// Auth controller with GetX
library;

import 'package:flutter/material.dart';
import 'package:get/get.dart';

import '../../../config/env.dart';
import '../../../config/routes.dart';
import '../../../core/constants/app_colors.dart';
import '../../../core/storage/shared_prefs.dart';
import '../../../core/utils/logger.dart';
import '../models/user_model.dart';
import '../services/auth_service.dart';
import '../widgets/github_auth_webview.dart';

/// Authentication controller managing user auth state
class AuthController extends GetxController {
  final AuthService _authService = AuthService();

  // State
  final Rx<UserModel?> currentUser = Rx<UserModel?>(null);
  final isLoading = false.obs;
  final isLoggedIn = false.obs;
  final isNewUser = false.obs;
  final errorMessage = RxnString();

  // Flow state management
  final showOnboardingForm = false.obs;
  final isAnimatingNewUser = false.obs;
  final isAnimatingExistingUser = false.obs;

  // Animation timing constants
  static const Duration _newUserAnimationDuration = Duration(seconds: 7);
  static const Duration _existingUserAnimationDuration = Duration(seconds: 9);

  // Reset key to force widget rebuilds (incremented on each reset)
  final resetKey = 0.obs;

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

        if (result != null &&
            result.containsKey('code') &&
            result.containsKey('state')) {
          final code = result['code']!;
          final state = result['state']!;
          await handleOAuthCallback(code, state);
        } else {
          // User closed the WebView without completing login
          AppLogger.info('User cancelled GitHub login');
          isLoading.value = false;
        }
      } else {
        errorMessage.value = 'Failed to get login URL';
        isLoading.value = false;
      }
    } catch (e) {
      AppLogger.error('GitHub login failed', error: e);
      errorMessage.value = 'Login failed. Please try again.';
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
        isNewUser.value = tokenResponse.isNewUser;
        isLoggedIn.value = true;

        // Initiate appropriate flow based on user type
        if (isNewUser.value) {
          await initiateNewUserFlow();
        } else {
          await initiateExistingUserFlow();
        }
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

  /// Initiate new user onboarding flow
  /// Shows welcome animations, then displays onboarding form
  Future<void> initiateNewUserFlow() async {
    AppLogger.info('Initiating new user flow');
    isAnimatingNewUser.value = true;
    showOnboardingForm.value = false;

    // Wait for welcome and configuration animations (first 2 screens)
    // Welcome (800ms + 2000ms + 600ms) + Configuring (800ms + 2000ms + 600ms) = 6.8s
    await Future.delayed(const Duration(milliseconds: 6800));

    // Show onboarding form
    isAnimatingNewUser.value = false;
    showOnboardingForm.value = true;

    AppLogger.info('Onboarding form displayed');
  }

  /// Initiate existing user flow
  /// Shows welcome back animations, then navigates to projects
  Future<void> initiateExistingUserFlow() async {
    AppLogger.info('Initiating existing user flow');
    isAnimatingExistingUser.value = true;

    // Wait for all welcome back animations to complete (9 seconds)
    await Future.delayed(_existingUserAnimationDuration);

    // Navigate to projects
    isAnimatingExistingUser.value = false;
    Get.offAllNamed(AppRoutes.layout);

    // Show welcome back message
    _showSnackbar(
      'Welcome Back!',
      'Logged in as ${currentUser.value?.displayName ?? "User"}',
      backgroundColor: AppColors.success,
    );

    AppLogger.info('Navigated to projects screen');
  }

  /// Complete onboarding form and navigate to projects
  /// Called when new user submits their onboarding information
  Future<void> completeOnboarding({
    required String displayName,
    Map<String, dynamic>? preferences,
  }) async {
    try {
      AppLogger.info('Completing onboarding for new user');

      // TODO: Send onboarding data to backend
      // await _authService.updateUserProfile(displayName, preferences);

      // Update local user data
      if (currentUser.value != null) {
        // Update the current user with new display name
        // currentUser.value = currentUser.value!.copyWith(displayName: displayName);
      }

      // Navigate to projects
      showOnboardingForm.value = false;
      Get.offAllNamed(AppRoutes.layout);

      // Show success message
      _showSnackbar(
        'Welcome To Codi!',
        'Let\'s build something amazing, $displayName!',
        backgroundColor: AppColors.success,
      );

      AppLogger.info('Onboarding completed successfully');
    } catch (e) {
      AppLogger.error('Failed to complete onboarding', error: e);
      errorMessage.value = 'Failed to save profile. Please try again.';
    }
  }

  /// Whether the user is existing (already had an account)
  bool get isExistingUser => isLoggedIn.value && !isNewUser.value;

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

    Get.offAllNamed(AppRoutes.layout);
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
