/// Project creation wizard screen
library;

import 'package:animations/animations.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:get/get.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../../../core/constants/app_colors.dart';
import '../../../core/utils/sf_font.dart';
import '../controllers/project_wizard_controller.dart';
import '../controllers/projects_controller.dart';
import '../services/backend_connection_service.dart';
import '../widgets/animated_selection_card.dart';
import '../widgets/backend_provider_card.dart';

/// Multi-step project creation wizard with compact dark theme
class ProjectWizardScreen extends StatelessWidget {
  const ProjectWizardScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final wizard = Get.put(ProjectWizardController());
    Get.put(BackendConnectionService());

    return AnnotatedRegion<SystemUiOverlayStyle>(
      value: SystemUiOverlayStyle.light,
      child: Scaffold(
        backgroundColor: Get.theme.scaffoldBackgroundColor,
        body: SafeArea(
          child: Column(
            mainAxisSize: MainAxisSize.max,
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisAlignment: MainAxisAlignment.start,
            children: [
              _buildHeader(wizard),
              Expanded(
                child: _buildStepContent(wizard),
              ),
              _buildFooter(wizard),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildHeader(ProjectWizardController wizard) {
    return Container(
      padding: EdgeInsets.fromLTRB(12.w, 8.h, 12.w, 16.h),
      child: Column(
        children: [
          // Top bar with close and progress
          Row(
            children: [
              GestureDetector(
                onTap: () => Get.back(),
                child: Container(
                  width: 36.r,
                  height: 36.r,
                  decoration: BoxDecoration(
                    color: AppColors.surfaceDark,
                    borderRadius: BorderRadius.circular(10.r),
                  ),
                  child: Icon(
                    Icons.chevron_left_rounded,
                    color: AppColors.textInverse,
                    size: 20.r,
                  ),
                ),
              ),
              SizedBox(width: 12.w),
              Expanded(
                child: _buildProgressIndicator(wizard),
              ),
              SizedBox(width: 48.w),
            ],
          ),
          SizedBox(height: 16.h),
          // Title and subtitle
          Obx(() => Column(
                children: [
                  Text(
                    wizard.stepTitle,
                    style: SFPro.bold(
                      fontSize: 22.sp,
                      color: Get.theme.textTheme.bodyLarge?.color,
                    ),
                  ),
                  SizedBox(height: 4.h),
                  Text(
                    wizard.stepSubtitle,
                    style: SFPro.regular(
                      fontSize: 14.sp,
                      color: AppColors.textSecondary,
                    ),
                  ),
                ],
              )),
        ],
      ),
    );
  }

  Widget _buildProgressIndicator(ProjectWizardController wizard) {
    return Obx(() {
      final progress = wizard.progress;
      return Container(
        height: 4.h,
        decoration: BoxDecoration(
          color: AppColors.surfaceDark,
          borderRadius: BorderRadius.circular(2.r),
        ),
        child: LayoutBuilder(
          builder: (context, constraints) {
            return Stack(
              children: [
                AnimatedContainer(
                  duration: const Duration(milliseconds: 400),
                  curve: Curves.easeOutCubic,
                  width: constraints.maxWidth * progress,
                  decoration: BoxDecoration(
                    color: AppColors.primary,
                    borderRadius: BorderRadius.circular(2.r),
                  ),
                ),
              ],
            );
          },
        ),
      );
    });
  }

  Widget _buildStepContent(ProjectWizardController wizard) {
    return Obx(() {
      final step = wizard.currentStep.value;

      // Build the current step widget
      Widget currentStepWidget;
      switch (step) {
        case WizardStep.framework:
          currentStepWidget = _buildFrameworkStep(wizard);
          break;
        case WizardStep.backend:
          currentStepWidget = _buildBackendStep(wizard);
          break;
        case WizardStep.deployment:
          currentStepWidget = _buildDeploymentStep(wizard);
          break;
        case WizardStep.details:
          currentStepWidget = _buildDetailsStep(wizard);
          break;
      }

      return PageTransitionSwitcher(
        duration: const Duration(milliseconds: 350),
        reverse: wizard.currentStep.value.index < wizard.lastStep.value.index,
        transitionBuilder: (child, animation, secondaryAnimation) {
          return SharedAxisTransition(
            fillColor: Colors.transparent,
            animation: animation,
            secondaryAnimation: secondaryAnimation,
            transitionType: SharedAxisTransitionType.horizontal,
            child: child,
          );
        },
        child: SingleChildScrollView(
          key: ValueKey(step),
          padding: EdgeInsets.symmetric(horizontal: 16.w),
          child: currentStepWidget,
        ),
      );
    });
  }

  Widget _buildFrameworkStep(ProjectWizardController wizard) {
    return Column(
      mainAxisSize: MainAxisSize.max,
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisAlignment: MainAxisAlignment.start,
      children: [
        ...ProjectWizardController.frameworks.map((framework) {
          return Padding(
            padding: EdgeInsets.only(bottom: 10.h),
            child: Obx(() => AnimatedSelectionCard(
                  id: framework.id,
                  iconWidget: Icon(framework.icon,
                      color: framework.gradient.first, size: 20.r),
                  title: framework.name,
                  subtitle: framework.description,
                  tags: framework.platforms,
                  gradientColors: framework.gradient,
                  isSelected: wizard.selectedFramework.value == framework.id,
                  onTap: () => wizard.selectedFramework.value = framework.id,
                )),
          );
        }),
        SizedBox(height: 100.h),
      ],
    );
  }

  Widget _buildBackendStep(ProjectWizardController wizard) {
    final backendService = Get.find<BackendConnectionService>();
    final connectionStatus = <String, bool>{}.obs;
    final isConnecting = <String, bool>{}.obs;

    for (final backend in ProjectWizardController.backends) {
      if (backend.id != 'serverpod') {
        backendService.checkConnectionStatus(backend.id).then((status) {
          connectionStatus[backend.id] = status.isConnected;
        });
      }
    }

    return Column(
      children: [
        Obx(() => SkipOptionCard(
              title: 'No Backend',
              subtitle: 'I\'ll set this up later',
              isSelected: wizard.selectedBackend.value == null,
              onTap: () => wizard.selectedBackend.value = null,
            )),
        SizedBox(height: 12.h),
        Container(
          height: 1,
          color: AppColors.surfaceDark,
        ),
        SizedBox(height: 12.h),
        ...ProjectWizardController.backends.map((backend) {
          final isServerpod = backend.id == 'serverpod';
          return Padding(
            padding: EdgeInsets.only(bottom: 14.h),
            child: Obx(() => BackendProviderCard(
                  id: backend.id,
                  iconWidget: Icon(backend.icon,
                      color: backend.gradient.first, size: 18.r),
                  title: backend.name,
                  description: backend.description,
                  features: backend.features,
                  gradientColors: backend.gradient,
                  isSelected: wizard.selectedBackend.value == backend.id,
                  isConnected: connectionStatus[backend.id] ?? false,
                  isConnecting: isConnecting[backend.id] ?? false,
                  showManualConfig: false,
                  isAutoManaged: isServerpod,
                  onSelect: () => wizard.selectedBackend.value = backend.id,
                  onConnect: isServerpod
                      ? null
                      : () async {
                          isConnecting[backend.id] = true;
                          final success =
                              await backendService.connectProvider(backend.id);
                          isConnecting[backend.id] = false;
                          if (success) {
                            connectionStatus[backend.id] = true;
                            Get.snackbar(
                              'Connected!',
                              '${backend.name} connected',
                              snackPosition: SnackPosition.BOTTOM,
                              backgroundColor:
                                  AppColors.success.withOpacity(0.9),
                              colorText: Colors.white,
                              margin: EdgeInsets.all(16.r),
                            );
                          }
                        },
                  onDisconnect: isServerpod
                      ? null
                      : () async {
                          final success = await backendService
                              .disconnectProvider(backend.id);
                          if (success) {
                            connectionStatus[backend.id] = false;
                          }
                        },
                  onManualConfig: null,
                )),
          );
        }),
        SizedBox(height: 20.h),
      ],
    );
  }

  Widget _buildDeploymentStep(ProjectWizardController wizard) {
    final backendService = Get.find<BackendConnectionService>();
    final connectionStatus = <String, bool>{}.obs;
    final isConnecting = <String, bool>{}.obs;

    backendService.checkConnectionStatus('vercel').then((status) {
      connectionStatus['vercel'] = status.isConnected;
    });

    return Column(
      children: [
        ...ProjectWizardController.deployments.map((deployment) {
          if (deployment.id == 'vercel') {
            return Padding(
              padding: EdgeInsets.only(bottom: 10.h),
              child: Obx(() => BackendProviderCard(
                    id: deployment.id,
                    iconWidget: Icon(deployment.icon,
                        color: deployment.gradient.first, size: 18.r),
                    title: deployment.name,
                    description: deployment.description,
                    features: deployment.features,
                    gradientColors: deployment.gradient,
                    isSelected:
                        wizard.selectedDeployment.value == deployment.id,
                    isConnected: connectionStatus[deployment.id] ?? false,
                    isConnecting: isConnecting[deployment.id] ?? false,
                    showManualConfig: false,
                    onSelect: () =>
                        wizard.selectedDeployment.value = deployment.id,
                    onConnect: () async {
                      isConnecting[deployment.id] = true;
                      final success =
                          await backendService.connectProvider(deployment.id);
                      isConnecting[deployment.id] = false;
                      if (success) {
                        connectionStatus[deployment.id] = true;
                        Get.snackbar(
                          'Connected!',
                          '${deployment.name} connected',
                          snackPosition: SnackPosition.BOTTOM,
                          backgroundColor: AppColors.success.withOpacity(0.9),
                          colorText: Colors.white,
                          margin: EdgeInsets.all(16.r),
                        );
                      }
                    },
                    onDisconnect: () async {
                      final success = await backendService
                          .disconnectProvider(deployment.id);
                      if (success) {
                        connectionStatus[deployment.id] = false;
                      }
                    },
                  )),
            );
          }
          return Padding(
            padding: EdgeInsets.only(bottom: 10.h),
            child: Obx(() => AnimatedSelectionCard(
                  id: deployment.id,
                  iconWidget: Icon(deployment.icon,
                      color: deployment.gradient.first, size: 20.r),
                  title: deployment.name,
                  subtitle: deployment.description,
                  tags: deployment.features,
                  gradientColors: deployment.gradient,
                  isSelected: wizard.selectedDeployment.value == deployment.id,
                  onTap: () => wizard.selectedDeployment.value = deployment.id,
                )),
          );
        }),
        SizedBox(height: 160.h),
      ],
    );
  }

  Widget _buildDetailsStep(ProjectWizardController wizard) {
    return Form(
      key: wizard.formKey,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildSummaryCard(wizard),
          SizedBox(height: 20.h),

          // Project name
          _buildFieldLabel('Project Name'),
          SizedBox(height: 6.h),
          _buildTextField(
            controller: wizard.nameController,
            hint: 'my-awesome-app',
            icon: LucideIcons.folder,
            validator: (value) {
              if (value == null || value.trim().isEmpty) {
                return 'Please enter a project name';
              }
              if (value.length < 3) {
                return 'Name must be at least 3 characters';
              }
              return null;
            },
            autofocus: true,
          ),
          SizedBox(height: 16.h),

          // Description
          _buildFieldLabel('Description (Optional)'),
          SizedBox(height: 6.h),
          _buildTextField(
            controller: wizard.descriptionController,
            hint: 'A brief description',
            icon: LucideIcons.fileText,
            maxLines: 2,
          ),
          SizedBox(height: 16.h),

          // App Idea
          _buildFieldLabel('App Idea (Optional)'),
          SizedBox(height: 6.h),
          _buildTextField(
            controller: wizard.appIdeaController,
            hint: 'e.g., A church app with events, sermons, donations',
            icon: LucideIcons.lightbulb,
            maxLines: 3,
          ),
          SizedBox(height: 4.h),
          Text(
            'AI will automatically build your app based on this idea',
            style: SFPro.regular(
              fontSize: 11.sp,
              color: AppColors.textSecondary,
            ),
          ),
          SizedBox(height: 16.h),

          // Private toggle
          _buildPrivateToggle(wizard),
          SizedBox(height: 24.h),
        ],
      ),
    );
  }

  Widget _buildFieldLabel(String label) {
    return Text(
      label,
      style: SFPro.medium(
        fontSize: 13.sp,
        color: AppColors.textSecondary,
      ),
    );
  }

  Widget _buildTextField({
    required TextEditingController controller,
    required String hint,
    required IconData icon,
    String? Function(String?)? validator,
    int maxLines = 1,
    bool autofocus = false,
  }) {
    return TextFormField(
      controller: controller,
      style: SFPro.regular(fontSize: 14.sp, color: AppColors.textInverse),
      decoration: InputDecoration(
        hintText: hint,
        hintStyle: SFPro.regular(
            fontSize: 14.sp, color: AppColors.textSecondary.withOpacity(0.5)),
        prefixIcon: Icon(icon, size: 18.r, color: AppColors.textSecondary),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10.r),
          borderSide: BorderSide.none,
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10.r),
          borderSide: BorderSide.none,
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10.r),
          borderSide:
              BorderSide(color: AppColors.primary.withOpacity(0.5), width: 1.5),
        ),
        filled: true,
        fillColor: AppColors.surfaceDark,
        contentPadding: EdgeInsets.symmetric(horizontal: 14.w, vertical: 12.h),
      ),
      validator: validator,
      maxLines: maxLines,
      textInputAction: TextInputAction.next,
      autofocus: autofocus,
    );
  }

  Widget _buildSummaryCard(ProjectWizardController wizard) {
    final framework = ProjectWizardController.frameworks
        .firstWhere((f) => f.id == wizard.selectedFramework.value);
    final backend = wizard.selectedBackend.value != null
        ? ProjectWizardController.backends
            .firstWhere((b) => b.id == wizard.selectedBackend.value)
        : null;
    final deployment = ProjectWizardController.deployments
        .firstWhere((d) => d.id == wizard.selectedDeployment.value);

    return Container(
      padding: EdgeInsets.all(14.r),
      decoration: BoxDecoration(
        color: AppColors.surfaceDark,
        borderRadius: BorderRadius.circular(12.r),
      ),
      child: Row(
        children: [
          _buildSummaryItem(framework.icon, framework.name),
          if (backend != null) ...[
            SizedBox(width: 12.w),
            Icon(LucideIcons.chevronRight,
                size: 14.r, color: AppColors.textSecondary.withOpacity(0.5)),
            SizedBox(width: 12.w),
            _buildSummaryItem(backend.icon, backend.name),
          ],
          SizedBox(width: 12.w),
          Icon(LucideIcons.chevronRight,
              size: 14.r, color: AppColors.textSecondary.withOpacity(0.5)),
          SizedBox(width: 12.w),
          _buildSummaryItem(deployment.icon, deployment.name),
        ],
      ),
    );
  }

  Widget _buildSummaryItem(IconData icon, String title) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: 16.r, color: AppColors.textSecondary),
        SizedBox(width: 6.w),
        Text(
          title,
          style: SFPro.medium(
            fontSize: 12.sp,
            color: AppColors.textInverse,
          ),
        ),
      ],
    );
  }

  Widget _buildPrivateToggle(ProjectWizardController wizard) {
    return Obx(() {
      final isPrivate = wizard.isPrivate.value;
      return GestureDetector(
        onTap: () => wizard.isPrivate.value = !wizard.isPrivate.value,
        child: Container(
          padding: EdgeInsets.all(12.r),
          decoration: BoxDecoration(
            color: AppColors.surfaceDark,
            borderRadius: BorderRadius.circular(10.r),
          ),
          child: Row(
            children: [
              Icon(
                isPrivate ? LucideIcons.lock : LucideIcons.lockOpen,
                size: 18.r,
                color: AppColors.textSecondary,
              ),
              SizedBox(width: 10.w),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Private Repository',
                      style: SFPro.medium(
                        fontSize: 13.sp,
                        color: AppColors.textInverse,
                      ),
                    ),
                    Text(
                      'Only you can see this repository',
                      style: SFPro.regular(
                        fontSize: 11.sp,
                        color: AppColors.textSecondary,
                      ),
                    ),
                  ],
                ),
              ),
              Switch(
                value: isPrivate,
                onChanged: (value) => wizard.isPrivate.value = value,
                activeColor: AppColors.primary,
              ),
            ],
          ),
        ),
      );
    });
  }

  Widget _buildFooter(ProjectWizardController wizard) {
    return Container(
      padding: EdgeInsets.fromLTRB(16.w, 12.h, 16.w, 16.h),
      decoration: BoxDecoration(
        color: Get.theme.scaffoldBackgroundColor,
        border: Border(
          top: BorderSide(
            color: AppColors.textTertiary.withOpacity(0.4),
            width: 1,
          ),
        ),
      ),
      child: Obx(() {
        final currentStep = wizard.currentStep.value;
        final isLastStep = currentStep == WizardStep.details;
        final canGoBack = wizard.canGoBack;
        final canProceed = wizard.canProceed;
        final projectsController = Get.find<ProjectsController>();
        final isCreating = projectsController.isCreating.value;

        return Row(
          children: [
            AnimatedScale(
              scale: canGoBack ? 1.0 : 0.0,
              duration: const Duration(milliseconds: 200),
              curve: Curves.easeOut,
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 200),
                width: canGoBack ? 48.r : 0,
                height: 48.r,
                curve: Curves.easeOut,
                child: canGoBack
                    ? GestureDetector(
                        onTap: wizard.previousStep,
                        child: Container(
                          decoration: BoxDecoration(
                            color: AppColors.surfaceDark,
                            borderRadius: BorderRadius.circular(12.r),
                          ),
                          child: Icon(
                            Icons.chevron_left_rounded,
                            color: AppColors.textInverse,
                            size: 20.r,
                          ),
                        ),
                      )
                    : const SizedBox.shrink(),
              ),
            ),
            AnimatedContainer(
              duration: const Duration(milliseconds: 200),
              width: canGoBack ? 12.w : 0,
              curve: Curves.easeOut,
            ),
            Expanded(
              child: GestureDetector(
                onTap: canProceed
                    ? (isLastStep
                        ? () => _createProject(wizard)
                        : wizard.nextStep)
                    : null,
                child: AnimatedContainer(
                  duration: const Duration(milliseconds: 200),
                  height: 48.h,
                  curve: Curves.easeOut,
                  decoration: BoxDecoration(
                    color: canProceed
                        ? AppColors.primary
                        : AppColors.primary.withOpacity(0.4),
                    borderRadius: BorderRadius.circular(12.r),
                  ),
                  child: Center(
                    child: AnimatedSwitcher(
                      duration: const Duration(milliseconds: 200),
                      child: isCreating
                          ? SizedBox(
                              key: const ValueKey('loading'),
                              width: 20.r,
                              height: 20.r,
                              child: const CircularProgressIndicator(
                                strokeWidth: 2,
                                valueColor:
                                    AlwaysStoppedAnimation<Color>(Colors.white),
                              ),
                            )
                          : Row(
                              key: ValueKey(isLastStep),
                              mainAxisAlignment: MainAxisAlignment.center,
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Text(
                                  isLastStep ? 'Create Project' : 'Continue',
                                  style: SFPro.semibold(
                                    fontSize: 15.sp,
                                    color: Colors.white,
                                  ),
                                ),
                                SizedBox(width: 6.w),
                                Icon(
                                  isLastStep
                                      ? LucideIcons.rocket
                                      : Icons.arrow_forward_rounded,
                                  size: 18.r,
                                  color: Colors.white,
                                ),
                              ],
                            ),
                    ),
                  ),
                ),
              ),
            ),
          ],
        );
      }),
    );
  }

  Future<void> _createProject(ProjectWizardController wizard) async {
    if (!(wizard.formKey.currentState?.validate() ?? false)) return;

    final controller = Get.find<ProjectsController>();

    await controller.createProject(
      name: wizard.projectName.value.trim(),
      description: wizard.projectDescription.value.trim().isEmpty
          ? null
          : wizard.projectDescription.value.trim(),
      isPrivate: wizard.isPrivate.value,
      platformType: wizard.platformType,
      framework: wizard.selectedFramework.value,
      backendType: wizard.selectedBackend.value,
      deploymentPlatform: wizard.selectedDeployment.value,
      appIdea: wizard.appIdea.value.trim().isEmpty
          ? null
          : wizard.appIdea.value.trim(),
    );
  }
}
