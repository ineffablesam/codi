/// Login screen
library;

import 'package:flutter/material.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:get/get.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../../core/constants/app_colors.dart';
import '../../../core/constants/app_strings.dart';
import '../../../core/constants/image_placeholders.dart';
import '../controllers/auth_controller.dart';
import '../widgets/github_login_button.dart';

/// Login screen with GitHub OAuth
class LoginScreen extends StatelessWidget {
  const LoginScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final authController = Get.find<AuthController>();

    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: Padding(
          padding: EdgeInsets.symmetric(horizontal: 24.w),
          child: Column(
            children: [
              SizedBox(height: 60.h),
              
              // Header section
              Expanded(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    // Logo
                    Container(
                      width: 100.r,
                      height: 100.r,
                      decoration: BoxDecoration(
                        gradient: const LinearGradient(
                          begin: Alignment.topLeft,
                          end: Alignment.bottomRight,
                          colors: [
                            AppColors.primary,
                            AppColors.secondary,
                          ],
                        ),
                        borderRadius: BorderRadius.circular(24.r),
                        boxShadow: [
                          BoxShadow(
                            color: AppColors.primary.withOpacity(0.3),
                            blurRadius: 30,
                            offset: const Offset(0, 15),
                          ),
                        ],
                      ),
                      child: Center(
                        child: Text(
                          '🤖',
                          style: TextStyle(fontSize: 48.sp),
                        ),
                      ),
                    ),
                    SizedBox(height: 32.h),

                    // Title
                    Text(
                      AppStrings.loginTitle,
                      style: GoogleFonts.inter(
                        fontSize: 28.sp,
                        fontWeight: FontWeight.w700,
                        color: AppColors.textPrimary,
                        letterSpacing: -0.5,
                      ),
                      textAlign: TextAlign.center,
                    ),
                    SizedBox(height: 8.h),

                    // Subtitle
                    Text(
                      AppStrings.loginSubtitle,
                      style: GoogleFonts.inter(
                        fontSize: 16.sp,
                        fontWeight: FontWeight.w400,
                        color: AppColors.textSecondary,
                      ),
                      textAlign: TextAlign.center,
                    ),
                    SizedBox(height: 48.h),

                    // Features list
                    _buildFeaturesList(),
                  ],
                ),
              ),

              // Login button section
              Column(
                children: [
                  // Error message
                  Obx(() {
                    if (authController.errorMessage.value != null) {
                      return Container(
                        margin: EdgeInsets.only(bottom: 16.h),
                        padding: EdgeInsets.all(12.r),
                        decoration: BoxDecoration(
                          color: AppColors.errorBackground,
                          borderRadius: BorderRadius.circular(8.r),
                        ),
                        child: Row(
                          children: [
                            Icon(
                              Icons.error_outline,
                              color: AppColors.error,
                              size: 20.r,
                            ),
                            SizedBox(width: 8.w),
                            Expanded(
                              child: Text(
                                authController.errorMessage.value!,
                                style: GoogleFonts.inter(
                                  fontSize: 14.sp,
                                  color: AppColors.error,
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
                  SizedBox(height: 16.h),

                  // Terms text
                  Text(
                    'By continuing, you agree to our Terms of Service and Privacy Policy',
                    style: GoogleFonts.inter(
                      fontSize: 12.sp,
                      color: AppColors.textTertiary,
                    ),
                    textAlign: TextAlign.center,
                  ),
                  SizedBox(height: 24.h),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildFeaturesList() {
    final features = [
      ('🚀', 'Build Flutter apps with AI'),
      ('💻', 'Real-time code generation'),
      ('☁️', 'Deploy to GitHub Pages'),
    ];

    return Column(
      children: features.map((feature) {
        return Padding(
          padding: EdgeInsets.only(bottom: 12.h),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Text(
                feature.$1,
                style: TextStyle(fontSize: 24.sp),
              ),
              SizedBox(width: 12.w),
              Text(
                feature.$2,
                style: GoogleFonts.inter(
                  fontSize: 16.sp,
                  fontWeight: FontWeight.w500,
                  color: AppColors.textPrimary,
                ),
              ),
            ],
          ),
        );
      }).toList(),
    );
  }
}
