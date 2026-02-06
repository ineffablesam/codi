/// Shared empty state widget
library;

import 'package:flutter/material.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';

import '../../core/constants/app_colors.dart';
import '../../core/constants/image_placeholders.dart';
import '../../core/utils/sf_font.dart';

/// Empty state widget with image, title, subtitle, and optional action
class EmptyStateWidget extends StatelessWidget {
  final String title;
  final String? subtitle;
  final String? actionLabel;
  final VoidCallback? onAction;
  final IconData? icon;

  const EmptyStateWidget({
    super.key,
    required this.title,
    this.subtitle,
    this.actionLabel,
    this.onAction,
    this.icon,
  });

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: EdgeInsets.all(32.r),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            if (icon != null)
              Icon(
                icon,
                size: 64.r,
                color: AppColors.textTertiary,
              )
            else
              Image.network(
                ImagePlaceholders.emptyState,
                width: 200.w,
                height: 150.h,
                fit: BoxFit.cover,
                errorBuilder: (_, __, ___) => Icon(
                  Icons.folder_open,
                  size: 64.r,
                  color: AppColors.textTertiary,
                ),
              ),
            SizedBox(height: 24.h),
            Text(
              title,
              style: SFPro.font(
                fontSize: 18.sp,
                fontWeight: FontWeight.w600,
                color: AppColors.textPrimary,
              ),
              textAlign: TextAlign.center,
            ),
            if (subtitle != null) ...[
              SizedBox(height: 8.h),
              Text(
                subtitle!,
                style: SFPro.font(
                  fontSize: 14.sp,
                  color: AppColors.textSecondary,
                ),
                textAlign: TextAlign.center,
              ),
            ],
            if (actionLabel != null && onAction != null) ...[
              SizedBox(height: 24.h),
              ElevatedButton(
                onPressed: onAction,
                child: Text(actionLabel!),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
