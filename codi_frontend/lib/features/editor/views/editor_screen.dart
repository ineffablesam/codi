/// Editor screen with preview and chat panels
library;

import 'package:flutter/material.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:get/get.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../../core/constants/app_colors.dart';
import '../controllers/editor_controller.dart';
import '../widgets/agent_chat_panel.dart';
import '../widgets/preview_panel.dart';

/// Main editor screen with preview and agent chat
class EditorScreen extends StatelessWidget {
  const EditorScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final controller = Get.find<EditorController>();
    final isLandscape =
        MediaQuery.of(context).orientation == Orientation.landscape;

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: _buildAppBar(controller),
      body: Obx(() {
        if (controller.isLoading.value) {
          return const Center(child: CircularProgressIndicator());
        }

        if (controller.errorMessage.value != null) {
          return _buildErrorState(controller);
        }

        if (controller.currentProject.value == null) {
          return const Center(child: Text('No project loaded'));
        }

        if (isLandscape) {
          return _buildLandscapeLayout();
        }
        return _buildPortraitLayout();
      }),
    );
  }

  PreferredSizeWidget _buildAppBar(EditorController controller) {
    return AppBar(
      title: Obx(() => Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                controller.currentProject.value?.name ?? 'Editor',
                style: GoogleFonts.inter(
                  fontSize: 16.sp,
                  fontWeight: FontWeight.w600,
                ),
              ),
              Obx(() {
                if (controller.isAgentWorking.value) {
                  return Row(
                    children: [
                      SizedBox(
                        width: 10.r,
                        height: 10.r,
                        child: const CircularProgressIndicator(
                          strokeWidth: 2,
                          valueColor: AlwaysStoppedAnimation(AppColors.primary),
                        ),
                      ),
                      SizedBox(width: 6.w),
                      Text(
                        'Working...',
                        style: GoogleFonts.inter(
                          fontSize: 11.sp,
                          color: AppColors.primary,
                        ),
                      ),
                    ],
                  );
                }
                return const SizedBox.shrink();
              }),
            ],
          )),
      actions: [
        // Build progress indicator
        Obx(() {
          if (controller.buildProgress.value > 0 &&
              controller.buildProgress.value < 1.0) {
            return Container(
              margin: EdgeInsets.symmetric(horizontal: 8.w),
              padding: EdgeInsets.symmetric(horizontal: 12.w, vertical: 6.h),
              decoration: BoxDecoration(
                color: AppColors.info.withOpacity(0.1),
                borderRadius: BorderRadius.circular(16.r),
              ),
              child: Row(
                children: [
                  SizedBox(
                    width: 12.r,
                    height: 12.r,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      value: controller.buildProgress.value,
                      valueColor:
                          const AlwaysStoppedAnimation(AppColors.info),
                    ),
                  ),
                  SizedBox(width: 6.w),
                  Text(
                    '${(controller.buildProgress.value * 100).toInt()}%',
                    style: GoogleFonts.inter(
                      fontSize: 12.sp,
                      fontWeight: FontWeight.w600,
                      color: AppColors.info,
                    ),
                  ),
                ],
              ),
            );
          }
          return const SizedBox.shrink();
        }),
        PopupMenuButton(
          icon: const Icon(Icons.more_vert),
          itemBuilder: (context) => [
            const PopupMenuItem(
              value: 'refresh',
              child: Row(
                children: [
                  Icon(Icons.refresh),
                  SizedBox(width: 8),
                  Text('Refresh'),
                ],
              ),
            ),
            const PopupMenuItem(
              value: 'github',
              child: Row(
                children: [
                  Icon(Icons.code),
                  SizedBox(width: 8),
                  Text('Open GitHub'),
                ],
              ),
            ),
          ],
          onSelected: (value) {
            if (value == 'refresh') {
              controller.refresh();
            } else if (value == 'github') {
              // Open GitHub
            }
          },
        ),
      ],
    );
  }

  Widget _buildPortraitLayout() {
    return Column(
      children: [
        // Preview panel (top half)
        Expanded(
          flex: 4,
          child: Container(
            decoration: BoxDecoration(
              border: Border(
                bottom: BorderSide(color: AppColors.border),
              ),
            ),
            child: const PreviewPanel(),
          ),
        ),
        // Agent chat panel (bottom half)
        const Expanded(
          flex: 6,
          child: AgentChatPanel(),
        ),
      ],
    );
  }

  Widget _buildLandscapeLayout() {
    return Row(
      children: [
        // Preview panel (left)
        Expanded(
          flex: 5,
          child: Container(
            decoration: BoxDecoration(
              border: Border(
                right: BorderSide(color: AppColors.border),
              ),
            ),
            child: const PreviewPanel(),
          ),
        ),
        // Agent chat panel (right)
        const Expanded(
          flex: 5,
          child: AgentChatPanel(),
        ),
      ],
    );
  }

  Widget _buildErrorState(EditorController controller) {
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
              controller.errorMessage.value ?? 'Something went wrong',
              style: GoogleFonts.inter(
                fontSize: 16.sp,
                color: AppColors.textPrimary,
              ),
              textAlign: TextAlign.center,
            ),
            SizedBox(height: 24.h),
            ElevatedButton(
              onPressed: () => Get.back(),
              child: const Text('Go Back'),
            ),
          ],
        ),
      ),
    );
  }
}
