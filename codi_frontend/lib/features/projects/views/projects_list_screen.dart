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
      body: DefaultTabController(
        length: 2,
        child: Column(
          children: [
            TabBar(
              onTap: (index) {
                controller.loadProjects(status: index == 0 ? 'active' : 'archived');
              },
              tabs: const [
                Tab(text: 'Active'),
                Tab(text: 'Archived'),
              ],
              labelColor: AppColors.primary,
              unselectedLabelColor: AppColors.textSecondary,
              indicatorColor: AppColors.primary,
            ),
            Expanded(
              child: TabBarView(
                physics: const NeverScrollableScrollPhysics(), // Disable swipe to avoid accidental refetch
                children: [
                  // Active Projects
                  RefreshIndicator(
                    onRefresh: () => controller.loadProjects(status: 'active'),
                    child: Obx(() {
                      if (controller.isLoading.value && controller.projects.isEmpty) {
                        return const Center(child: CircularProgressIndicator());
                      }
                      if (controller.projects.isEmpty) {
                        return _buildEmptyState(false);
                      }
                      return _buildProjectsList(controller, false);
                    }),
                  ),
                  
                  // Archived Projects
                  RefreshIndicator(
                    onRefresh: () => controller.loadProjects(status: 'archived'),
                    child: Obx(() {
                      if (controller.isLoading.value && controller.projects.isEmpty) {
                        return const Center(child: CircularProgressIndicator());
                      }
                      if (controller.projects.isEmpty) {
                        return _buildEmptyState(true);
                      }
                      return _buildProjectsList(controller, true);
                    }),
                  ),
                ],
              ),
            ),
          ],
        ),
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

  Widget _buildProjectsList(ProjectsController controller, bool isArchived) {
    return ListView.builder(
      padding: EdgeInsets.all(16.r),
      itemCount: controller.projects.length,
      itemBuilder: (context, index) {
        final project = controller.projects[index];
        return Padding(
          padding: EdgeInsets.only(bottom: 12.h),
          child: ProjectCard(
            project: project,
            onTap: () {
               if (isArchived) {
                 controller.confirmRestoreProject(project);
               } else {
                 controller.openEditor(project);
               }
            },
            onArchive: () => controller.confirmArchiveProject(project),
            onRestore: () => controller.confirmRestoreProject(project),
            onDelete: () => controller.confirmDeleteProject(project),
          ),
        );
      },
    );
  }

  Widget _buildEmptyState(bool isArchived) {
    return Center(
      child: Padding(
        padding: EdgeInsets.all(32.r),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              isArchived ? Icons.archive_outlined : Icons.folder_open,
              size: 80.r,
              color: AppColors.textTertiary,
            ),
            SizedBox(height: 24.h),
            Text(
              isArchived ? 'No archived projects' : AppStrings.noProjects,
              style: GoogleFonts.inter(
                fontSize: 20.sp,
                fontWeight: FontWeight.w600,
                color: AppColors.textPrimary,
              ),
            ),
            SizedBox(height: 8.h),
            Text(
              isArchived 
                  ? 'Projects you archive will appear here'
                  : AppStrings.noProjectsSubtitle,
              style: GoogleFonts.inter(
                fontSize: 14.sp,
                color: AppColors.textSecondary,
              ),
              textAlign: TextAlign.center,
            ),
            if (!isArchived) ...[
              SizedBox(height: 32.h),
              ElevatedButton.icon(
                onPressed: () => Get.toNamed(AppRoutes.createProject),
                icon: Icon(Icons.add, size: 20.r),
                label: Text(AppStrings.createProject),
              ),
            ],
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
