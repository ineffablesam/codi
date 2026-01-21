/// Editor screen with preview and chat panels
library;

import 'package:flex_switch/flex_switch.dart';
import 'package:flutter/material.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:get/get.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:iconsax_flutter/iconsax_flutter.dart';
import 'package:radix_icons/radix_icons.dart';

import '../../../core/constants/app_colors.dart';
import '../../../core/utils/sf_font.dart';
import '../../../shared/controller/ui_controller.dart';
import '../controllers/branch_controller.dart';
import '../controllers/commit_panel_controller.dart';
import '../controllers/editor_controller.dart';
import '../controllers/preview_controller.dart';
import '../widgets/agent_chat_panel.dart';
import '../widgets/branch_switcher_sheet.dart';
import '../widgets/browser_agent_panel.dart';
import '../widgets/code_editor_tab.dart';
import '../widgets/container_logs_sheet.dart';
import '../widgets/preview_panel.dart';

/// Main editor screen with preview and agent chat
class EditorScreen extends StatelessWidget {
  const EditorScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final controller = Get.find<EditorController>();
    final previewController = Get.find<PreviewController>();
    final size = MediaQuery.of(Get.context!).size;
    final ui = Get.find<UIController>();
    return Scaffold(
      backgroundColor: Get.theme.scaffoldBackgroundColor,
      body: SafeArea(
        bottom: false,
        child: CustomScrollView(
          physics: const NeverScrollableScrollPhysics(),
          slivers: [
            SliverAppBar(
              pinned: true,
              backgroundColor: Get.theme.scaffoldBackgroundColor,
              expandedHeight: 80.h,
              automaticallyImplyLeading: false,
              flexibleSpace: FlexibleSpaceBar(
                background: _buildAppBar(controller),
              ),
            ),
            SliverFillRemaining(
              child: Obx(() {
                if (controller.isLoading.value) {
                  return const Center(child: CircularProgressIndicator());
                }

                if (controller.errorMessage.value != null) {
                  return _buildErrorState(controller);
                }

                if (controller.currentProject.value == null) {
                  return const Center(child: Text('No project loaded'));
                }

                return Stack(
                  children: [
                    TabBarView(
                      controller: controller.tabController,
                      physics: const NeverScrollableScrollPhysics(),
                      children: [
                        // Preview Tab
                        _buildAgentTab(context),
                        // Code Editor Tab
                        const CodeEditorTab(),
                        // Browser Agent Tab
                        const BrowserAgentPanel(),
                      ],
                    ),
                    // Sliding Chat Panel from bottom
                    Obx(() => AnimatedSlide(
                          duration: const Duration(milliseconds: 300),
                          curve: Curves.easeInOut,
                          offset: controller.isChatVisible.value
                              ? const Offset(0, 0) // visible
                              : const Offset(0, 1), // hidden below
                          child: Container(
                            height: MediaQuery.of(context).size.height * 0.85,
                            margin: EdgeInsets.only(top: 80.h),
                            decoration: BoxDecoration(
                              color: Get.theme.cardTheme.color,
                              borderRadius: BorderRadius.vertical(
                                top: Radius.circular(24.r),
                              ),
                              boxShadow: [
                                BoxShadow(
                                  color: Colors.black.withOpacity(0.15),
                                  blurRadius: 20,
                                  offset: const Offset(0, -5),
                                ),
                              ],
                            ),
                            child: Column(
                              children: [
                                // Handle bar
                                GestureDetector(
                                  onTap: controller.toggleChat,
                                  child: Container(
                                    width: double.infinity,
                                    padding:
                                        EdgeInsets.symmetric(vertical: 12.h),
                                    child: Center(
                                      child: Container(
                                        width: 40.w,
                                        height: 4.h,
                                        decoration: BoxDecoration(
                                          color: Colors.grey.shade300,
                                          borderRadius:
                                              BorderRadius.circular(2.r),
                                        ),
                                      ),
                                    ),
                                  ),
                                ),
                                // Chat panel content
                                const Expanded(
                                  child: AgentChatPanel(),
                                ),
                              ],
                            ),
                          ),
                        )),
                    // Bottom navigation bar
                    Align(
                      alignment: Alignment.bottomCenter,
                      child: Padding(
                        padding: EdgeInsets.only(
                          left: 24.w,
                          right: 24.w,
                          bottom: 13.h, // account for safe area
                        ),
                        child: Row(
                          spacing: 5,
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          crossAxisAlignment: CrossAxisAlignment.center,
                          children: [
                            // Arrow button to toggle chat
                            GestureDetector(
                              onTap: controller.toggleChat,
                              child: Obx(() => AnimatedRotation(
                                    duration: const Duration(milliseconds: 300),
                                    turns: controller.isChatVisible.value
                                        ? 0.5
                                        : 0,
                                    child: Container(
                                      padding: EdgeInsets.all(8.w),
                                      decoration: BoxDecoration(
                                        color:
                                            Get.theme.scaffoldBackgroundColor,
                                        borderRadius:
                                            BorderRadius.circular(1250.r),
                                        border: Border.all(
                                            color: Colors.grey.shade800,
                                            width: 2.w),
                                      ),
                                      child: Icon(
                                        Icons.arrow_upward,
                                        color: Colors.white,
                                        size: 22.sp,
                                      ),
                                    ),
                                  )),
                            ),
                            Expanded(
                              child: FlexSwitch.fromEnum<EditorTab>(
                                style: FlexSwitchStyle(
                                  backgroundColor: Get.theme.focusColor,
                                  thumbColor: Get.theme.cardTheme.color,
                                  activeLabelColor: Colors.white,
                                  inactiveLabelColor: Colors.grey.shade400,
                                  borderRadius: ui.topLeft.value,
                                  thumbRadius: ui.topLeft.value,
                                  thumbPressScale: 0.95,
                                  padding: 4.w,
                                  itemPadding:
                                      EdgeInsets.symmetric(vertical: 4.w),
                                  gap: 8,
                                  shadow: [
                                    BoxShadow(
                                        blurRadius: 12, color: Colors.black26)
                                  ],
                                  duration: Duration(milliseconds: 150),
                                  curve: Curves.easeInOut,
                                  border: null,
                                  labelTextStyle: null,
                                  iconSize: null,
                                  focusRingWidth: 2,
                                  enableRipple: true,
                                  segmentOverlayColor: null,
                                  splashFactory: null,
                                  enableTrackHoverOverlay: true,
                                  segmentGutter: 6,
                                  layout: FlexSwitchLayout.equal,
                                ),
                                iconBuilder: (v) => switch (v) {
                                  EditorTab.preview => RadixIcons.Eye_Open,
                                  EditorTab.code => RadixIcons.CodeSandbox_Logo,
                                  EditorTab.browser => RadixIcons.Globe,
                                },
                                values: EditorTab.values,
                                selectedValue: controller.currentTab.value,
                                onChanged: controller.setTab,
                                thumbDragOnly: true,
                                dragCommitBehavior:
                                    DragCommitBehavior.onRelease,
                                labelBuilder: (v) => switch (v) {
                                  EditorTab.preview => 'Preview',
                                  EditorTab.code => 'Code',
                                  EditorTab.browser => 'Browser',
                                },
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ],
                );
              }),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildAppBar(EditorController controller,
      {BranchController? branchCtrl}) {
    return Container(
      decoration: BoxDecoration(
        color: Get.theme.cardTheme.color,
        // border: Border.all(
        //   color: Get.theme.dividerColor,
        //   width: 1,
        // ),
        borderRadius: BorderRadius.circular(8.r),
      ),
      child: Padding(
        padding: EdgeInsets.symmetric(horizontal: 16.w, vertical: 12.h),
        child: Row(
          children: [
            // Leading - Back button
            _buildIconButton(
              icon: Icons.arrow_back,
              onPressed: () => Get.back(),
            ),
            SizedBox(width: 12.w),

            // Title + subtitle area
            Expanded(
              child: Obx(() => Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(
                        controller.currentProject.value?.name ?? 'Editor',
                        style: SFPro.medium(
                          fontSize: 16.sp,
                          color: Get.textTheme.titleMedium?.color,
                        ),
                      ),
                      Obx(() {
                        if (controller.isAgentWorking.value) {
                          // Show working indicator
                          return Row(
                            children: [
                              SizedBox(
                                width: 10.r,
                                height: 10.r,
                                child: const CircularProgressIndicator(
                                  strokeWidth: 2,
                                  valueColor:
                                      AlwaysStoppedAnimation(AppColors.primary),
                                ),
                              ),
                              SizedBox(width: 6.w),
                              Text(
                                'Working...',
                                style: SFPro.regular(
                                  fontSize: 11.sp,
                                  color: AppColors.primary,
                                ),
                              ),
                            ],
                          );
                        }
                        // Show connection status when not working
                        return Row(
                          children: [
                            Container(
                              width: 8.r,
                              height: 8.r,
                              decoration: BoxDecoration(
                                shape: BoxShape.circle,
                                color: controller.isConnected.value
                                    ? AppColors.success
                                    : Colors.grey,
                              ),
                            ),
                            SizedBox(width: 6.w),
                            Text(
                              controller.isConnected.value
                                  ? 'Connected'
                                  : 'Offline',
                              style: SFPro.regular(
                                fontSize: 11.sp,
                                color: controller.isConnected.value
                                    ? AppColors.success
                                    : Colors.grey,
                              ),
                            ),
                          ],
                        );
                      }),
                    ],
                  )),
            ),

            // Trailing buttons
            Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                // Commit badge
                Obx(() {
                  if (Get.isRegistered<CommitPanelController>()) {
                    final commitController = Get.find<CommitPanelController>();
                    if (commitController.modifiedFiles.isNotEmpty) {
                      return _buildIconButton(
                        icon: Icons.commit,
                        onPressed: () {
                          controller.setTab(EditorTab.preview);
                          commitController.isExpanded.value = true;
                        },
                        badge: commitController.modifiedFiles.length,
                      );
                    }
                  }
                  return const SizedBox.shrink();
                }),

                // Build progress indicator
                Obx(() {
                  if (controller.buildProgress.value > 0 &&
                      controller.buildProgress.value < 1.0) {
                    return Container(
                      margin: EdgeInsets.symmetric(horizontal: 8.w),
                      padding:
                          EdgeInsets.symmetric(horizontal: 12.w, vertical: 6.h),
                      decoration: BoxDecoration(
                        color: AppColors.info.withOpacity(0.1),
                        borderRadius: BorderRadius.circular(16.r),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
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
                            style: SFPro.medium(
                              fontSize: 12.sp,
                              color: AppColors.info,
                            ),
                          ),
                        ],
                      ),
                    );
                  }
                  return const SizedBox.shrink();
                }),

                SizedBox(width: 8.w),

                // Branch switcher button
                _buildOutlineButton(
                  onPressed: () => BranchSwitcherSheet.show(
                    Get.context!,
                    onBranchSelected: (branch, {createPreview = false}) async {
                      if (createPreview) {
                        final previewCtrl = Get.find<PreviewController>();
                        await previewCtrl.createDeployment(
                            branch: branch, isPreview: true);
                      }
                    },
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const Icon(Iconsax.code_circle, size: 18),
                      if (branchCtrl != null) ...[
                        SizedBox(width: 4.w),
                        Text(
                          branchCtrl.currentBranch.value,
                          style: SFPro.medium(fontSize: 11.sp),
                        ),
                      ],
                    ],
                  ),
                ),

                SizedBox(width: 8.w),

                // More menu
                _buildPopupMenu(controller),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildIconButton({
    required IconData icon,
    required VoidCallback onPressed,
    int? badge,
  }) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onPressed,
        borderRadius: BorderRadius.circular(8.r),
        child: Container(
          padding: EdgeInsets.all(8.r),
          decoration: BoxDecoration(
            // border: Border.all(color: Get.theme.dividerColor),
            color: Get.theme.focusColor,
            borderRadius: BorderRadius.circular(8.r),
          ),
          child: badge != null
              ? Badge(
                  label: Text('$badge'),
                  child: Icon(icon, size: 20.sp),
                )
              : Icon(icon, size: 20.sp),
        ),
      ),
    );
  }

  Widget _buildOutlineButton({
    required VoidCallback onPressed,
    required Widget child,
  }) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onPressed,
        borderRadius: BorderRadius.circular(8.r),
        child: Container(
          padding: EdgeInsets.symmetric(horizontal: 12.w, vertical: 8.h),
          decoration: BoxDecoration(
            border: Border.all(color: Get.theme.dividerColor),
            borderRadius: BorderRadius.circular(8.r),
          ),
          child: child,
        ),
      ),
    );
  }

  Widget _buildPopupMenu(EditorController controller) {
    return Container(
      decoration: BoxDecoration(
        border: Border.all(color: Get.theme.dividerColor),
        borderRadius: BorderRadius.circular(8.r),
      ),
      child: PopupMenuButton(
        icon: Icon(Icons.more_vert, size: 20.sp),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(8.r),
        ),
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
            value: 'branches',
            child: Row(
              children: [
                Icon(Iconsax.code_circle),
                SizedBox(width: 8),
                Text('Branches'),
              ],
            ),
          ),
          const PopupMenuItem(
            value: 'logs',
            child: Row(
              children: [
                Icon(Iconsax.monitor),
                SizedBox(width: 8),
                Text('Container Logs'),
              ],
            ),
          ),
          const PopupMenuItem(
            value: 'deploy',
            child: Row(
              children: [
                Icon(Iconsax.cloud_add),
                SizedBox(width: 8),
                Text('Deploy'),
              ],
            ),
          ),
          const PopupMenuItem(
            value: 'redeploy',
            child: Row(
              children: [
                Icon(Iconsax.refresh_circle),
                SizedBox(width: 8),
                Text('Redeploy'),
              ],
            ),
          ),
        ],
        onSelected: (value) async {
          final previewCtrl = Get.find<PreviewController>();
          switch (value) {
            case 'refresh':
              controller.refresh();
              break;
            case 'branches':
              BranchSwitcherSheet.show(Get.context!);
              break;
            case 'logs':
              if (previewCtrl.containerId.value != null) {
                ContainerLogsSheet.show(
                  Get.context!,
                  containerId: previewCtrl.containerId.value!,
                  containerName: controller.currentProject.value?.name,
                );
              } else {
                Get.snackbar('No Container', 'Deploy first to view logs');
              }
              break;
            case 'deploy':
              await previewCtrl.createDeployment();
              break;
            case 'redeploy':
              await previewCtrl.redeploy();
              break;
          }
        },
      ),
    );
  }

  Widget _buildAgentTab(BuildContext context) {
    return const Column(
      children: [
        // Preview panel (top half)
        Expanded(
          child: PreviewPanel(),
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
