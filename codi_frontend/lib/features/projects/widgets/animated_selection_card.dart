/// Animated selection card widget for project wizard
library;

import 'package:flutter/material.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../../../core/constants/app_colors.dart';
import '../../../core/utils/sf_font.dart';

/// Compact animated selection card with minimal dark theme styling
class AnimatedSelectionCard extends StatelessWidget {
  final String id;
  final Widget iconWidget;
  final String title;
  final String subtitle;
  final List<String> tags;
  final List<Color> gradientColors;
  final bool isSelected;
  final VoidCallback onTap;

  const AnimatedSelectionCard({
    super.key,
    required this.id,
    required this.iconWidget,
    required this.title,
    required this.subtitle,
    required this.tags,
    required this.gradientColors,
    required this.isSelected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final primaryColor = gradientColors.first;

    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        curve: Curves.easeOutCubic,
        padding: EdgeInsets.all(14.r),
        decoration: BoxDecoration(
          color: isSelected
              ? primaryColor.withOpacity(0.12)
              : AppColors.surfaceDark,
          borderRadius: BorderRadius.circular(14.r),
          border: Border.all(
            color:
                isSelected ? primaryColor.withOpacity(0.5) : Colors.transparent,
            width: 1.5,
          ),
        ),
        child: Row(
          children: [
            // Icon container
            Container(
              width: 44.r,
              height: 44.r,
              decoration: BoxDecoration(
                color: primaryColor.withOpacity(0.15),
                borderRadius: BorderRadius.circular(12.r),
              ),
              child: Center(
                child: iconWidget,
              ),
            ),
            SizedBox(width: 12.w),
            // Content
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    title,
                    style: SFPro.semibold(
                      fontSize: 15.sp,
                      color: AppColors.textInverse,
                    ),
                  ),
                  SizedBox(height: 2.h),
                  Text(
                    subtitle,
                    style: SFPro.regular(
                      fontSize: 12.sp,
                      color: AppColors.textSecondary,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                  SizedBox(height: 6.h),
                  // Tags
                  Wrap(
                    spacing: 6.w,
                    runSpacing: 4.h,
                    children: tags.map((tag) {
                      return Container(
                        padding: EdgeInsets.symmetric(
                          horizontal: 6.w,
                          vertical: 2.h,
                        ),
                        decoration: BoxDecoration(
                          color: primaryColor.withOpacity(0.1),
                          borderRadius: BorderRadius.circular(4.r),
                        ),
                        child: Text(
                          tag,
                          style: SFPro.medium(
                            fontSize: 10.sp,
                            color: primaryColor.withOpacity(0.8),
                          ),
                        ),
                      );
                    }).toList(),
                  ),
                ],
              ),
            ),
            SizedBox(width: 8.w),
            // Selection indicator
            AnimatedContainer(
              duration: const Duration(milliseconds: 200),
              width: 22.r,
              height: 22.r,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: isSelected ? primaryColor : Colors.transparent,
                border: Border.all(
                  color: isSelected
                      ? primaryColor
                      : AppColors.textSecondary.withOpacity(0.3),
                  width: 1.5,
                ),
              ),
              child: isSelected
                  ? Icon(
                      Icons.check,
                      color: Colors.white,
                      size: 14.r,
                    )
                  : null,
            ),
          ],
        ),
      ),
    );
  }
}

/// Skip option card for optional selections
class SkipOptionCard extends StatelessWidget {
  final String title;
  final String subtitle;
  final bool isSelected;
  final VoidCallback onTap;

  const SkipOptionCard({
    super.key,
    required this.title,
    required this.subtitle,
    required this.isSelected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        padding: EdgeInsets.all(12.r),
        decoration: BoxDecoration(
          color: isSelected
              ? AppColors.textSecondary.withOpacity(0.1)
              : AppColors.surfaceDark,
          borderRadius: BorderRadius.circular(12.r),
          border: Border.all(
            color: isSelected
                ? AppColors.textSecondary.withOpacity(0.3)
                : Colors.transparent,
            width: 1.5,
          ),
        ),
        child: Row(
          children: [
            Container(
              width: 36.r,
              height: 36.r,
              decoration: BoxDecoration(
                color: AppColors.textSecondary.withOpacity(0.1),
                borderRadius: BorderRadius.circular(10.r),
              ),
              child: Icon(
                LucideIcons.circleMinus,
                color: AppColors.textSecondary,
                size: 18.r,
              ),
            ),
            SizedBox(width: 10.w),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: SFPro.semibold(
                      fontSize: 14.sp,
                      color: AppColors.textInverse,
                    ),
                  ),
                  SizedBox(height: 1.h),
                  Text(
                    subtitle,
                    style: SFPro.regular(
                      fontSize: 11.sp,
                      color: AppColors.textSecondary,
                    ),
                  ),
                ],
              ),
            ),
            AnimatedContainer(
              duration: const Duration(milliseconds: 200),
              width: 20.r,
              height: 20.r,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color:
                    isSelected ? AppColors.textSecondary : Colors.transparent,
                border: Border.all(
                  color: isSelected
                      ? AppColors.textSecondary
                      : AppColors.textSecondary.withOpacity(0.3),
                  width: 1.5,
                ),
              ),
              child: isSelected
                  ? Icon(
                      LucideIcons.check,
                      color: Colors.white,
                      size: 12.r,
                    )
                  : null,
            ),
          ],
        ),
      ),
    );
  }
}
