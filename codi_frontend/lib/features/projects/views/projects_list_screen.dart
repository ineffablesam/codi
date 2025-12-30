/// Projects list screen
library;

import 'package:flutter/material.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:get/get.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../../config/routes.dart';
import '../../../core/constants/app_colors.dart';
import '../../../core/constants/app_strings.dart';
import '../../../core/constants/image_placeholders.dart';
import '../../auth/controllers/auth_controller.dart';
import '../controllers/projects_controller.dart';
import '../widgets/project_card.dart';

/// Projects list screen
class ProjectsListScreen extends StatelessWidget {
  const ProjectsListScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final controller = Get.find<ProjectsController>();
    final authController = Get.find<AuthController>();

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: Text(
          AppStrings.myProjects,
          style: GoogleFonts.inter(fontWeight: FontWeight.w600),
        ),
        actions: [
          // User avatar
          Obx(() {
            final user = authController.currentUser.value;
            return GestureDetector(
              onTap: () => Get.toNamed(AppRoutes.settings),
              child: Padding(
                padding: EdgeInsets.only(right: 16.w),
                child: CircleAvatar(
                  radius: 18.r,
                  backgroundImage: NetworkImage(
                    ImagePlaceholders.userAvatarWithFallback(
                      user?.githubAvatarUrl,
                      user?.githubUsername,
                    ),
                  ),
                ),
              ),
            );
          }),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: controller.refresh,
        child: Obx(() {
          if (controller.isLoading.value && controller.projects.isEmpty) {
            return const Center(child: CircularProgressIndicator());
          }

          if (controller.errorMessage.value != null &&
              controller.projects.isEmpty) {
            return _buildErrorState(controller);
          }

          if (controller.projects.isEmpty) {
            return _buildEmptyState();
          }

          return _buildProjectsList(controller);
        }),
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => Get.toNamed(AppRoutes.createProject),
        backgroundColor: AppColors.primary,
        icon: Icon(Icons.add, size: 20.r),
        label: Text(
          AppStrings.newProject,
          style: GoogleFonts.inter(fontWeight: FontWeight.w600),
        ),
      ),
    );
  }

  Widget _buildProjectsList(ProjectsController controller) {
    return ListView.builder(
      padding: EdgeInsets.all(16.r),
      itemCount: controller.projects.length,
      itemBuilder: (context, index) {
        final project = controller.projects[index];
        return Padding(
          padding: EdgeInsets.only(bottom: 12.h),
          child: ProjectCard(
            project: project,
            onTap: () => controller.openEditor(project),
            onDelete: () => controller.confirmDeleteProject(project),
          ),
        );
      },
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Padding(
        padding: EdgeInsets.all(32.r),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Image.network(
              ImagePlaceholders.emptyState,
              width: 200.w,
              height: 150.h,
              fit: BoxFit.cover,
              errorBuilder: (_, __, ___) => Icon(
                Icons.folder_open,
                size: 80.r,
                color: AppColors.textTertiary,
              ),
            ),
            SizedBox(height: 24.h),
            Text(
              AppStrings.noProjects,
              style: GoogleFonts.inter(
                fontSize: 20.sp,
                fontWeight: FontWeight.w600,
                color: AppColors.textPrimary,
              ),
            ),
            SizedBox(height: 8.h),
            Text(
              AppStrings.noProjectsSubtitle,
              style: GoogleFonts.inter(
                fontSize: 14.sp,
                color: AppColors.textSecondary,
              ),
              textAlign: TextAlign.center,
            ),
            SizedBox(height: 32.h),
            ElevatedButton.icon(
              onPressed: () => Get.toNamed(AppRoutes.createProject),
              icon: Icon(Icons.add, size: 20.r),
              label: Text(AppStrings.createProject),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildErrorState(ProjectsController controller) {
    return Center(
      child: Padding(
        padding: EdgeInsets.all(32.r),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.error_outline,
              size: 64.r,
              color: AppColors.error,
            ),
            SizedBox(height: 16.h),
            Text(
              AppStrings.somethingWentWrong,
              style: GoogleFonts.inter(
                fontSize: 18.sp,
                fontWeight: FontWeight.w600,
                color: AppColors.textPrimary,
              ),
            ),
            SizedBox(height: 8.h),
            Text(
              controller.errorMessage.value ?? '',
              style: GoogleFonts.inter(
                fontSize: 14.sp,
                color: AppColors.textSecondary,
              ),
              textAlign: TextAlign.center,
            ),
            SizedBox(height: 24.h),
            ElevatedButton(
              onPressed: controller.loadProjects,
              child: Text(AppStrings.tryAgain),
            ),
          ],
        ),
      ),
    );
  }
}
