/// Preview panel widget with WebView
library;

import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_inappwebview/flutter_inappwebview.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:get/get.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../../core/constants/app_colors.dart';
import '../../../core/constants/app_strings.dart';
import '../../../core/constants/image_placeholders.dart';
import '../controllers/preview_controller.dart';

/// Embedded WebView preview panel using InAppWebView
class PreviewPanel extends StatelessWidget {
  const PreviewPanel({super.key});

  @override
  Widget build(BuildContext context) {
    final controller = Get.find<PreviewController>();

    return Obx(() {
      // Show build phase UI if building
      if (controller.isBuilding.value) {
        return _buildPhaseUI(controller);
      }

      // No preview URL yet - show initial state
      if (controller.deploymentUrl.value == null ||
          controller.deploymentUrl.value!.isEmpty) {
        return _buildNoPreviewState();
      }

      // Error loading preview
      if (controller.hasError.value) {
        return _buildErrorState(controller);
      }

      return Stack(
        children: [
          Column(
            children: [
              _buildPreviewControls(controller),
              Expanded(
                child: Stack(
                  fit: StackFit.expand,
                  children: [
                    // InAppWebView
                    InAppWebView(
                      initialSettings: InAppWebViewSettings(
                        javaScriptEnabled: true,
                        useOnDownloadStart: true,
                        useOnLoadResource: true,
                        useWideViewPort: true,
                        loadWithOverviewMode: true,
                        supportZoom: true,
                        builtInZoomControls: true,
                        displayZoomControls: false,
                        transparentBackground: true,
                      ),
                      pullToRefreshController:
                          controller.pullToRefreshController,
                      onWebViewCreated: (webController) {
                        controller.onWebViewCreated(webController);
                      },
                      onLoadStart: (webController, url) {
                        controller.onLoadStart(url);
                      },
                      onLoadStop: (webController, url) {
                        controller.onLoadStop(url);
                      },
                      onScrollChanged: (controller, x, y) {
                        Get.find<PreviewController>().onScrollChanged(x, y);
                      },
                      onProgressChanged: (webController, progress) {
                        controller.onProgressChanged(progress);
                      },
                      onReceivedError: (webController, request, error) {
                        controller.onLoadError(
                          request.url,
                          error.type.toNativeValue() as int,
                          error.description,
                        );
                      },
                    ),

                    // Top linear progress bar (modern loading feel)
                    if (controller.isLoading.value &&
                        !controller.isBuilding.value)
                      Positioned(
                        top: 0,
                        left: 0,
                        right: 0,
                        child: LinearProgressIndicator(
                          value: controller.loadProgress.value / 100,
                          backgroundColor: Colors.transparent,
                          valueColor: AlwaysStoppedAnimation<Color>(
                            AppColors.primary.withOpacity(0.8),
                          ),
                          minHeight: 3.h,
                        ),
                      ),

                    // Centered loading overlay (only shown for initial/slow loads)
                    if (controller.isLoading.value &&
                        !controller.isBuilding.value &&
                        controller.loadProgress.value < 20)
                      Container(
                        color: Colors.black.withOpacity(0.35), // dark overlay
                        child: BackdropFilter(
                          filter: ImageFilter.blur(sigmaX: 8, sigmaY: 8),
                          child: Center(
                            child: const CircularProgressIndicator(
                              strokeWidth: 2.5,
                              valueColor: AlwaysStoppedAnimation<Color>(
                                Colors.white,
                              ),
                            ),
                          ),
                        ),
                      ),
                  ],
                ),
              ),
            ],
          ),
        ],
      );
    });
  }

  /// Build phase-specific UI (Initial Deploy, AI Building, Live Updates)
  Widget _buildPhaseUI(PreviewController controller) {
    return Obx(() {
      final phase = controller.buildPhase.value;
      
      switch (phase) {
        case BuildPhase.initialDeploy:
          return _buildInitialDeployUI(controller);
        case BuildPhase.aiBuilding:
          return _buildAIBuildingUI(controller);
        case BuildPhase.liveUpdates:
          return _buildLiveUpdatesUI(controller);
        default:
          return _buildInitialDeployUI(controller);
      }
    });
  }

  /// Phase 1: Initial Deploy UI
  Widget _buildInitialDeployUI(PreviewController controller) {
    return Container(
      color: Get.theme.scaffoldBackgroundColor,
      child: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            // Animated loading indicator
            SizedBox(
              width: 60.w,
              height: 60.w,
              child: CircularProgressIndicator(
                strokeWidth: 3,
                valueColor:
                    const AlwaysStoppedAnimation<Color>(AppColors.primary),
              ),
            ),
            SizedBox(height: 32.h),
            // Title
            Text(
              'Initial Deployment',
              style: GoogleFonts.inter(
                fontSize: 20.sp,
                fontWeight: FontWeight.w600,
                color: AppColors.textPrimary,
              ),
            ),
            SizedBox(height: 12.h),
            // Stage message
            Obx(() => Text(
                  controller.buildStage.value.isNotEmpty
                      ? controller.buildStage.value
                      : 'Setting up your development environment...',
                  style: GoogleFonts.inter(
                    fontSize: 14.sp,
                    color: AppColors.textSecondary,
                  ),
                  textAlign: TextAlign.center,
                )),
            SizedBox(height: 32.h),
            // Progress bar
            Obx(() => SizedBox(
                  width: 200.w,
                  child: LinearProgressIndicator(
                    value: controller.buildProgress.value > 0
                        ? controller.buildProgress.value
                        : null,
                    backgroundColor: AppColors.surfaceDark,
                    valueColor:
                        const AlwaysStoppedAnimation<Color>(AppColors.primary),
                  ),
                )),
          ],
        ),
      ),
    );
  }

  /// Phase 2: AI Building UI
  Widget _buildAIBuildingUI(PreviewController controller) {
    return Container(
      color: Get.theme.scaffoldBackgroundColor,
      child: Center(
        child: Padding(
          padding: EdgeInsets.symmetric(horizontal: 32.w),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              // AI icon/animation
              Icon(
                Icons.auto_awesome,
                size: 64.r,
                color: AppColors.primary,
              ),
              SizedBox(height: 24.h),
              // Title
              Text(
                'AI Building Your App',
                style: GoogleFonts.inter(
                  fontSize: 22.sp,
                  fontWeight: FontWeight.bold,
                  color: AppColors.textPrimary,
                ),
              ),
              SizedBox(height: 12.h),
              // Current stage
              Obx(() => Text(
                    controller.buildStage.value.isNotEmpty
                        ? controller.buildStage.value
                        : 'Analyzing your requirements...',
                    style: GoogleFonts.inter(
                      fontSize: 14.sp,
                      color: AppColors.textSecondary,
                    ),
                    textAlign: TextAlign.center,
                  )),
              SizedBox(height: 32.h),
              // Progress bar with percentage
              Obx(() {
                final progress = controller.buildProgress.value;
                return Column(
                  children: [
                    SizedBox(
                      width: 250.w,
                      child: LinearProgressIndicator(
                        value: progress > 0 ? progress : null,
                        backgroundColor: AppColors.surfaceDark,
                        valueColor: const AlwaysStoppedAnimation<Color>(
                            AppColors.primary),
                        minHeight: 6.h,
                      ),
                    ),
                    if (progress > 0) ...[
                      SizedBox(height: 8.h),
                      Text(
                        '${(progress * 100).toInt()}%',
                        style: GoogleFonts.inter(
                          fontSize: 12.sp,
                          color: AppColors.textTertiary,
                        ),
                      ),
                    ],
                  ],
                );
              }),
              SizedBox(height: 32.h),
              // Recent messages
              Obx(() {
                if (controller.buildMessages.isEmpty) return const SizedBox();
                return Container(
                  padding: EdgeInsets.all(16.r),
                  decoration: BoxDecoration(
                    color: AppColors.surfaceDark,
                    borderRadius: BorderRadius.circular(12.r),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: controller.buildMessages
                        .take(3)
                        .map((msg) => Padding(
                              padding: EdgeInsets.only(bottom: 8.h),
                              child: Row(
                                children: [
                                  Icon(Icons.check_circle,
                                      size: 16.r, color: AppColors.success),
                                  SizedBox(width: 8.w),
                                  Expanded(
                                    child: Text(
                                      msg,
                                      style: GoogleFonts.inter(
                                        fontSize: 12.sp,
                                        color: AppColors.textSecondary,
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                            ))
                        .toList(),
                  ),
                );
              }),
            ],
          ),
        ),
      ),
    );
  }

  /// Phase 3: Live Updates UI (blurred preview overlay)
  Widget _buildLiveUpdatesUI(PreviewController controller) {
    return Stack(
      children: [
        // Show the webview in background
        Column(
          children: [
            _buildPreviewControls(controller),
            Expanded(
              child: InAppWebView(
                initialSettings: InAppWebViewSettings(
                  javaScriptEnabled: true,
                  transparentBackground: true,
                ),
                pullToRefreshController: controller.pullToRefreshController,
                onWebViewCreated: (webController) {
                  controller.onWebViewCreated(webController);
                },
              ),
            ),
          ],
        ),
        // Blurred overlay
        BackdropFilter(
          filter: ImageFilter.blur(sigmaX: 10, sigmaY: 10),
          child: Container(
            color: Colors.black.withOpacity(0.6),
            child: Center(
              child: Container(
                padding: EdgeInsets.all(24.r),
                margin: EdgeInsets.symmetric(horizontal: 32.w),
                decoration: BoxDecoration(
                  color: AppColors.surfaceDark.withOpacity(0.95),
                  borderRadius: BorderRadius.circular(16.r),
                ),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    SizedBox(
                      width: 40.w,
                      height: 40.w,
                      child: CircularProgressIndicator(
                        strokeWidth: 2.5,
                        valueColor: const AlwaysStoppedAnimation<Color>(
                            AppColors.primary),
                      ),
                    ),
                    SizedBox(height: 16.h),
                    Text(
                      'Updating Preview',
                      style: GoogleFonts.inter(
                        fontSize: 18.sp,
                        fontWeight: FontWeight.w600,
                        color: AppColors.textPrimary,
                      ),
                    ),
                    SizedBox(height: 8.h),
                    Obx(() => Text(
                          controller.buildStage.value.isNotEmpty
                              ? controller.buildStage.value
                              : 'Making changes...',
                          style: GoogleFonts.inter(
                            fontSize: 13.sp,
                            color: AppColors.textSecondary,
                          ),
                          textAlign: TextAlign.center,
                        )),
                  ],
                ),
              ),
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildPreviewControls(PreviewController controller) {
    return Container(
      padding: EdgeInsets.symmetric(horizontal: 12.w, vertical: 0.h),
      decoration: BoxDecoration(
        color: Get.theme.cardTheme.color,
      ),
      child: Row(
        children: [
          // Refresh button
          IconButton(
            icon: Icon(Icons.refresh, size: 20.r),
            onPressed: controller.refreshPreview,
            tooltip: AppStrings.refresh,
            padding: EdgeInsets.zero,
            constraints: BoxConstraints(
              minWidth: 36.r,
              minHeight: 36.r,
            ),
          ),
          SizedBox(width: 4.w),
          // Open in browser button
          IconButton(
            icon: Icon(Icons.open_in_browser, size: 20.r),
            onPressed: controller.openInBrowser,
            tooltip: AppStrings.openInBrowser,
            padding: EdgeInsets.zero,
            constraints: BoxConstraints(
              minWidth: 36.r,
              minHeight: 36.r,
            ),
          ),
          SizedBox(width: 8.w),
          // URL display
          Expanded(
            child: Obx(() => GestureDetector(
                  // on click copy and show snackbar
                  onTap: () {
                    final url = controller.deploymentUrl.value;

                    if (url != null && url.isNotEmpty) {
                      Clipboard.setData(ClipboardData(text: url));

                      Get.snackbar(
                        "Copied to Clipboard",
                        url,
                        snackPosition: SnackPosition.BOTTOM,
                        backgroundColor: AppColors.primary,
                        colorText: Colors.white,
                        margin: EdgeInsets.all(16.r),
                      );
                    }
                  },
                  child: Container(
                    padding:
                        EdgeInsets.symmetric(horizontal: 8.w, vertical: 4.h),
                    decoration: BoxDecoration(
                      color: Get.theme.focusColor,
                      borderRadius: BorderRadius.circular(4.r),
                    ),
                    child: Text(
                      controller.deploymentUrl.value ?? '',
                      style: GoogleFonts.jetBrainsMono(
                        fontSize: 11.sp,
                        color: AppColors.textTertiary,
                      ),
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                )),
          ),
          // Live indicator
          SizedBox(width: 8.w),
          Container(
            padding: EdgeInsets.symmetric(horizontal: 8.w, vertical: 4.h),
            decoration: BoxDecoration(
              color: AppColors.success.withOpacity(0.1),
              borderRadius: BorderRadius.circular(4.r),
            ),
            child: Row(
              children: [
                Container(
                  width: 6.r,
                  height: 6.r,
                  decoration: const BoxDecoration(
                    color: AppColors.success,
                    shape: BoxShape.circle,
                  ),
                ),
                SizedBox(width: 4.w),
                Text(
                  'Live',
                  style: GoogleFonts.inter(
                    fontSize: 10.sp,
                    fontWeight: FontWeight.w600,
                    color: AppColors.success,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildNoPreviewState() {
    return Container(
      color: AppColors.surface,
      child: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Image.network(
              ImagePlaceholders.noPreview,
              width: 160.w,
              height: 120.h,
              fit: BoxFit.cover,
              errorBuilder: (_, __, ___) => Icon(
                Icons.preview,
                size: 64.r,
                color: AppColors.textTertiary,
              ),
            ),
            SizedBox(height: 16.h),
            Text(
              AppStrings.noPreview,
              style: GoogleFonts.inter(
                fontSize: 18.sp,
                fontWeight: FontWeight.w600,
                color: AppColors.textPrimary,
              ),
            ),
            SizedBox(height: 8.h),
            Text(
              AppStrings.noPreviewSubtitle,
              style: GoogleFonts.inter(
                fontSize: 14.sp,
                color: AppColors.textSecondary,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildErrorState(PreviewController controller) {
    return Container(
      color: AppColors.surface,
      child: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.error_outline,
              size: 48.r,
              color: AppColors.error,
            ),
            SizedBox(height: 16.h),
            Text(
              'Failed to load preview',
              style: GoogleFonts.inter(
                fontSize: 16.sp,
                fontWeight: FontWeight.w600,
                color: AppColors.textPrimary,
              ),
            ),
            SizedBox(height: 16.h),
            ElevatedButton.icon(
              onPressed: controller.refreshPreview,
              icon: const Icon(Icons.refresh),
              label: const Text('Retry'),
            ),
          ],
        ),
      ),
    );
  }
}
