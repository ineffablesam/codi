/// Project detail screen
library;

import 'package:flutter/material.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:get/get.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:intl/intl.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../../core/constants/app_colors.dart';
import '../../../core/utils/sf_font.dart';
import '../controllers/projects_controller.dart';

/// Project detail screen
class ProjectDetailScreen extends StatelessWidget {
  const ProjectDetailScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final controller = Get.find<ProjectsController>();
    final projectId = int.tryParse(Get.parameters['id'] ?? '');

    if (projectId != null) {
      controller.loadProject(projectId);
    }

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: Obx(() => Text(
              controller.selectedProject.value?.name ?? 'Project',
              style: SFPro.font(fontWeight: FontWeight.w600),
            )),
        actions: [
          IconButton(
            icon: const Icon(Icons.more_vert),
            onPressed: () {
              final project = controller.selectedProject.value;
              if (project != null) {
                _showOptionsSheet(context, controller, project);
              }
            },
          ),
        ],
      ),
      body: Obx(() {
        if (controller.isLoading.value) {
          return const Center(child: CircularProgressIndicator());
        }

        final project = controller.selectedProject.value;
        if (project == null) {
          return Center(
            child: Text(
              'Project not found',
              style: SFPro.font(
                fontSize: 16.sp,
                color: AppColors.textSecondary,
              ),
            ),
          );
        }

        return ListView(
          padding: EdgeInsets.all(16.r),
          children: [
            // Status card
            _buildStatusCard(project),
            SizedBox(height: 16.h),

            // Info card
            _buildInfoCard(project),
            SizedBox(height: 16.h),

            // GitHub card
            if (project.githubRepoUrl != null) _buildGitHubCard(project),
            SizedBox(height: 16.h),

            // Deployment card
            if (project.deploymentUrl != null) _buildDeploymentCard(project),
            SizedBox(height: 24.h),

            // Open editor button
            ElevatedButton.icon(
              onPressed: () => controller.openEditor(project),
              icon: Icon(Icons.code, size: 20.r),
              label: const Text('Open Editor'),
            ),
          ],
        );
      }),
    );
  }

  Widget _buildStatusCard(project) {
    return Container(
      padding: EdgeInsets.all(16.r),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(12.r),
        border: Border.all(color: AppColors.border),
      ),
      child: Row(
        children: [
          Container(
            width: 12.r,
            height: 12.r,
            decoration: BoxDecoration(
              color: project.isActive ? AppColors.success : AppColors.warning,
              shape: BoxShape.circle,
            ),
          ),
          SizedBox(width: 12.w),
          Text(
            project.status.toString().toUpperCase(),
            style: SFPro.font(
              fontSize: 14.sp,
              fontWeight: FontWeight.w600,
              color: AppColors.textPrimary,
            ),
          ),
          const Spacer(),
          if (project.lastBuildAt != null)
            Text(
              'Last build: ${DateFormat.yMd().format(project.lastBuildAt!)}',
              style: SFPro.font(
                fontSize: 12.sp,
                color: AppColors.textSecondary,
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildInfoCard(project) {
    return Container(
      padding: EdgeInsets.all(16.r),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(12.r),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Project Info',
            style: SFPro.font(
              fontSize: 16.sp,
              fontWeight: FontWeight.w600,
              color: AppColors.textPrimary,
            ),
          ),
          SizedBox(height: 12.h),
          if (project.description != null && project.description!.isNotEmpty)
            Text(
              project.description!,
              style: SFPro.font(
                fontSize: 14.sp,
                color: AppColors.textSecondary,
              ),
            ),
          SizedBox(height: 12.h),
          Row(
            children: [
              Icon(Icons.calendar_today,
                  size: 16.r, color: AppColors.textSecondary),
              SizedBox(width: 8.w),
              Text(
                'Created ${DateFormat.yMMMd().format(project.createdAt)}',
                style: SFPro.font(
                  fontSize: 12.sp,
                  color: AppColors.textSecondary,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildGitHubCard(project) {
    return Container(
      padding: EdgeInsets.all(16.r),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(12.r),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.code, size: 20.r, color: AppColors.textPrimary),
              SizedBox(width: 8.w),
              Text(
                'GitHub Repository',
                style: SFPro.font(
                  fontSize: 16.sp,
                  fontWeight: FontWeight.w600,
                  color: AppColors.textPrimary,
                ),
              ),
            ],
          ),
          SizedBox(height: 12.h),
          GestureDetector(
            onTap: () => _openUrl(project.githubRepoUrl!),
            child: Text(
              project.githubRepoFullName ?? project.githubRepoUrl!,
              style: GoogleFonts.jetBrainsMono(
                fontSize: 13.sp,
                color: AppColors.primary,
                decoration: TextDecoration.underline,
              ),
            ),
          ),
          if (project.githubCurrentBranch != null) ...[
            SizedBox(height: 8.h),
            Row(
              children: [
                Icon(Icons.account_tree,
                    size: 14.r, color: AppColors.textSecondary),
                SizedBox(width: 4.w),
                Text(
                  project.githubCurrentBranch!,
                  style: SFPro.font(
                    fontSize: 12.sp,
                    color: AppColors.textSecondary,
                  ),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildDeploymentCard(project) {
    return Container(
      padding: EdgeInsets.all(16.r),
      decoration: BoxDecoration(
        color: AppColors.deploymentSuccess,
        borderRadius: BorderRadius.circular(12.r),
        border: Border.all(color: AppColors.success.withOpacity(0.3)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.rocket_launch, size: 20.r, color: AppColors.success),
              SizedBox(width: 8.w),
              Text(
                'Live Deployment',
                style: SFPro.font(
                  fontSize: 16.sp,
                  fontWeight: FontWeight.w600,
                  color: AppColors.textPrimary,
                ),
              ),
            ],
          ),
          SizedBox(height: 12.h),
          GestureDetector(
            onTap: () => _openUrl(project.deploymentUrl!),
            child: Container(
              padding: EdgeInsets.symmetric(horizontal: 12.w, vertical: 8.h),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(8.r),
              ),
              child: Row(
                children: [
                  Icon(Icons.link, size: 16.r, color: AppColors.primary),
                  SizedBox(width: 8.w),
                  Expanded(
                    child: Text(
                      project.deploymentUrl!,
                      style: GoogleFonts.jetBrainsMono(
                        fontSize: 12.sp,
                        color: AppColors.primary,
                      ),
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  Icon(Icons.open_in_new, size: 16.r, color: AppColors.primary),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  void _showOptionsSheet(
      BuildContext context, ProjectsController controller, project) {
    showModalBottomSheet(
      context: context,
      builder: (context) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ListTile(
              leading: const Icon(Icons.code),
              title: const Text('Open Editor'),
              onTap: () {
                Get.back();
                controller.openEditor(project);
              },
            ),
            if (project.githubRepoUrl != null)
              ListTile(
                leading: const Icon(Icons.open_in_browser),
                title: const Text('Open on GitHub'),
                onTap: () {
                  Get.back();
                  _openUrl(project.githubRepoUrl!);
                },
              ),
            ListTile(
              leading: Icon(Icons.delete, color: AppColors.error),
              title: Text('Delete', style: TextStyle(color: AppColors.error)),
              onTap: () {
                Get.back();
                controller.confirmDeleteProject(project);
              },
            ),
          ],
        ),
      ),
    );
  }

  void _openUrl(String url) async {
    final uri = Uri.parse(url);
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    }
  }
}
