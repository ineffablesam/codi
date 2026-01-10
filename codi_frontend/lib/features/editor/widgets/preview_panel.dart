/// Preview panel widget with WebView
library;

import 'package:flutter/material.dart';
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
      // No preview URL yet
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
              // _buildPreviewControls(controller),
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
                        color: Colors.white.withOpacity(0.5),
                        child: Center(
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                            valueColor: const AlwaysStoppedAnimation<Color>(
                                AppColors.primary),
                          ),
                        ),
                      ),

                    // Building overlay (GitHub Actions running)
                    if (controller.isBuilding.value)
                      _buildBuildingOverlay(controller),
                  ],
                ),
              ),
            ],
          ),
        ],
      );
    });
  }

  Widget _buildPreviewControls(PreviewController controller) {
    return Container(
      padding: EdgeInsets.symmetric(horizontal: 12.w, vertical: 8.h),
      decoration: BoxDecoration(
        color: AppColors.surface,
        border: Border(
          bottom: BorderSide(color: AppColors.border),
        ),
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
            child: Obx(() => Container(
                  padding: EdgeInsets.symmetric(horizontal: 8.w, vertical: 4.h),
                  decoration: BoxDecoration(
                    color: AppColors.inputBackground,
                    borderRadius: BorderRadius.circular(4.r),
                  ),
                  child: Text(
                    controller.deploymentUrl.value ?? '',
                    style: GoogleFonts.jetBrainsMono(
                      fontSize: 11.sp,
                      color: AppColors.textSecondary,
                    ),
                    overflow: TextOverflow.ellipsis,
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

  /// Build overlay shown when GitHub Actions is running
  Widget _buildBuildingOverlay(PreviewController controller) {
    return Container(
      color: Colors.black.withOpacity(0.85),
      child: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            // Animated loading indicator
            SizedBox(
              width: 10.w,
              height: 10.w,
              child: CircularProgressIndicator(
                strokeWidth: 2,
                valueColor:
                    const AlwaysStoppedAnimation<Color>(AppColors.primary),
              ),
            ),
            SizedBox(height: 24.h),
            SizedBox(height: 12.h),
            // Stage message
            Obx(() => Text(
                  controller.buildStage.value.isNotEmpty
                      ? controller.buildStage.value
                      : 'Preparing build environment...',
                  style: GoogleFonts.inter(
                    fontSize: 14.sp,
                    color: Colors.white70,
                  ),
                  textAlign: TextAlign.center,
                )),
            SizedBox(height: 24.h),
            // Progress bar
            Obx(() => SizedBox(
                  width: 200.w,
                  child: LinearProgressIndicator(
                    value: controller.buildProgress.value > 0
                        ? controller.buildProgress.value
                        : null, // Indeterminate if no progress
                    backgroundColor: Colors.white24,
                    valueColor:
                        const AlwaysStoppedAnimation<Color>(AppColors.primary),
                  ),
                )),
            SizedBox(height: 32.h),
            // Info text
            Text(
              'Codi is building and deploying your Flutter app.\nThis usually takes 2-3 minutes.',
              style: GoogleFonts.inter(
                fontSize: 12.sp,
                color: Colors.white54,
              ),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }
}
