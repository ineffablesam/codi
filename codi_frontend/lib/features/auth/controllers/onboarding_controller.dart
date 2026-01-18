/// Onboarding controller for managing new user form state
library;

import 'package:flutter/material.dart';
import 'package:get/get.dart';

import '../../../core/utils/logger.dart';
import '../services/auth_service.dart';
import 'auth_controller.dart';

/// Controller for managing onboarding form state and validation
class OnboardingController extends GetxController {
  final AuthService _authService = AuthService();

  // Form controllers
  late TextEditingController nameController;

  // Form state
  final whatBringsYou = RxnString();
  final codingExperience = RxnString();
  final isSubmitting = false.obs;
  final errorMessage = RxnString();

  // What brings you options
  static const List<Map<String, String>> whatBringsYouOptions = [
    {'value': 'build_app', 'label': '📱 Build an app'},
    {'value': 'create_website', 'label': '🌐 Create a website'},
    {'value': 'learn_to_code', 'label': '📚 Learn to code'},
    {'value': 'just_exploring', 'label': '🎨 Just exploring'},
  ];

  // Coding experience options
  static const List<Map<String, String>> codingExperienceOptions = [
    {
      'value': 'never_coded',
      'label': '🌱 Never coded',
      'description': "I'm completely new to this"
    },
    {
      'value': 'still_learning',
      'label': '📚 Still learning',
      'description': "I've tried some tutorials"
    },
    {
      'value': 'can_code',
      'label': '🚀 I can code',
      'description': "I'm comfortable with coding"
    },
  ];

  @override
  void onInit() {
    super.onInit();
    nameController = TextEditingController();
    // Listen for name changes to update form validity
    nameController.addListener(_updateFormValidity);
    _initializeFromAuth();
  }

  /// Pre-populate name from auth if available
  void _initializeFromAuth() {
    final authController = Get.find<AuthController>();
    final user = authController.currentUser.value;
    if (user != null && user.name != null && user.name!.isNotEmpty) {
      nameController.text = user.name!;
    } else if (user != null && user.githubUsername.isNotEmpty) {
      // Fallback to GitHub username
      nameController.text = user.githubUsername;
    }
  }

  // Reactive form validity tracker
  final isFormValid = false.obs;

  /// Update form validity state
  void _updateFormValidity() {
    isFormValid.value = nameController.text.trim().isNotEmpty &&
        whatBringsYou.value != null &&
        codingExperience.value != null;
  }

  /// Set what brings you selection
  void setWhatBringsYou(String value) {
    whatBringsYou.value = value;
    _updateFormValidity();
  }

  /// Set coding experience selection
  void setCodingExperience(String value) {
    codingExperience.value = value;
    _updateFormValidity();
  }

  /// Submit onboarding data to backend
  Future<void> submitOnboarding() async {
    if (!isFormValid.value) {
      errorMessage.value = 'Please fill in all fields';
      return;
    }

    isSubmitting.value = true;
    errorMessage.value = null;

    try {
      final success = await _authService.completeOnboarding(
        name: nameController.text.trim(),
        whatBringsYou: whatBringsYou.value!,
        codingExperience: codingExperience.value!,
      );

      if (success) {
        AppLogger.info('Onboarding completed successfully');
        final authController = Get.find<AuthController>();
        await authController.completeOnboarding(
          displayName: nameController.text.trim(),
          preferences: {
            'what_brings_you': whatBringsYou.value,
            'coding_experience': codingExperience.value,
          },
        );
      } else {
        errorMessage.value = 'Failed to save profile. Please try again.';
      }
    } catch (e) {
      AppLogger.error('Onboarding submission failed', error: e);
      errorMessage.value = 'Something went wrong. Please try again.';
    } finally {
      isSubmitting.value = false;
    }
  }

  @override
  void onClose() {
    nameController.dispose();
    super.onClose();
  }
}
