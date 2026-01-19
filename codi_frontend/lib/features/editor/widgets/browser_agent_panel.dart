/// Browser agent panel widget
library;

import 'package:flutter/material.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:get/get.dart';
import 'package:radix_icons/radix_icons.dart';

import '../../../core/constants/app_colors.dart';
import '../../../core/utils/sf_font.dart';
import '../controllers/browser_agent_controller.dart';

/// Panel displaying the browser agent stream and placeholder state
class BrowserAgentPanel extends GetView<BrowserAgentController> {
  const BrowserAgentPanel({super.key});

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        Container(
          color: Get.theme.scaffoldBackgroundColor,
          child: Column(
            children: [
              // URL bar
              _buildUrlBar(),

              // Browser viewport
              Expanded(
                child: Obx(() {
                  if (controller.isLoading.value &&
                      controller.currentFrame.value == null) {
                    return _buildLoadingState();
                  }

                  if (controller.currentFrame.value == null) {
                    return _buildPlaceholder();
                  }

                  return _buildBrowserView();
                }),
              ),
            ],
          ),
        ),

        // Debug Overlay - Always visible
        Positioned(
          top: 60, // Below URL bar
          right: 8,
          child: Obx(() => Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: Colors.black.withOpacity(0.6),
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Text(
                      'FPS: ${controller.fps.value.toStringAsFixed(1)}',
                      style: const TextStyle(color: Colors.green, fontSize: 10),
                    ),
                    Text(
                      'Frames: ${controller.frameCount.value}',
                      style: const TextStyle(color: Colors.white, fontSize: 10),
                    ),
                    Text(
                      'Size: ${(controller.lastFrameSize.value / 1024).toStringAsFixed(1)} KB',
                      style: const TextStyle(color: Colors.white, fontSize: 10),
                    ),
                    if (controller.errorCount.value > 0)
                      Text(
                        'Errors: ${controller.errorCount.value}',
                        style: const TextStyle(color: Colors.red, fontSize: 10),
                      ),
                    if (controller.lastError.value != null)
                      Text(
                        'Last Err: ${controller.lastError.value}',
                        style: const TextStyle(color: Colors.red, fontSize: 10),
                      ),
                  ],
                ),
              )),
        ),
      ],
    );
  }

  /// URL bar at the top
  Widget _buildUrlBar() {
    return Container(
      padding: EdgeInsets.symmetric(horizontal: 12.w, vertical: 8.h),
      decoration: BoxDecoration(
        color: Get.theme.cardColor,
        border: Border(
          bottom: BorderSide(color: Get.theme.dividerColor, width: 1),
        ),
      ),
      child: Row(
        children: [
          // Globe icon
          Container(
            padding: EdgeInsets.all(6.r),
            decoration: BoxDecoration(
              color: AppColors.primary.withOpacity(0.1),
              borderRadius: BorderRadius.circular(6.r),
            ),
            child: Icon(
              RadixIcons.Globe,
              size: 14.sp,
              color: AppColors.primary,
            ),
          ),
          SizedBox(width: 8.w),

          // URL text
          Expanded(
            child: Obx(() => Container(
                  padding:
                      EdgeInsets.symmetric(horizontal: 12.w, vertical: 6.h),
                  decoration: BoxDecoration(
                    color: Get.theme.scaffoldBackgroundColor,
                    borderRadius: BorderRadius.circular(8.r),
                  ),
                  child: Text(
                    controller.currentUrl.value,
                    style: SFPro.regular(
                      fontSize: 12.sp,
                      color: Colors.grey.shade400,
                    ),
                    overflow: TextOverflow.ellipsis,
                  ),
                )),
          ),

          // Status indicator
          Obx(() => controller.isSessionActive.value
              ? Container(
                  padding: EdgeInsets.all(6.r),
                  child: Icon(
                    Icons.circle,
                    size: 8.sp,
                    color: AppColors.success,
                  ),
                )
              : const SizedBox.shrink()),

          SizedBox(width: 8.w),

          // Viewport Toggle
          Obx(() {
            if (!controller.isSessionActive.value)
              return const SizedBox.shrink();

            return Container(
              height: 24.h,
              decoration: BoxDecoration(
                color: Get.theme.scaffoldBackgroundColor,
                borderRadius: BorderRadius.circular(4.r),
                border: Border.all(color: Get.theme.dividerColor),
              ),
              child: Row(
                children: [
                  _buildToggleItem(
                    icon: Icons.desktop_mac,
                    isActive: !controller.isMobile.value,
                    onTap: () {
                      if (controller.isMobile.value)
                        controller.toggleViewport();
                    },
                  ),
                  Container(width: 1, color: Get.theme.dividerColor),
                  _buildToggleItem(
                    icon: Icons.phone_iphone,
                    isActive: controller.isMobile.value,
                    onTap: () {
                      if (!controller.isMobile.value)
                        controller.toggleViewport();
                    },
                  ),
                ],
              ),
            );
          }),
        ],
      ),
    );
  }

  Widget _buildToggleItem({
    required IconData icon,
    required bool isActive,
    required VoidCallback onTap,
  }) {
    return InkWell(
      onTap: onTap,
      child: Container(
        padding: EdgeInsets.symmetric(horizontal: 8.w),
        color: isActive ? AppColors.primary.withOpacity(0.1) : null,
        child: Center(
          child: Icon(
            icon,
            size: 14.sp,
            color: isActive ? AppColors.primary : Colors.grey.shade400,
          ),
        ),
      ),
    );
  }

  /// Browser viewport with the streamed image
  Widget _buildBrowserView() {
    return Stack(
      fit: StackFit.expand,
      children: [
        Positioned.fill(
          child: InteractiveViewer(
            minScale: 0.5,
            maxScale: 3.0,
            child: Listener(
              onPointerMove: (event) {
                controller.sendMouseEvent(
                  eventType: 'mousemove',
                  x: event.localPosition.dx,
                  y: event.localPosition.dy,
                );
              },
              onPointerDown: (event) {
                controller.sendMouseEvent(
                  eventType: 'mousedown',
                  x: event.localPosition.dx,
                  y: event.localPosition.dy,
                  button: event.buttons == 2 ? 'right' : 'left',
                );
              },
              onPointerUp: (event) {
                controller.sendMouseEvent(
                  eventType: 'mouseup',
                  x: event.localPosition.dx,
                  y: event.localPosition.dy,
                  button: event.buttons == 2 ? 'right' : 'left',
                );
              },
              child: Obx(() => RepaintBoundary(
                    child: Image.memory(
                      controller.currentFrame.value!,
                      fit: BoxFit.contain,
                      gaplessPlayback: true,
                      filterQuality: FilterQuality.medium,
                      errorBuilder: (context, error, stackTrace) {
                        return Container(
                          color: Colors.red.withOpacity(0.1),
                          padding: EdgeInsets.all(16.r),
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Icon(Icons.broken_image,
                                  color: Colors.red, size: 32.sp),
                              SizedBox(height: 8.h),
                              Text(
                                'Image Render Error:\n$error',
                                style: TextStyle(
                                    color: Colors.red, fontSize: 10.sp),
                                textAlign: TextAlign.center,
                              ),
                            ],
                          ),
                        );
                      },
                    ),
                  )),
            ),
          ),
        ),

        // Loading overlay when refreshing
        Obx(() => controller.isLoading.value
            ? Container(
                color: Colors.black.withOpacity(0.3),
                child: const Center(
                  child: CircularProgressIndicator(
                    valueColor: AlwaysStoppedAnimation(AppColors.primary),
                  ),
                ),
              )
            : const SizedBox.shrink()),
      ],
    );
  }

  /// Loading state while waiting for first frame
  Widget _buildLoadingState() {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const CircularProgressIndicator(
            valueColor: AlwaysStoppedAnimation(AppColors.primary),
          ),
          SizedBox(height: 16.h),
          Text(
            'Starting browser...',
            style: SFPro.medium(
              fontSize: 14.sp,
              color: Colors.grey.shade400,
            ),
          ),
        ],
      ),
    );
  }

  /// Placeholder when no browser session is active
  Widget _buildPlaceholder() {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // Browser icon
          Container(
            padding: EdgeInsets.all(24.r),
            decoration: BoxDecoration(
              color: AppColors.primary.withOpacity(0.1),
              shape: BoxShape.circle,
            ),
            child: Icon(
              RadixIcons.Globe,
              size: 48.sp,
              color: AppColors.primary.withOpacity(0.6),
            ),
          ),
          SizedBox(height: 24.h),

          // Title
          Text(
            'Browser Agent',
            style: SFPro.bold(
              fontSize: 20.sp,
              color: Get.textTheme.titleLarge?.color,
            ),
          ),
          SizedBox(height: 8.h),

          // Description
          Padding(
            padding: EdgeInsets.symmetric(horizontal: 48.w),
            child: Text(
              'Toggle browser mode in the chat panel and send a command to start browsing',
              style: SFPro.regular(
                fontSize: 14.sp,
                color: Colors.grey.shade500,
              ),
              textAlign: TextAlign.center,
            ),
          ),
          SizedBox(height: 32.h),

          // Instructions
          Container(
            padding: EdgeInsets.all(16.r),
            margin: EdgeInsets.symmetric(horizontal: 32.w),
            decoration: BoxDecoration(
              color: Get.theme.cardColor,
              borderRadius: BorderRadius.circular(12.r),
              border: Border.all(color: Get.theme.dividerColor),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _buildInstructionRow(
                  '1',
                  'Tap the globe icon in the chat input',
                ),
                SizedBox(height: 12.h),
                _buildInstructionRow(
                  '2',
                  'Type a command like "Go to google.com and search for Flutter tutorials"',
                ),
                SizedBox(height: 12.h),
                _buildInstructionRow(
                  '3',
                  'Watch the AI navigate the web for you',
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildInstructionRow(String number, String text) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          width: 24.r,
          height: 24.r,
          decoration: BoxDecoration(
            color: AppColors.primary.withOpacity(0.1),
            shape: BoxShape.circle,
          ),
          child: Center(
            child: Text(
              number,
              style: SFPro.medium(
                fontSize: 12.sp,
                color: AppColors.primary,
              ),
            ),
          ),
        ),
        SizedBox(width: 12.w),
        Expanded(
          child: Text(
            text,
            style: SFPro.regular(
              fontSize: 13.sp,
              color: Colors.grey.shade400,
            ),
          ),
        ),
      ],
    );
  }
}
