/// GitHub login button widget
library;

import 'package:flutter/material.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:shadcn_flutter/shadcn_flutter.dart'
    hide Colors, CircularProgressIndicator;

import '../../../core/constants/app_colors.dart';
import '../../../core/constants/app_strings.dart';
import '../../../core/utils/sf_font.dart';

/// Styled GitHub login button
class GitHubLoginButton extends StatelessWidget {
  final bool isLoading;
  final VoidCallback onPressed;

  const GitHubLoginButton({
    super.key,
    this.isLoading = false,
    required this.onPressed,
  });

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: double.infinity,
      height: 50.h,
      child: ElevatedButton(
        onPressed: isLoading ? null : onPressed,
        style: ElevatedButton.styleFrom(
          backgroundColor: Colors.black,
          foregroundColor: Colors.white,
          elevation: 0,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12.r),
          ),
          padding: EdgeInsets.symmetric(horizontal: 24.w),
        ),
        child: isLoading
            ? SizedBox(
                width: 24.r,
                height: 24.r,
                child: const CircularProgressIndicator(
                  strokeWidth: 2,
                  valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                ),
              )
            : Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  // GitHub icon
                  Container(
                    width: 24.r,
                    height: 24.r,
                    child: Center(
                      child: Icon(
                        RadixIcons.githubLogo,
                        size: 16.r,
                        color: AppColors.github,
                      ),
                    ),
                  ),
                  SizedBox(width: 6.w),
                  Text(
                    AppStrings.loginWithGitHub,
                    style: SFPro.font(
                      fontSize: 16.sp,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ),
      ),
    );
  }
}
