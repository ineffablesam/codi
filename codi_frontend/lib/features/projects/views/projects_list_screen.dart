/// Projects list screen
library;

import 'dart:ui';

import 'package:codi_frontend/core/utils/sf_font.dart';
import 'package:flutter/material.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:get/get.dart';

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

    return DefaultTabController(
      length: 2,
      child: Scaffold(
        backgroundColor: Get.theme.scaffoldBackgroundColor,
        body: CustomScrollView(
          physics: const BouncingScrollPhysics(),
          slivers: [
            /// Sliver App Bar with background image
            SliverAppBar(
              stretch: false,
              pinned: true,
              expandedHeight: 95.h,
              collapsedHeight: 55.h,
              backgroundColor: Colors.black,
              flexibleSpace: FlexibleSpaceBar(
                background: Stack(
                  fit: StackFit.expand,
                  children: [
                    // Blob 1
                    Image.asset(
                      "assets/images/3.jpg",
                      fit: BoxFit.cover,
                    ),
                    // image overlay
                    Container(
                      color: Colors.black.withOpacity(0.5),
                    ),
                    Positioned.fill(
                      child: BackdropFilter(
                        filter: ImageFilter.blur(sigmaX: 20, sigmaY: 20),
                        child: Container(color: Colors.transparent),
                      ),
                    ),
                    Align(
                      alignment: Alignment.topLeft,
                      child: SafeArea(
                        child: Padding(
                          padding: EdgeInsets.only(
                              left: 28.w, bottom: 16.h, top: 16.h),
                          child: Text(
                            AppStrings.myProjects,
                            style: SFPro.font(
                              fontSize: 24.sp,
                              fontWeight: FontWeight.w700,
                              color: Colors.white,
                            ),
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              actions: [
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
              bottom: TabBar(
                onTap: (index) {
                  controller.loadProjects(
                    status: index == 0 ? 'active' : 'archived',
                  );
                },
                indicatorSize: TabBarIndicatorSize.tab,
                labelColor: Colors.white,
                unselectedLabelColor: Colors.white70,
                indicatorColor: Colors.white,
                tabs: const [
                  Tab(text: 'Active'),
                  Tab(text: 'Archived'),
                ],
              ),
            ),

            /// Tab views
            SliverFillRemaining(
              child: TabBarView(
                physics: const NeverScrollableScrollPhysics(),
                children: [
                  /// Active Projects
                  RefreshIndicator(
                    onRefresh: () => controller.loadProjects(status: 'active'),
                    child: Obx(() {
                      if (controller.isLoading.value &&
                          controller.projects.isEmpty) {
                        return const Center(
                          child: CircularProgressIndicator(),
                        );
                      }

                      if (controller.projects.isEmpty) {
                        return _buildEmptyState(false);
                      }

                      return _buildProjectsList(controller, false);
                    }),
                  ),

                  /// Archived Projects
                  RefreshIndicator(
                    onRefresh: () =>
                        controller.loadProjects(status: 'archived'),
                    child: Obx(() {
                      if (controller.isLoading.value &&
                          controller.projects.isEmpty) {
                        return const Center(
                          child: CircularProgressIndicator(),
                        );
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
              style: SFPro.font(
                fontSize: 20.sp,
                fontWeight: FontWeight.w600,
              ),
            ),
            SizedBox(height: 2.h),
            Text(
              isArchived
                  ? 'Projects you archive will appear here'
                  : AppStrings.noProjectsSubtitle,
              style: SFPro.font(
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
}
