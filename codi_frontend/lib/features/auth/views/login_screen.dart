/// Login screen
library;

import 'package:animate_do/animate_do.dart';
import 'package:chewie/chewie.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:get/get.dart';
import 'package:liquid_glass_renderer/liquid_glass_renderer.dart';

import '../../../core/constants/app_colors.dart';
import '../../../core/utils/sf_font.dart';
import '../../../shared/controller/ui_controller.dart';
import '../controllers/auth_controller.dart';
import '../controllers/login_video_controller.dart';
import '../widgets/github_login_button.dart';
import '../widgets/google_login_button.dart';
import '../widgets/onboarding_form_widget.dart';

/// Login screen with Google and GitHub sign-in OAuth
class LoginScreen extends StatelessWidget {
  const LoginScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final authController = Get.find<AuthController>();
    final videoController = Get.put(LoginVideoController());
    final size = MediaQuery.of(context).size;

    return AnnotatedRegion<SystemUiOverlayStyle>(
      value: SystemUiOverlayStyle.light,
      child: Scaffold(
        backgroundColor: AppColors.background,
        body: Stack(
          fit: StackFit.expand,
          alignment: Alignment.center,
          children: [
            // Fixed image background for initial load to avoid blank screen
            _buildImageBackground(size),

            /// 🔹 Background Media (Image/Video)
            Positioned.fill(
              child: Obx(() {
                return AnimatedSwitcher(
                  transitionBuilder: (child, animation) => FadeTransition(
                    opacity: animation,
                    child: child,
                  ),
                  duration: const Duration(milliseconds: 800),
                  child: videoController.showVideo.value
                      ? _buildVideoBackground(size, videoController)
                      : _buildImageBackground(size),
                );
              }),
            ),

            /// Dark Overlay
            Positioned.fill(
              child: Container(
                color: Colors.black.withOpacity(0.25),
              ),
            ),

            /// Debug buttons (only in development)
            // if (Environment.isDevelopment)
              Align(
                  alignment: Alignment.topRight,
                  child: _buildDebugButtons(authController)),

            /// Content
            Obx(() {
              final isLoading = authController.isLoading.value;
              final isNewUser = authController.isNewUser.value;
              final isProcessingAuth = authController.isProcessingAuth.value;
              final showOnboardingForm = authController.showOnboardingForm.value;

              // Priority 1: Show onboarding form if it should be displayed
              // This takes priority because the form needs to stay visible after animations
              if (showOnboardingForm && isNewUser) {
                // Stop video when showing form
                WidgetsBinding.instance.addPostFrameCallback((_) {
                  videoController.stopVideo();
                });
                return const OnboardingFormWidget()
                    .animate()
                    .fadeIn(duration: const Duration(milliseconds: 800));
              }

              // Priority 2: While processing OAuth callback, show loading
              if (isProcessingAuth) {
                return Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      SizedBox(
                        width: 30.w,
                        height: 30.w,
                        child: CircularProgressIndicator(
                          color: Colors.white,
                          strokeWidth: 3.w,
                        ),
                      ),
                    ],
                  ),
                );
              }

              // Priority 3: Show new user animation sequence during loading
              if (isLoading && isNewUser) {
                // Schedule video play after build completes
                WidgetsBinding.instance.addPostFrameCallback((_) {
                  // Reset video state first (in case it was stopped previously)
                  if (videoController.isVideoStopped.value) {
                    videoController.resetVideo();
                  }
                  videoController.playVideo();
                });
                return _buildWelcomeNewUserView(authController);
              }

              // Default: Show login buttons
              return _buildLoginView(authController);
            }),
          ],
        ),
      ),
    );
  }

  /// Debug buttons for testing flows (only visible in development)
  Widget _buildDebugButtons(AuthController authController) {
    final videoController = Get.find<LoginVideoController>();

    Widget _iconButton({
      required IconData icon,
      required VoidCallback onTap,
      String? tooltip,
    }) {
      return IconButton(
        tooltip: tooltip,
        onPressed: onTap,
        icon: Icon(
          icon,
          color: Colors.white,
          size: 20.sp,
        ),
        splashRadius: 22.r,
      );
    }

    return Align(
      alignment: Alignment.topRight,
      child: Padding(
        padding: EdgeInsets.only(top: 40.h, right: 16.w),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            // New user
            _iconButton(
              icon: Icons.person_add_alt_1,
              tooltip: 'Test New User',
              onTap: () {
                authController.isLoading.value = true;
                authController.isNewUser.value = true;
                authController.initiateNewUserFlow();
              },
            ),

            // Existing user
            _iconButton(
              icon: Icons.person,
              tooltip: 'Test Existing User',
              onTap: () {
                authController.isLoading.value = true;
                authController.isNewUser.value = false;
                authController.initiateExistingUserFlow();
              },
            ),

            // Reset
            _iconButton(
              icon: Icons.refresh,
              tooltip: 'Reset',
              onTap: () {
                authController.isLoading.value = false;
                authController.isNewUser.value = false;
                authController.showOnboardingForm.value = false;
                authController.isAnimatingNewUser.value = false;
                authController.isAnimatingExistingUser.value = false;

                // Increment reset key to force widget rebuild
                authController.resetKey.value++;
                // Reset video so it can play again
                videoController.resetVideo();
              },
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildImageBackground(Size size) {
    return SizedBox.expand(
      key: const ValueKey('image_bg'),
      child: Image.asset(
        'assets/images/3.jpg',
        fit: BoxFit.cover,
        alignment: Alignment.topCenter,
      ),
    );
  }

  Widget _buildVideoBackground(Size size, LoginVideoController controller) {
    return SizedBox.expand(
      key: const ValueKey('video_bg'),
      child: Obx(() {
        if (controller.chewieController.value != null &&
            controller.isVideoInitialized.value) {
          return FittedBox(
            fit: BoxFit.cover,
            child: SizedBox(
              width: controller.videoPlayerController.value!.value.size.width,
              height: controller.videoPlayerController.value!.value.size.height,
              child: Chewie(controller: controller.chewieController.value!),
            ),
          );
        }
        return const SizedBox.shrink();
      }),
    );
  }

  /// Default login view with buttons
  Widget _buildLoginView(AuthController authController) {
    final size = MediaQuery.of(Get.context!).size;
    final ui = Get.find<UIController>();
    return Align(
      alignment: Alignment.bottomCenter,
      child: SlideInUp(
        duration: const Duration(milliseconds: 600),
        curve: Curves.fastLinearToSlowEaseIn,
        from: 110,
        child: LiquidGlassLayer(
          settings: const LiquidGlassSettings(
            thickness: 90,
            blur: 8,
            refractiveIndex: 1.5,
            glassColor: Color(0x1505042A),
          ),
          child: Padding(
            padding: EdgeInsets.all(16.w),
            child: LiquidStretch(
              stretch: 0.5,
              interactionScale: 1.02,
              child: LiquidGlass(
                shape: LiquidRoundedSuperellipse(
                  borderRadius: 50,
                ),
                child: Obx(() {
                  return Container(
                    width: size.width,
                    padding: EdgeInsets.all(24.w),
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.only(
                        topLeft: Radius.circular(ui.topLeft.value),
                        topRight: Radius.circular(ui.topRight.value),
                        bottomLeft: Radius.circular(ui.bottomLeft.value),
                        bottomRight: Radius.circular(ui.bottomRight.value),
                      ),
                    ),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        /// Drag Indicator
                        Container(
                          width: 40,
                          height: 4,
                          margin: const EdgeInsets.only(bottom: 20),
                          decoration: BoxDecoration(
                            color: Colors.grey.shade300,
                            borderRadius: BorderRadius.circular(2),
                          ),
                        ),

                        /// Title
                        Row(
                          mainAxisAlignment: MainAxisAlignment.start,
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                Text(
                                  'Welcome Back',
                                  style: SFPro.font(
                                    fontSize: 33,
                                    fontWeight: FontWeight.w700,
                                    color: Colors.white,
                                  ),
                                ),
                                Text(
                                  'Step into the Codi\'verse',
                                  style: SFPro.font(
                                    fontSize: 15,
                                    fontWeight: FontWeight.w400,
                                    color: Colors.white,
                                  ),
                                ),
                              ],
                            ),
                          ],
                        ),
                        20.verticalSpace,

                        // Error message
                        Obx(() {
                          if (authController.errorMessage.value != null) {
                            return Container(
                              margin: EdgeInsets.only(bottom: 16.h),
                              padding: EdgeInsets.all(12.r),
                              decoration: BoxDecoration(
                                color: Colors.red.shade800.withOpacity(0.6),
                                borderRadius: BorderRadius.circular(8.r),
                              ),
                              child: Row(
                                children: [
                                  Icon(
                                    Icons.error_outline,
                                    color: Colors.red.shade100,
                                    size: 20.r,
                                  ),
                                  SizedBox(width: 8.w),
                                  Expanded(
                                    child: Text(
                                      authController.errorMessage.value!,
                                      style: SFPro.font(
                                        fontSize: 14.sp,
                                        fontWeight: FontWeight.w500,
                                        color: Colors.red.shade100,
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                            );
                          }
                          return const SizedBox.shrink();
                        }),

                        // GitHub login button
                        Obx(() => GitHubLoginButton(
                              isLoading: authController.isLoading.value,
                              onPressed: authController.loginWithGitHub,
                            )),
                        6.verticalSpace,

                        // Google login button (test trigger)
                        Obx(() => GoogleLoginButton(
                              isLoading: authController.isLoading.value,
                              onPressed: authController.loginWithGitHub,
                            )),
                        SizedBox(height: 16.h),

                        // Terms text
                        Text(
                          'By continuing, you agree to our Terms of Service and Privacy Policy',
                          style: SFPro.font(
                            fontWeight: FontWeight.w400,
                            fontSize: 12.sp,
                            color: AppColors.textTertiary,
                          ),
                          textAlign: TextAlign.center,
                        ),
                        SizedBox(height: 24.h),
                      ],
                    ),
                  );
                }),
              ),
            ),
          ),
        ),
      ),
    );
  }

  /// Build new user welcome animation sequence
  /// Only shows the animation - form is handled by main Obx builder when showOnboardingForm is true
  Widget _buildWelcomeNewUserView(AuthController authController) {
    return Padding(
      key: ValueKey('new_user_flow_${authController.resetKey.value}'),
      padding: EdgeInsets.symmetric(
        horizontal: 16.w,
        vertical: 40.h,
      ),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Text(
            'Welcome to the Codi',
            textAlign: TextAlign.center,
            style: SFPro.black(
              fontSize: 24.sp,
              color: Colors.white,
            ),
          ),
          8.verticalSpace,
          Text(
            'Where code meets creativity, pocket-sized',
            textAlign: TextAlign.center,
            style: SFPro.font(
              fontSize: 14.sp,
              fontWeight: FontWeight.w400,
              color: Colors.grey.shade200,
            ),
          ),
        ],
      )
          .animate()
          .fadeIn(duration: const Duration(milliseconds: 800))
          .then(delay: const Duration(seconds: 2))
          .fadeOut(duration: const Duration(milliseconds: 600))
          .swap(
            builder: (_, __) => Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Text(
                  'Configuring your studio...',
                  textAlign: TextAlign.center,
                  style: SFPro.black(
                    fontSize: 24.sp,
                    color: Colors.white,
                  ),
                ),
                8.verticalSpace,
                Text(
                  'Your AI agents need to know you',
                  textAlign: TextAlign.center,
                  style: SFPro.font(
                    fontSize: 14.sp,
                    fontWeight: FontWeight.w400,
                    color: Colors.grey.shade200,
                  ),
                ),
              ],
            )
                .animate()
                .fadeIn(duration: const Duration(milliseconds: 800)),
          ),
    );
  }


  /// Build existing user view with rotating messages
  Widget _buildExistingUserView(AuthController authController) {
    final messages = [
      'Syncing your workspace...',
      'Waking up your AI agents...',
      'Loading your projects...',
      'Restoring your vibe...',
      'Almost ready...',
    ];

    return Padding(
      padding: EdgeInsets.symmetric(
        horizontal: 24.w,
        vertical: 40.h,
      ),
      child: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text(
              'Welcome back, coder! 👋',
              textAlign: TextAlign.center,
              style: SFPro.black(
                fontSize: 28.sp,
                color: Colors.white,
              ),
            ),
            24.verticalSpace,
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              crossAxisAlignment: CrossAxisAlignment.center,
              children: [
                SizedBox(
                  width: 16.w,
                  height: 16.w,
                  child: CircularProgressIndicator(
                    color: Colors.white,
                    strokeWidth: 2.5.w,
                    backgroundColor: Colors.grey.shade200.withOpacity(0.2),
                  ),
                ),
                12.horizontalSpace,
                Flexible(
                  child: Text(
                    messages[0],
                    textAlign: TextAlign.center,
                    style: SFPro.font(
                      fontSize: 14.sp,
                      fontWeight: FontWeight.w400,
                      color: Colors.grey.shade200,
                    ),
                  )
                      .animate(
                        onPlay: (controller) => controller.repeat(),
                      )
                      .fadeOut(
                        delay: const Duration(milliseconds: 2000),
                        duration: const Duration(milliseconds: 400),
                      )
                      .swap(
                        builder: (_, __) => Text(
                          messages[1],
                          textAlign: TextAlign.center,
                          style: SFPro.font(
                            fontSize: 14.sp,
                            fontWeight: FontWeight.w400,
                            color: Colors.grey.shade200,
                          ),
                        ),
                      )
                      .fadeIn(duration: const Duration(milliseconds: 400))
                      .then(delay: const Duration(milliseconds: 1600))
                      .fadeOut(duration: const Duration(milliseconds: 400))
                      .swap(
                        builder: (_, __) => Text(
                          messages[2],
                          textAlign: TextAlign.center,
                          style: SFPro.font(
                            fontSize: 14.sp,
                            fontWeight: FontWeight.w400,
                            color: Colors.grey.shade200,
                          ),
                        ),
                      )
                      .fadeIn(duration: const Duration(milliseconds: 400))
                      .then(delay: const Duration(milliseconds: 1600))
                      .fadeOut(duration: const Duration(milliseconds: 400))
                      .swap(
                        builder: (_, __) => Text(
                          messages[3],
                          textAlign: TextAlign.center,
                          style: SFPro.font(
                            fontSize: 14.sp,
                            fontWeight: FontWeight.w400,
                            color: Colors.grey.shade200,
                          ),
                        ),
                      )
                      .fadeIn(duration: const Duration(milliseconds: 400))
                      .then(delay: const Duration(milliseconds: 1600))
                      .fadeOut(duration: const Duration(milliseconds: 400))
                      .swap(
                        builder: (_, __) => Text(
                          messages[4],
                          textAlign: TextAlign.center,
                          style: SFPro.font(
                            fontSize: 14.sp,
                            fontWeight: FontWeight.w400,
                            color: Colors.grey.shade200,
                          ),
                        ),
                      )
                      .fadeIn(duration: const Duration(milliseconds: 400)),
                ),
              ],
            ),
          ],
        ).animate().fadeIn(
              duration: const Duration(milliseconds: 800),
            ),
      ),
    );
  }
}
