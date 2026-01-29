/// Project creation wizard controller
library;

import 'package:flutter/cupertino.dart';
import 'package:get/get.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../../../core/constants/app_colors.dart';
import '../services/backend_connection_service.dart';

/// Wizard step enum
enum WizardStep { framework, backend, deployment, details }

/// Project creation wizard controller
class ProjectWizardController extends GetxController {
  // Form Key
  final formKey = GlobalKey<FormState>();

  // Current step
  final currentStep = WizardStep.framework.obs;
  final lastStep = WizardStep.framework.obs;

  // Selections
  final selectedFramework = 'flutter'.obs;
  final selectedBackend = RxnString();
  final selectedDeployment = 'github_pages'.obs;

  // Project details
  final projectName = ''.obs;
  final projectDescription = ''.obs;
  final isPrivate = false.obs;
  final appIdea = ''.obs;

  // Animation state
  final isAnimating = false.obs;

  // Text editing controllers
  late final TextEditingController nameController;
  late final TextEditingController descriptionController;
  late final TextEditingController appIdeaController;

  @override
  void onInit() {
    super.onInit();
    nameController = TextEditingController();
    descriptionController = TextEditingController();
    appIdeaController = TextEditingController();

    // Listen to changes and update observable values
    nameController.addListener(() => projectName.value = nameController.text);
    descriptionController.addListener(
        () => projectDescription.value = descriptionController.text);
    appIdeaController.addListener(() => appIdea.value = appIdeaController.text);
  }

  @override
  void onClose() {
    nameController.dispose();
    descriptionController.dispose();
    appIdeaController.dispose();
    super.onClose();
  }

  /// Framework options
  static const List<FrameworkOption> frameworks = [
    FrameworkOption(
      id: 'flutter',
      name: 'Flutter',
      description: 'Cross-platform mobile & web apps',
      icon: LucideIcons.tabletSmartphone,
      gradient: [Color(0xFF02569B), Color(0xFF0175C2)],
      platforms: ['iOS', 'Android', 'Web'],
    ),
    FrameworkOption(
      id: 'react',
      name: 'React',
      description: 'Modern web applications',
      icon: LucideIcons.code,
      gradient: [Color(0xFF61DAFB), Color(0xFF20232A)],
      platforms: ['Web'],
    ),
    FrameworkOption(
      id: 'nextjs',
      name: 'Next.js',
      description: 'Full-stack React framework',
      icon: LucideIcons.hexagon,
      gradient: [Color(0xFF61DAFB), Color(0xFF282C34)],
      platforms: ['Web', 'API'],
    ),
    FrameworkOption(
      id: 'react_native',
      name: 'React Native',
      description: 'Native mobile apps with React',
      icon: LucideIcons.smartphone,
      gradient: [Color(0xFF61DAFB), Color(0xFF282C34)],
      platforms: ['iOS', 'Android'],
    ),
  ];

  /// Backend options
  static const List<BackendOption> backends = [
    BackendOption(
      id: 'supabase',
      name: 'Supabase',
      description: 'Open source Firebase alternative',
      icon: LucideIcons.database,
      gradient: [Color(0xFF3ECF8E), Color(0xFF1C7C54)],
      features: ['Auth', 'Database', 'Storage', 'Realtime'],
    ),
    BackendOption(
      id: 'firebase',
      name: 'Firebase',
      description: 'Google\'s app platform',
      icon: LucideIcons.flame,
      gradient: [Color(0xFFFFCA28), Color(0xFFF57C00)],
      features: ['Auth', 'Firestore', 'Storage', 'Analytics'],
    ),
    BackendOption(
      id: 'serverpod',
      name: 'Serverpod',
      description: 'Auto-managed by Codi',
      icon: LucideIcons.server,
      gradient: [Color(0xFF0175C2), Color(0xFF02569B)],
      features: ['Type-safe API', 'ORM', 'Caching', 'Auth'],
    ),
  ];

  /// Deployment options
  static const List<DeploymentOption> deployments = [
    DeploymentOption(
      id: 'github_pages',
      name: 'GitHub Pages',
      description: 'Free static site hosting',
      icon: LucideIcons.github,
      gradient: [Color(0xFFFFFFFF), Color(0xFF9CA3AF)],
      features: ['Free', 'HTTPS', 'Custom domain'],
    ),
    DeploymentOption(
      id: 'vercel',
      name: 'Vercel',
      description: 'Edge-first deployment',
      icon: LucideIcons.triangle,
      gradient: [Color(0xFFFFFFFF), Color(0xFF6B7280)],
      features: ['Edge functions', 'Preview deploys', 'Analytics'],
    ),
    DeploymentOption(
      id: 'netlify',
      name: 'Netlify',
      description: 'Modern web hosting',
      icon: LucideIcons.cloud,
      gradient: [Color(0xFF00C7B7), Color(0xFF008C82)],
      features: ['Forms', 'Functions', 'Identity'],
    ),
  ];

  /// Get platform type based on framework
  String get platformType {
    switch (selectedFramework.value) {
      case 'flutter':
      case 'react_native':
        return 'mobile';
      case 'react':
      case 'nextjs':
        return 'web';
      default:
        return 'mobile';
    }
  }

  /// Progress percentage
  double get progress {
    switch (currentStep.value) {
      case WizardStep.framework:
        return 0.25;
      case WizardStep.backend:
        return 0.5;
      case WizardStep.deployment:
        return 0.75;
      case WizardStep.details:
        return 1.0;
    }
  }

  /// Step title
  String get stepTitle {
    switch (currentStep.value) {
      case WizardStep.framework:
        return 'Choose Framework';
      case WizardStep.backend:
        return 'Backend Service';
      case WizardStep.deployment:
        return 'Deployment';
      case WizardStep.details:
        return 'Project Details';
    }
  }

  /// Step subtitle
  String get stepSubtitle {
    switch (currentStep.value) {
      case WizardStep.framework:
        return 'Select the technology for your app';
      case WizardStep.backend:
        return 'Optional: Add a backend service';
      case WizardStep.deployment:
        return 'Choose where to deploy';
      case WizardStep.details:
        return 'Name your project';
    }
  }

  /// Can go back
  bool get canGoBack => currentStep.value != WizardStep.framework;

  /// Can proceed
  bool get canProceed {
    switch (currentStep.value) {
      case WizardStep.framework:
        return selectedFramework.value.isNotEmpty;
      case WizardStep.backend:
        return true; // Optional
      case WizardStep.deployment:
        if (selectedDeployment.value == 'vercel') {
          // Can only proceed if Vercel is ignored or connected
          // We rely on the screen to show Connect button which updates status
          // The screen should pass connection status to controller or controller should check it
          // Let's assume controller needs to check it.
          // But controller doesn't have the status map directly.
          // Let's rely on the screen to block 'next' visually or
          // better: injecting the status into controller or checking it here.
          // Ideally the controller should manage connection status.
          return true; // We'll block in nextStep if needed
        }
        return selectedDeployment.value.isNotEmpty;
      case WizardStep.details:
        return projectName.value.trim().isNotEmpty;
    }
  }

  /// Check deployment connection
  Future<bool> checkDeploymentConnection() async {
    if (selectedDeployment.value == 'vercel') {
      final backendService = Get.find<BackendConnectionService>();
      final status = await backendService.checkConnectionStatus('vercel');
      return status.isConnected;
    }
    return true;
  }

  /// Go to next step
  Future<void> nextStep() async {
    // Extra validation for deployment
    if (currentStep.value == WizardStep.deployment) {
      if (selectedDeployment.value == 'vercel') {
        final isConnected = await checkDeploymentConnection();
        if (!isConnected) {
          Get.snackbar(
            'Connection Required',
            'Please connect your Vercel account to proceed.',
            snackPosition: SnackPosition.BOTTOM,
            backgroundColor: AppColors.error,
            colorText: const Color(0xFFFFFFFF),
          );
          return;
        }
      }
    }

    if (!canProceed) return;

    isAnimating.value = true;
    await Future.delayed(const Duration(milliseconds: 150));

    lastStep.value = currentStep.value;

    switch (currentStep.value) {
      case WizardStep.framework:
        currentStep.value = WizardStep.backend;
        break;
      case WizardStep.backend:
        currentStep.value = WizardStep.deployment;
        break;
      case WizardStep.deployment:
        currentStep.value = WizardStep.details;
        break;
      case WizardStep.details:
        // Submit
        break;
    }

    isAnimating.value = false;
  }

  /// Go to previous step
  Future<void> previousStep() async {
    if (!canGoBack) return;

    isAnimating.value = true;
    await Future.delayed(const Duration(milliseconds: 150));

    lastStep.value = currentStep.value;

    switch (currentStep.value) {
      case WizardStep.framework:
        break;
      case WizardStep.backend:
        currentStep.value = WizardStep.framework;
        break;
      case WizardStep.deployment:
        currentStep.value = WizardStep.backend;
        break;
      case WizardStep.details:
        currentStep.value = WizardStep.deployment;
        break;
    }

    isAnimating.value = false;
  }

  /// Skip backend selection
  void skipBackend() {
    selectedBackend.value = null;
    nextStep();
  }

  /// Reset wizard
  void reset() {
    currentStep.value = WizardStep.framework;
    selectedFramework.value = 'flutter';
    selectedBackend.value = null;
    selectedDeployment.value = 'github_pages';
    projectName.value = '';
    projectDescription.value = '';
    appIdea.value = '';
    isPrivate.value = false;
  }
}

/// Framework option model
class FrameworkOption {
  final String id;
  final String name;
  final String description;
  final IconData icon;
  final List<Color> gradient;
  final List<String> platforms;

  const FrameworkOption({
    required this.id,
    required this.name,
    required this.description,
    required this.icon,
    required this.gradient,
    required this.platforms,
  });
}

/// Backend option model
class BackendOption {
  final String id;
  final String name;
  final String description;
  final IconData icon;
  final List<Color> gradient;
  final List<String> features;

  const BackendOption({
    required this.id,
    required this.name,
    required this.description,
    required this.icon,
    required this.gradient,
    required this.features,
  });
}

/// Deployment option model
class DeploymentOption {
  final String id;
  final String name;
  final String description;
  final IconData icon;
  final List<Color> gradient;
  final List<String> features;

  const DeploymentOption({
    required this.id,
    required this.name,
    required this.description,
    required this.icon,
    required this.gradient,
    required this.features,
  });
}
