/// Editor screen with preview and chat panels
library;

import 'package:flex_switch/flex_switch.dart';
import 'package:flutter/material.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:get/get.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:radix_icons/radix_icons.dart';
import 'package:shadcn_flutter/shadcn_flutter.dart' as shadcn;

import '../../../core/constants/app_colors.dart';
import '../../../core/utils/sf_font.dart';
import '../controllers/commit_panel_controller.dart';
import '../controllers/editor_controller.dart';
import '../controllers/preview_controller.dart';
import '../widgets/agent_chat_panel.dart';
import '../widgets/code_editor_tab.dart';
import '../widgets/preview_panel.dart';

/// Main editor screen with preview and agent chat
class EditorScreen extends StatelessWidget {
  const EditorScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final controller = Get.find<EditorController>();
    final previewController = Get.find<PreviewController>();
    return Scaffold(
      backgroundColor: AppColors.background,
      // appBar: _buildAppBar(controller),
      body: SafeArea(
        child: CustomScrollView(
          physics: const NeverScrollableScrollPhysics(),
          slivers: [
            SliverAppBar(
              pinned: true,
              backgroundColor: AppColors.background,
              expandedHeight: 80.h,
              automaticallyImplyLeading: false,
              flexibleSpace: FlexibleSpaceBar(
                background: _buildAppBar(controller),
              ),
            ),
            shadcn.SliverFillRemaining(
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
                        // Agent Tab (existing layout)
                        _buildAgentTab(context),
                        // Code Editor Tab (new)
                        const CodeEditorTab(),
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
                              color: Colors.white,
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
                                    padding: EdgeInsets.symmetric(vertical: 12.h),
                                    child: Center(
                                      child: Container(
                                        width: 40.w,
                                        height: 4.h,
                                        decoration: BoxDecoration(
                                          color: Colors.grey.shade300,
                                          borderRadius: BorderRadius.circular(2.r),
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
                        padding: EdgeInsets.symmetric(
                          horizontal: 24.w,
                        ),
                        child: Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          crossAxisAlignment: CrossAxisAlignment.center,
                          children: [
                            // Arrow button to toggle chat
                            GestureDetector(
                              onTap: controller.toggleChat,
                              child: AnimatedSlide(
                                // webview scroll based animation
                                duration: const Duration(milliseconds: 100),
                                offset: previewController.isScrollingDown.value
                                    ? const Offset(0, 1) // hide
                                    : const Offset(0, 0), // show
                                child: Obx(() => AnimatedRotation(
                                      duration: const Duration(milliseconds: 300),
                                      turns: controller.isChatVisible.value ? 0.5 : 0,
                                      child: Container(
                                        padding: EdgeInsets.all(12.w),
                                        decoration: BoxDecoration(
                                          color: Colors.grey.shade900,
                                          borderRadius: BorderRadius.circular(18.r),
                                          border: Border.all(
                                              color: Colors.grey.shade800, width: 2.w),
                                        ),
                                        child: Icon(
                                          Icons.arrow_upward,
                                          color: Colors.white,
                                          size: 22.sp,
                                        ),
                                      ),
                                    )),
                              ),
                            ),
                            FlexSwitch.fromEnum<EditorTab>(
                              style: FlexSwitchStyle(
                                backgroundColor: Colors.grey.shade900,
                                thumbColor: Colors.grey.shade800,
                                activeLabelColor: Colors.white,
                                inactiveLabelColor: Colors.grey.shade400,
                                borderRadius: 16,
                                thumbRadius: 12,
                                thumbPressScale: 0.95,
                                // scale thumb while pressed (1.0 to disable)
                                padding: 6,
                                itemPadding: EdgeInsets.symmetric(vertical: 8),
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
                                // computed from height if null
                                focusRingWidth: 2,
                                enableRipple: true,
                                segmentOverlayColor: null,
                                splashFactory: null,
                                enableTrackHoverOverlay: true,
                                segmentGutter: 6,
                                // interior gap; outer edges keep the track padding
                                layout: FlexSwitchLayout
                                    .equal, // default layout; can also come from FlexSwitchTheme
                              ),
                              iconBuilder: (v) => switch (v) {
                                EditorTab.preview => RadixIcons.Eye_Open,
                                EditorTab.code => RadixIcons.CodeSandbox_Logo,
                              },
                              values: EditorTab.values,
                              selectedValue: controller.currentTab.value,
                              onChanged: controller.setTab,
                              thumbDragOnly: true,
                              dragCommitBehavior: DragCommitBehavior.immediate,
                              labelBuilder: (v) => switch (v) {
                                EditorTab.preview => 'Preview',
                                EditorTab.code => 'Code Editor',
                              },
                            ),
                          ],
                        ),
                      ),
                    ),
                  ],
                );
              }),
            )
          ],
        ),
      ),
    );
  }

  Widget _buildAppBar(EditorController controller) {
    return shadcn.OutlinedContainer(
      clipBehavior: Clip.antiAlias,
      child: shadcn.AppBar(
        // Title + subtitle area with reactive updates
        title: Obx(() => Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  controller.currentProject.value?.name ?? 'Editor',
                  style: SFPro.medium(
                    fontSize: 16.sp,
                    color: Colors.black,
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
                  return const SizedBox.shrink();
                }),
              ],
            )),
        subtitle: const SizedBox.shrink(), // optional, not required
        // Leading buttons (left)
        leading: [
          shadcn.OutlineButton(
            density: shadcn.ButtonDensity.icon,
            onPressed: () {
              Get.back();
            },
            child: const Icon(Icons.arrow_back),
          ),
        ],
        // Trailing buttons (right)
        trailing: [
          // Commit badge
          Obx(() {
            if (Get.isRegistered<CommitPanelController>()) {
              final commitController = Get.find<CommitPanelController>();
              if (commitController.modifiedFiles.isNotEmpty) {
                return shadcn.OutlineButton(
                  density: shadcn.ButtonDensity.icon,
                  onPressed: () {
                    controller.setTab(EditorTab.preview);
                    commitController.isExpanded.value = true;
                  },
                  child: Badge(
                    label: Text('${commitController.modifiedFiles.length}'),
                    child: const Icon(Icons.commit),
                  ),
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
          // Popup menu
          shadcn.OutlineButton(
            density: shadcn.ButtonDensity.icon,
            onPressed: () {},
            child: PopupMenuButton(
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
                  // open GitHub
                }
              },
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildAgentTab(BuildContext context) {
    return Column(
      children: [
        // Preview panel (top half)
        Expanded(
          // flex: 5,
          child: const PreviewPanel(),
        ),
        // Agent chat panel (bottom half)
        // const Expanded(
        //   flex: 6,
        //   child: AgentChatPanel(),
        // ),
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
