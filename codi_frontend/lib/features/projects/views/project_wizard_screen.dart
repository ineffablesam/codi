/// Project creation wizard screen
library;

import 'package:flutter/material.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:get/get.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../../core/constants/app_colors.dart';
import '../controllers/project_wizard_controller.dart';
import '../controllers/projects_controller.dart';
import '../services/backend_connection_service.dart';
import '../widgets/animated_selection_card.dart';
import '../widgets/backend_provider_card.dart';

/// Multi-step project creation wizard with animations
class ProjectWizardScreen extends StatefulWidget {
  const ProjectWizardScreen({super.key});

  @override
  State<ProjectWizardScreen> createState() => _ProjectWizardScreenState();
}

class _ProjectWizardScreenState extends State<ProjectWizardScreen>
    with TickerProviderStateMixin {
  late ProjectWizardController _wizard;
  late AnimationController _fadeController;
  late Animation<double> _fadeAnimation;
  late AnimationController _slideController;
  late Animation<Offset> _slideAnimation;

  final _nameController = TextEditingController();
  final _descriptionController = TextEditingController();
  final _formKey = GlobalKey<FormState>();

  // Backend connection tracking
  late BackendConnectionService _backendService;
  final RxMap<String, bool> _connectionStatus = <String, bool>{}.obs;
  final RxMap<String, bool> _isConnecting = <String, bool>{}.obs;

  @override
  void initState() {
    super.initState();
    _wizard = Get.put(ProjectWizardController());
    _backendService = Get.put(BackendConnectionService());

    // Check connection status for each provider
    _checkBackendConnections();

    _fadeController = AnimationController(
      duration: const Duration(milliseconds: 300),
      vsync: this,
    );
    _fadeAnimation = CurvedAnimation(
      parent: _fadeController,
      curve: Curves.easeInOut,
    );

    _slideController = AnimationController(
      duration: const Duration(milliseconds: 400),
      vsync: this,
    );
    _slideAnimation = Tween<Offset>(
      begin: const Offset(0.05, 0),
      end: Offset.zero,
    ).animate(CurvedAnimation(
      parent: _slideController,
      curve: Curves.easeOutCubic,
    ));

    _fadeController.forward();
    _slideController.forward();

    _wizard.currentStep.listen((_) {
      _fadeController.reset();
      _slideController.reset();
      _fadeController.forward();
      _slideController.forward();
    });
  }

  Future<void> _checkBackendConnections() async {
    // Check backends
    for (final backend in ProjectWizardController.backends) {
      if (backend.id != 'serverpod') {
        final status = await _backendService.checkConnectionStatus(backend.id);
        _connectionStatus[backend.id] = status.isConnected;
      }
    }
    // Check deployments (Vercel)
    final status = await _backendService.checkConnectionStatus('vercel');
    _connectionStatus['vercel'] = status.isConnected;
  }

  Future<void> _connectBackend(String provider) async {
    _isConnecting[provider] = true;
    final success = await _backendService.connectProvider(provider);
    _isConnecting[provider] = false;
    if (success) {
      _connectionStatus[provider] = true;
      Get.snackbar(
        'Connected!',
        '${provider.capitalizeFirst} account connected successfully',
        snackPosition: SnackPosition.BOTTOM,
        backgroundColor: AppColors.success.withOpacity(0.9),
        colorText: Colors.white,
      );
    }
  }

  Future<void> _disconnectBackend(String provider) async {
    final success = await _backendService.disconnectProvider(provider);
    if (success) {
      _connectionStatus[provider] = false;
    }
  }

  @override
  void dispose() {
    _fadeController.dispose();
    _slideController.dispose();
    _nameController.dispose();
    _descriptionController.dispose();
    Get.delete<ProjectWizardController>();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: Column(
          children: [
            _buildHeader(),
            Expanded(
              child: _buildStepContent(),
            ),
            _buildFooter(),
          ],
        ),
      ),
    );
  }

  Widget _buildHeader() {
    return Container(
      padding: EdgeInsets.fromLTRB(16.w, 16.h, 16.w, 24.h),
      child: Column(
        children: [
          // Top bar with close and progress
          Row(
            children: [
              IconButton(
                onPressed: () => Get.back(),
                icon: Icon(
                  Icons.close,
                  color: AppColors.textSecondary,
                  size: 24.r,
                ),
              ),
              Expanded(
                child: _buildProgressIndicator(),
              ),
              SizedBox(width: 48.w), // Balance
            ],
          ),
          SizedBox(height: 24.h),
          // Title and subtitle
          Obx(() => Column(
                children: [
                  Text(
                    _wizard.stepTitle,
                    style: GoogleFonts.inter(
                      fontSize: 28.sp,
                      fontWeight: FontWeight.w800,
                      color: AppColors.textPrimary,
                      letterSpacing: -0.5,
                    ),
                  ),
                  SizedBox(height: 8.h),
                  Text(
                    _wizard.stepSubtitle,
                    style: GoogleFonts.inter(
                      fontSize: 16.sp,
                      color: AppColors.textSecondary,
                    ),
                  ),
                ],
              )),
        ],
      ),
    );
  }

  Widget _buildProgressIndicator() {
    return Obx(() {
      final progress = _wizard.progress;
      return Container(
        height: 6.h,
        margin: EdgeInsets.symmetric(horizontal: 16.w),
        decoration: BoxDecoration(
          color: AppColors.border.withOpacity(0.3),
          borderRadius: BorderRadius.circular(3.r),
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
                    gradient: const LinearGradient(
                      colors: [AppColors.primary, AppColors.info],
                    ),
                    borderRadius: BorderRadius.circular(3.r),
                    boxShadow: [
                      BoxShadow(
                        color: AppColors.primary.withOpacity(0.4),
                        blurRadius: 8,
                        offset: const Offset(0, 2),
                      ),
                    ],
                  ),
                ),
              ],
            );
          },
        ),
      );
    });
  }

  Widget _buildStepContent() {
    return FadeTransition(
      opacity: _fadeAnimation,
      child: SlideTransition(
        position: _slideAnimation,
        child: SingleChildScrollView(
          padding: EdgeInsets.symmetric(horizontal: 20.w),
          child: Obx(() {
            switch (_wizard.currentStep.value) {
              case WizardStep.framework:
                return _buildFrameworkStep();
              case WizardStep.backend:
                return _buildBackendStep();
              case WizardStep.deployment:
                return _buildDeploymentStep();
              case WizardStep.details:
                return _buildDetailsStep();
            }
          }),
        ),
      ),
    );
  }

  Widget _buildFrameworkStep() {
    return Column(
      children: [
        ...ProjectWizardController.frameworks.map((framework) {
          return Padding(
            padding: EdgeInsets.only(bottom: 16.h),
            child: Obx(() => AnimatedSelectionCard(
                  id: framework.id,
                  icon: framework.icon,
                  title: framework.name,
                  subtitle: framework.description,
                  tags: framework.platforms,
                  gradientColors: framework.gradient,
                  isSelected: _wizard.selectedFramework.value == framework.id,
                  onTap: () => _wizard.selectedFramework.value = framework.id,
                )),
          );
        }),
        SizedBox(height: 40.h),
      ],
    );
  }

  Widget _buildBackendStep() {
    return Column(
      children: [
        // Skip option
        Obx(() => SkipOptionCard(
              title: 'No Backend',
              subtitle: 'I\'ll set this up later',
              isSelected: _wizard.selectedBackend.value == null,
              onTap: () => _wizard.selectedBackend.value = null,
            )),
        SizedBox(height: 20.h),
        Divider(color: AppColors.border.withOpacity(0.3)),
        SizedBox(height: 20.h),
        // Backend providers with Connect buttons
        ...ProjectWizardController.backends.map((backend) {
          final isServerpod = backend.id == 'serverpod';
          return Padding(
            padding: EdgeInsets.only(bottom: 16.h),
            child: Obx(() => BackendProviderCard(
                  id: backend.id,
                  icon: backend.icon,
                  title: backend.name,
                  description: backend.description,
                  features: backend.features,
                  gradientColors: backend.gradient,
                  isSelected: _wizard.selectedBackend.value == backend.id,
                  isConnected: _connectionStatus[backend.id] ?? false,
                  isConnecting: _isConnecting[backend.id] ?? false,
                  showManualConfig: isServerpod,
                  onSelect: () => _wizard.selectedBackend.value = backend.id,
                  onConnect: isServerpod ? null : () => _connectBackend(backend.id),
                  onDisconnect: isServerpod ? null : () => _disconnectBackend(backend.id),
                  onManualConfig: isServerpod
                      ? () => Get.dialog(
                            ServerpodConfigDialog(
                              onSave: (serverUrl, apiKey) {
                                // Store for later use during project creation
                                _wizard.serverpodServerUrl.value = serverUrl;
                                _wizard.serverpodApiKey.value = apiKey ?? '';
                                Get.snackbar(
                                  'Configured!',
                                  'Serverpod settings saved',
                                  snackPosition: SnackPosition.BOTTOM,
                                  backgroundColor: AppColors.success.withOpacity(0.9),
                                  colorText: Colors.white,
                                );
                              },
                            ),
                          )
                      : null,
                )),
          );
        }),
        SizedBox(height: 40.h),
      ],
    );
  }

  Widget _buildDeploymentStep() {
    return Column(
      children: [
        ...ProjectWizardController.deployments.map((deployment) {
          if (deployment.id == 'vercel') {
             return Padding(
              padding: EdgeInsets.only(bottom: 16.h),
              child: Obx(() => BackendProviderCard(
                    id: deployment.id,
                    icon: deployment.icon,
                    title: deployment.name,
                    description: deployment.description,
                    features: deployment.features,
                    gradientColors: deployment.gradient,
                    isSelected: _wizard.selectedDeployment.value == deployment.id,
                    isConnected: _connectionStatus[deployment.id] ?? false,
                    isConnecting: _isConnecting[deployment.id] ?? false,
                    showManualConfig: false,
                    onSelect: () => _wizard.selectedDeployment.value = deployment.id,
                    onConnect: () => _connectBackend(deployment.id),
                    onDisconnect: () => _disconnectBackend(deployment.id),
                  )),
            );
          }
          return Padding(
            padding: EdgeInsets.only(bottom: 16.h),
            child: Obx(() => AnimatedSelectionCard(
                  id: deployment.id,
                  icon: deployment.icon,
                  title: deployment.name,
                  subtitle: deployment.description,
                  tags: deployment.features,
                  gradientColors: deployment.gradient,
                  isSelected: _wizard.selectedDeployment.value == deployment.id,
                  onTap: () => _wizard.selectedDeployment.value = deployment.id,
                )),
          );
        }),
        SizedBox(height: 40.h),
      ],
    );
  }

  Widget _buildDetailsStep() {
    return Form(
      key: _formKey,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Summary card
          _buildSummaryCard(),
          SizedBox(height: 32.h),

          // Project name
          Text(
            'Project Name',
            style: GoogleFonts.inter(
              fontSize: 14.sp,
              fontWeight: FontWeight.w600,
              color: AppColors.textPrimary,
            ),
          ),
          SizedBox(height: 8.h),
          TextFormField(
            controller: _nameController,
            decoration: InputDecoration(
              hintText: 'my-awesome-app',
              prefixIcon: Icon(Icons.folder_outlined, size: 20.r),
            ),
            validator: (value) {
              if (value == null || value.trim().isEmpty) {
                return 'Please enter a project name';
              }
              if (value.length < 3) {
                return 'Name must be at least 3 characters';
              }
              return null;
            },
            onChanged: (value) => _wizard.projectName.value = value,
            textInputAction: TextInputAction.next,
            autofocus: true,
          ),
          SizedBox(height: 24.h),

          // Description
          Text(
            'Description (Optional)',
            style: GoogleFonts.inter(
              fontSize: 14.sp,
              fontWeight: FontWeight.w600,
              color: AppColors.textPrimary,
            ),
          ),
          SizedBox(height: 8.h),
          TextFormField(
            controller: _descriptionController,
            decoration: InputDecoration(
              hintText: 'A brief description of your project',
              prefixIcon: Icon(Icons.description_outlined, size: 20.r),
            ),
            maxLines: 2,
            onChanged: (value) => _wizard.projectDescription.value = value,
          ),
          SizedBox(height: 24.h),

          // Private toggle
          _buildPrivateToggle(),
          SizedBox(height: 40.h),
        ],
      ),
    );
  }

  Widget _buildSummaryCard() {
    final framework = ProjectWizardController.frameworks
        .firstWhere((f) => f.id == _wizard.selectedFramework.value);
    final backend = _wizard.selectedBackend.value != null
        ? ProjectWizardController.backends
            .firstWhere((b) => b.id == _wizard.selectedBackend.value)
        : null;
    final deployment = ProjectWizardController.deployments
        .firstWhere((d) => d.id == _wizard.selectedDeployment.value);

    return Container(
      padding: EdgeInsets.all(20.r),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            AppColors.primary.withOpacity(0.1),
            AppColors.info.withOpacity(0.05),
          ],
        ),
        borderRadius: BorderRadius.circular(16.r),
        border: Border.all(
          color: AppColors.primary.withOpacity(0.2),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Your Setup',
            style: GoogleFonts.inter(
              fontSize: 12.sp,
              fontWeight: FontWeight.w600,
              color: AppColors.primary,
              letterSpacing: 1,
            ),
          ),
          SizedBox(height: 16.h),
          Row(
            children: [
              _buildSummaryItem(framework.icon, framework.name, 'Framework'),
              SizedBox(width: 16.w),
              if (backend != null)
                _buildSummaryItem(backend.icon, backend.name, 'Backend'),
              if (backend != null) SizedBox(width: 16.w),
              _buildSummaryItem(deployment.icon, deployment.name, 'Deploy'),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildSummaryItem(String icon, String title, String label) {
    return Column(
      children: [
        Container(
          width: 48.r,
          height: 48.r,
          decoration: BoxDecoration(
            color: AppColors.surface,
            borderRadius: BorderRadius.circular(12.r),
            border: Border.all(color: AppColors.border.withOpacity(0.3)),
          ),
          child: Center(
            child: Text(icon, style: TextStyle(fontSize: 24.sp)),
          ),
        ),
        SizedBox(height: 8.h),
        Text(
          title,
          style: GoogleFonts.inter(
            fontSize: 12.sp,
            fontWeight: FontWeight.w600,
            color: AppColors.textPrimary,
          ),
        ),
        Text(
          label,
          style: GoogleFonts.inter(
            fontSize: 10.sp,
            color: AppColors.textSecondary,
          ),
        ),
      ],
    );
  }

  Widget _buildPrivateToggle() {
    return Obx(() {
      final isPrivate = _wizard.isPrivate.value;
      return GestureDetector(
        onTap: () => _wizard.isPrivate.value = !_wizard.isPrivate.value,
        child: Container(
          padding: EdgeInsets.all(16.r),
          decoration: BoxDecoration(
            color: AppColors.surface,
            borderRadius: BorderRadius.circular(12.r),
            border: Border.all(color: AppColors.border.withOpacity(0.3)),
          ),
          child: Row(
            children: [
              Icon(
                isPrivate ? Icons.lock : Icons.lock_open,
                size: 24.r,
                color: AppColors.textSecondary,
              ),
              SizedBox(width: 12.w),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Private Repository',
                      style: GoogleFonts.inter(
                        fontSize: 14.sp,
                        fontWeight: FontWeight.w600,
                        color: AppColors.textPrimary,
                      ),
                    ),
                    SizedBox(height: 2.h),
                    Text(
                      'Only you can see this repository',
                      style: GoogleFonts.inter(
                        fontSize: 12.sp,
                        color: AppColors.textSecondary,
                      ),
                    ),
                  ],
                ),
              ),
              Switch(
                value: isPrivate,
                onChanged: (value) => _wizard.isPrivate.value = value,
                activeColor: AppColors.primary,
              ),
            ],
          ),
        ),
      );
    });
  }

  Widget _buildFooter() {
    return Container(
      padding: EdgeInsets.all(20.r),
      decoration: BoxDecoration(
        color: AppColors.background,
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.05),
            blurRadius: 10,
            offset: const Offset(0, -4),
          ),
        ],
      ),
      child: Obx(() {
        final currentStep = _wizard.currentStep.value;
        final isLastStep = currentStep == WizardStep.details;
        final canGoBack = _wizard.canGoBack;
        final canProceed = _wizard.canProceed;
        final projectsController = Get.find<ProjectsController>();
        final isCreating = projectsController.isCreating.value;

        return Row(
          children: [
            // Back button
            if (canGoBack)
              Expanded(
                child: OutlinedButton(
                  onPressed: _wizard.previousStep,
                  style: OutlinedButton.styleFrom(
                    padding: EdgeInsets.symmetric(vertical: 16.h),
                    side: BorderSide(color: AppColors.border),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12.r),
                    ),
                  ),
                  child: Text(
                    'Back',
                    style: GoogleFonts.inter(
                      fontSize: 16.sp,
                      fontWeight: FontWeight.w600,
                      color: AppColors.textSecondary,
                    ),
                  ),
                ),
              ),
            if (canGoBack) SizedBox(width: 12.w),
            // Next/Create button
            Expanded(
              flex: canGoBack ? 2 : 1,
              child: ElevatedButton(
                onPressed: canProceed
                    ? (isLastStep ? _createProject : _wizard.nextStep)
                    : null,
                style: ElevatedButton.styleFrom(
                  padding: EdgeInsets.symmetric(vertical: 16.h),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12.r),
                  ),
                ),
                child: isCreating
                    ? SizedBox(
                        width: 24.r,
                        height: 24.r,
                        child: const CircularProgressIndicator(
                          strokeWidth: 2,
                          valueColor:
                              AlwaysStoppedAnimation<Color>(Colors.white),
                        ),
                      )
                    : Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Text(
                            isLastStep ? 'Create Project' : 'Continue',
                            style: GoogleFonts.inter(
                              fontSize: 16.sp,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                          if (!isLastStep) ...[
                            SizedBox(width: 8.w),
                            Icon(Icons.arrow_forward, size: 20.r),
                          ] else ...[
                            SizedBox(width: 8.w),
                            Icon(Icons.rocket_launch, size: 20.r),
                          ],
                        ],
                      ),
              ),
            ),
          ],
        );
      }),
    );
  }

  Future<void> _createProject() async {
    if (!(_formKey.currentState?.validate() ?? false)) return;

    final controller = Get.find<ProjectsController>();

    await controller.createProject(
      name: _nameController.text.trim(),
      description: _descriptionController.text.trim().isEmpty
          ? null
          : _descriptionController.text.trim(),
      isPrivate: _wizard.isPrivate.value,
      platformType: _wizard.platformType,
      framework: _wizard.selectedFramework.value,
      backendType: _wizard.selectedBackend.value,
      deploymentPlatform: _wizard.selectedDeployment.value,
    );
  }
}
