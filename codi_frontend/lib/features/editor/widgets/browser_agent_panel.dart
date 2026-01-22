/// Browser agent panel widget
library;

import 'package:flutter/material.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:get/get.dart';
import 'package:radix_icons/radix_icons.dart';

import '../../../core/constants/app_colors.dart';
import '../../../core/utils/sf_font.dart';
import '../controllers/agent_chat_controller.dart';
import '../controllers/browser_agent_controller.dart';
import '../controllers/editor_controller.dart';

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

              // Keyboard input bar (only in interactive mode with active session)
              Obx(() => controller.isInteractiveMode.value &&
                      controller.isSessionActive.value
                  ? _buildKeyboardInputBar()
                  : const SizedBox.shrink()),
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
          // Navigation Buttons (only in interactive mode)
          Obx(() => controller.isInteractiveMode.value
              ? Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    _buildNavButton(
                      icon: Icons.arrow_back,
                      onTap: () => controller.goBack(),
                      tooltip: 'Back',
                    ),
                    SizedBox(width: 4.w),
                    _buildNavButton(
                      icon: Icons.arrow_forward,
                      onTap: () => controller.goForward(),
                      tooltip: 'Forward',
                    ),
                    SizedBox(width: 4.w),
                    _buildNavButton(
                      icon: Icons.refresh,
                      onTap: () => controller.refresh(),
                      tooltip: 'Refresh',
                    ),
                    SizedBox(width: 8.w),
                  ],
                )
              : const SizedBox.shrink()),

          // // Globe icon
          // Container(
          //   padding: EdgeInsets.all(6.r),
          //   decoration: BoxDecoration(
          //     color: AppColors.primary.withOpacity(0.1),
          //     borderRadius: BorderRadius.circular(6.r),
          //   ),
          //   child: Icon(
          //     RadixIcons.Globe,
          //     size: 14.sp,
          //     color: AppColors.primary,
          //   ),
          // ),
          // SizedBox(width: 8.w),

          // URL text input
          Expanded(
            child: Container(
              height: 28.h,
              padding: EdgeInsets.symmetric(horizontal: 12.w),
              decoration: BoxDecoration(
                color: Get.theme.scaffoldBackgroundColor,
                borderRadius: BorderRadius.circular(8.r),
              ),
              child: Row(
                children: [
                  Expanded(
                    child: Obx(() {
                      // Keep text field in sync with controller URL if not focused
                      // Note: A verified implementation would use a TextEditingController
                      // and listeners, but for now we use a simple approach
                      return TextField(
                        controller: TextEditingController(
                            text: controller.currentUrl.value)
                          ..selection = TextSelection.fromPosition(TextPosition(
                              offset: controller.currentUrl.value.length)),
                        style: SFPro.regular(
                          fontSize: 12.sp,
                          color: controller.isInteractiveMode.value
                              ? Get.textTheme.bodyMedium?.color
                              : Colors.grey.shade400,
                        ),
                        enabled: controller.isInteractiveMode.value,
                        decoration: InputDecoration(
                          border: InputBorder.none,
                          contentPadding: EdgeInsets.only(
                              bottom: 14.h), // Center vertically
                          hintText: 'Enter URL...',
                          isDense: true,
                        ),
                        onSubmitted: (value) => controller.navigateTo(value),
                      );
                    }),
                  ),
                  if (controller.isInteractiveMode.value) ...[
                    SizedBox(width: 8.w),
                    InkWell(
                      onTap: () {
                        // We can't easily get the text here without a persistent controller
                        // So we rely on the user hitting Enter for now, or we could refactor
                        // to use a stateful widget or keep controller in GetX controller.
                        // For now, let's just show the icon as an indicator that Enter works
                      },
                      child: Icon(
                        Icons.arrow_forward_ios,
                        size: 10.sp,
                        color: Colors.grey,
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ),

          // Status indicator / Interactive mode badge
          // Obx(() {
          //   if (!controller.isSessionActive.value) {
          //     return const SizedBox.shrink();
          //   }
          //
          //   if (controller.isInteractiveMode.value) {
          //     // Show interactive mode badge
          //     return Container(
          //       padding: EdgeInsets.symmetric(horizontal: 8.w, vertical: 4.h),
          //       decoration: BoxDecoration(
          //         color: Colors.blue.withOpacity(0.1),
          //         borderRadius: BorderRadius.circular(4.r),
          //         border: Border.all(color: Colors.blue.withOpacity(0.3)),
          //       ),
          //       child: Text(
          //         'Interactive',
          //         style: SFPro.medium(
          //           fontSize: 10.sp,
          //           color: Colors.blue,
          //         ),
          //       ),
          //     );
          //   }
          //
          //   // Default: green dot for AI mode
          //   return Container(
          //     padding: EdgeInsets.all(6.r),
          //     child: Icon(
          //       Icons.circle,
          //       size: 8.sp,
          //       color: AppColors.success,
          //     ),
          //   );
          // }),
          //
          // SizedBox(width: 8.w),

          // End Session button (when session is active)
          Obx(() => controller.isSessionActive.value
              ? InkWell(
                  onTap: () {
                    controller.clearSession();
                  },
                  borderRadius: BorderRadius.circular(4.r),
                  child: Container(
                    padding:
                        EdgeInsets.symmetric(horizontal: 8.w, vertical: 4.h),
                    decoration: BoxDecoration(
                      color: Colors.red.withOpacity(0.1),
                      borderRadius: BorderRadius.circular(4.r),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(
                          Icons.close,
                          size: 12.sp,
                          color: Colors.red,
                        ),
                        SizedBox(width: 4.w),
                        Text(
                          'End',
                          style: SFPro.medium(
                            fontSize: 10.sp,
                            color: Colors.red,
                          ),
                        ),
                      ],
                    ),
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
          child: LayoutBuilder(
            builder: (context, constraints) {
              final widgetSize =
                  Size(constraints.maxWidth, constraints.maxHeight);

              return InteractiveViewer(
                minScale: 0.5,
                maxScale: 3.0,
                child: Listener(
                  onPointerMove: (event) {
                    controller.sendMouseEvent(
                      eventType: 'mouseMoved',
                      x: event.localPosition.dx,
                      y: event.localPosition.dy,
                      widgetSize: widgetSize,
                    );
                  },
                  onPointerDown: (event) {
                    controller.sendMouseEvent(
                      eventType: 'mousePressed',
                      x: event.localPosition.dx,
                      y: event.localPosition.dy,
                      button: event.buttons == 2 ? 'right' : 'left',
                      widgetSize: widgetSize,
                    );
                  },
                  onPointerUp: (event) {
                    controller.sendMouseEvent(
                      eventType: 'mouseReleased',
                      x: event.localPosition.dx,
                      y: event.localPosition.dy,
                      button: event.buttons == 2 ? 'right' : 'left',
                      widgetSize: widgetSize,
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
              );
            },
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
              'Browse the web with AI assistance or take direct control',
              style: SFPro.regular(
                fontSize: 14.sp,
                color: Colors.grey.shade500,
              ),
              textAlign: TextAlign.center,
            ),
          ),
          SizedBox(height: 32.h),

          // Action buttons
          Padding(
            padding: EdgeInsets.symmetric(horizontal: 32.w),
            child: Row(
              children: [
                // Interactive Mode button
                Expanded(
                  child: _buildModeButton(
                    icon: Icons.mouse_outlined,
                    title: 'Interactive',
                    subtitle: 'Control browser directly',
                    color: Colors.blue,
                    onTap: () {
                      controller.startInteractiveSession();
                    },
                  ),
                ),
                SizedBox(width: 16.w),
                // Agent Mode button
                Expanded(
                  child: _buildModeButton(
                    icon: Icons.auto_fix_high,
                    title: 'AI Agent',
                    subtitle: 'Let AI browse for you',
                    color: AppColors.primary,
                    onTap: () {
                      // Get the AgentChatController and toggle browser mode
                      try {
                        final chatController = Get.find<AgentChatController>();
                        if (!chatController.isBrowserAgentMode.value) {
                          chatController.toggleBrowserAgentMode();
                        }
                        // Show chat panel
                        final editorController = Get.find<EditorController>();
                        editorController.isChatVisible.value = true;
                      } catch (e) {
                        // Controllers not found, fallback
                      }
                    },
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  /// Build a mode selection button
  Widget _buildModeButton({
    required IconData icon,
    required String title,
    required String subtitle,
    required Color color,
    required VoidCallback onTap,
  }) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(12.r),
      child: Container(
        padding: EdgeInsets.all(16.r),
        decoration: BoxDecoration(
          color: Get.theme.cardColor,
          borderRadius: BorderRadius.circular(12.r),
          border: Border.all(color: Get.theme.dividerColor),
        ),
        child: Column(
          children: [
            Container(
              padding: EdgeInsets.all(12.r),
              decoration: BoxDecoration(
                color: color.withOpacity(0.1),
                shape: BoxShape.circle,
              ),
              child: Icon(
                icon,
                size: 24.sp,
                color: color,
              ),
            ),
            SizedBox(height: 12.h),
            Text(
              title,
              style: SFPro.semibold(
                fontSize: 14.sp,
                color: Get.textTheme.bodyLarge?.color,
              ),
            ),
            SizedBox(height: 4.h),
            Text(
              subtitle,
              style: SFPro.regular(
                fontSize: 11.sp,
                color: Colors.grey.shade500,
              ),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }

  /// Keyboard input bar for interactive mode
  Widget _buildKeyboardInputBar() {
    return Container(
      padding: EdgeInsets.only(left: 12.w, right: 12.w, top: 8.h, bottom: 60.h),
      decoration: BoxDecoration(
        color: Get.theme.cardColor,
        border: Border(
          top: BorderSide(color: Get.theme.dividerColor, width: 1),
        ),
      ),
      child: Row(
        children: [
          // Interactive mode indicator
          Container(
            padding: EdgeInsets.symmetric(horizontal: 8.w, vertical: 4.h),
            decoration: BoxDecoration(
              color: Colors.blue.withOpacity(0.1),
              borderRadius: BorderRadius.circular(4.r),
              border: Border.all(color: Colors.blue.withOpacity(0.3)),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(
                  Icons.mouse_outlined,
                  size: 12.sp,
                  color: Colors.blue,
                ),
                SizedBox(width: 4.w),
                Text(
                  'Interactive',
                  style: SFPro.medium(
                    fontSize: 10.sp,
                    color: Colors.blue,
                  ),
                ),
              ],
            ),
          ),
          SizedBox(width: 8.w),

          // Text input field
          Expanded(
            child: Container(
              height: 36.h,
              decoration: BoxDecoration(
                color: Get.theme.scaffoldBackgroundColor,
                borderRadius: BorderRadius.circular(8.r),
              ),
              child: TextField(
                controller: controller.textInputController,
                style: SFPro.regular(
                  fontSize: 13.sp,
                  color: Get.textTheme.bodyMedium?.color,
                ),
                decoration: InputDecoration(
                  hintText: 'Type to send keyboard input...',
                  hintStyle: SFPro.regular(
                    fontSize: 13.sp,
                    color: Colors.grey.shade500,
                  ),
                  border: InputBorder.none,
                  contentPadding: EdgeInsets.symmetric(
                    horizontal: 12.w,
                    vertical: 8.h,
                  ),
                ),
                // Real-time typing - send each character as user types
                onChanged: (text) {
                  // Get the difference between old and new text
                  final oldText = controller.lastSentText.value;

                  if (text.length > oldText.length) {
                    // User typed new character(s)
                    final newChars = text.substring(oldText.length);
                    controller.sendTextInput(newChars);
                  } else if (text.length < oldText.length) {
                    // User deleted character(s)
                    final deleteCount = oldText.length - text.length;
                    for (var i = 0; i < deleteCount; i++) {
                      controller.sendSpecialKey('Backspace');
                    }
                  }

                  controller.lastSentText.value = text;
                },
                onSubmitted: (text) {
                  // Send Enter key when user presses Enter
                  controller.sendSpecialKey('Enter');
                  controller.textInputController.clear();
                  controller.lastSentText.value = '';
                },
              ),
            ),
          ),
          SizedBox(width: 8.w),

          // Special key buttons
          _buildKeyButton('Tab', () => controller.sendSpecialKey('Tab')),
          SizedBox(width: 4.w),
          _buildKeyButton('⌫', () {
            controller.sendSpecialKey('Backspace');
            // Also update local text field
            final currentText = controller.textInputController.text;
            if (currentText.isNotEmpty) {
              controller.textInputController.text =
                  currentText.substring(0, currentText.length - 1);
              controller.textInputController.selection =
                  TextSelection.fromPosition(
                TextPosition(
                    offset: controller.textInputController.text.length),
              );
              controller.lastSentText.value =
                  controller.textInputController.text;
            }
          }),
          SizedBox(width: 4.w),
          _buildKeyButton('↵', () {
            controller.sendSpecialKey('Enter');
            controller.textInputController.clear();
            controller.lastSentText.value = '';
          }),
        ],
      ),
    );
  }

  /// Build a special key button
  Widget _buildKeyButton(String label, VoidCallback onTap) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(4.r),
      child: Container(
        padding: EdgeInsets.symmetric(horizontal: 8.w, vertical: 6.h),
        decoration: BoxDecoration(
          color: Get.theme.scaffoldBackgroundColor,
          borderRadius: BorderRadius.circular(4.r),
          border: Border.all(color: Get.theme.dividerColor),
        ),
        child: Text(
          label,
          style: SFPro.medium(
            fontSize: 11.sp,
            color: Colors.grey.shade400,
          ),
        ),
      ),
    );
  }

  /// Build a navigation button
  Widget _buildNavButton({
    required IconData icon,
    required VoidCallback onTap,
    required String tooltip,
  }) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(4.r),
      child: Tooltip(
        message: tooltip,
        child: Container(
          padding: EdgeInsets.all(4.r),
          decoration: BoxDecoration(
            color: Get.theme.scaffoldBackgroundColor,
            borderRadius: BorderRadius.circular(4.r),
            border: Border.all(color: Get.theme.dividerColor),
          ),
          child: Icon(
            icon,
            size: 14.sp,
            color: Get.textTheme.bodyMedium?.color?.withOpacity(0.7),
          ),
        ),
      ),
    );
  }
}
