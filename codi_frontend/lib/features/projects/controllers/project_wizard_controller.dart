/// Project creation wizard controller
library;

import 'package:get/get.dart';

/// Wizard step enum
enum WizardStep { framework, backend, deployment, details }

/// Project creation wizard controller
class ProjectWizardController extends GetxController {
  // Current step
  final currentStep = WizardStep.framework.obs;
  
  // Selections
  final selectedFramework = 'flutter'.obs;
  final selectedBackend = RxnString();
  final selectedDeployment = 'github_pages'.obs;
  
  // Project details
  final projectName = ''.obs;
  final projectDescription = ''.obs;
  final isPrivate = false.obs;
  
  // Serverpod manual config
  final serverpodServerUrl = ''.obs;
  final serverpodApiKey = ''.obs;
  
  // Animation state
  final isAnimating = false.obs;
  
  /// Framework options
  static const List<FrameworkOption> frameworks = [
    FrameworkOption(
      id: 'flutter',
      name: 'Flutter',
      description: 'Cross-platform mobile & web apps',
      icon: '📱',
      gradient: ['#02569B', '#0175C2'],
      platforms: ['iOS', 'Android', 'Web'],
    ),
    FrameworkOption(
      id: 'react',
      name: 'React',
      description: 'Modern web applications',
      icon: '⚛️',
      gradient: ['#20232A', '#61DAFB'],
      platforms: ['Web'],
    ),
    FrameworkOption(
      id: 'nextjs',
      name: 'Next.js',
      description: 'Full-stack React framework',
      icon: '▲',
      gradient: ['#000000', '#333333'],
      platforms: ['Web', 'API'],
    ),
    FrameworkOption(
      id: 'react_native',
      name: 'React Native',
      description: 'Native mobile apps with React',
      icon: '📲',
      gradient: ['#282C34', '#61DAFB'],
      platforms: ['iOS', 'Android'],
    ),
  ];
  
  /// Backend options
  static const List<BackendOption> backends = [
    BackendOption(
      id: 'supabase',
      name: 'Supabase',
      description: 'Open source Firebase alternative',
      icon: '⚡',
      gradient: ['#3ECF8E', '#1C7C54'],
      features: ['Auth', 'Database', 'Storage', 'Realtime'],
    ),
    BackendOption(
      id: 'firebase',
      name: 'Firebase',
      description: 'Google\'s app platform',
      icon: '🔥',
      gradient: ['#FFCA28', '#F57C00'],
      features: ['Auth', 'Firestore', 'Storage', 'Analytics'],
    ),
    BackendOption(
      id: 'serverpod',
      name: 'Serverpod',
      description: 'Dart backend for Flutter',
      icon: '🎯',
      gradient: ['#0175C2', '#02569B'],
      features: ['Type-safe API', 'ORM', 'Caching', 'Auth'],
    ),
  ];
  
  /// Deployment options
  static const List<DeploymentOption> deployments = [
    DeploymentOption(
      id: 'github_pages',
      name: 'GitHub Pages',
      description: 'Free static site hosting',
      icon: '🐙',
      gradient: ['#24292E', '#586069'],
      features: ['Free', 'HTTPS', 'Custom domain'],
    ),
    DeploymentOption(
      id: 'vercel',
      name: 'Vercel',
      description: 'Edge-first deployment',
      icon: '▲',
      gradient: ['#000000', '#333333'],
      features: ['Edge functions', 'Preview deploys', 'Analytics'],
    ),
    DeploymentOption(
      id: 'netlify',
      name: 'Netlify',
      description: 'Modern web hosting',
      icon: '⚡',
      gradient: ['#00C7B7', '#008C82'],
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
        return selectedDeployment.value.isNotEmpty;
      case WizardStep.details:
        return projectName.value.trim().isNotEmpty;
    }
  }
  
  /// Go to next step
  Future<void> nextStep() async {
    if (!canProceed) return;
    
    isAnimating.value = true;
    await Future.delayed(const Duration(milliseconds: 150));
    
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
    isPrivate.value = false;
  }
}

/// Framework option model
class FrameworkOption {
  final String id;
  final String name;
  final String description;
  final String icon;
  final List<String> gradient;
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
  final String icon;
  final List<String> gradient;
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
  final String icon;
  final List<String> gradient;
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
