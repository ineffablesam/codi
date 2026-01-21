/// Selectable option button widget with animated container
library;

import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';

import '../../../core/utils/sf_font.dart';

/// A custom selectable button with animated container and blue border on selection
class SelectableOptionButton extends StatelessWidget {
  final String title;
  final String? subtitle;
  final bool isSelected;
  final VoidCallback onTap;

  const SelectableOptionButton({
    super.key,
    required this.title,
    this.subtitle,
    required this.isSelected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: ClipRRect(
        borderRadius: BorderRadius.circular(12.r),
        child: BackdropFilter(
          filter: ImageFilter.blur(
            sigmaX: 8,
            sigmaY: 8,
          ),
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 200),
            curve: Curves.easeInOut,
            height: subtitle != null ? 70.h : 50.h,
            width: 1.sw,
            decoration: BoxDecoration(
              color: Colors.grey.shade800.withOpacity(0.15),
              border: Border.all(
                color: isSelected ? Colors.blue.shade200 : Colors.grey.shade600,
                width: isSelected ? 2 : 1,
              ),
              borderRadius: BorderRadius.circular(12.r),
            ),
            child: Row(
              children: [
                Expanded(
                  child: Padding(
                    padding: EdgeInsets.symmetric(
                      horizontal: 12.w,
                      vertical: 8.h,
                    ),
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          title,
                          style: SFPro.font(
                            fontSize: 15.sp,
                            fontWeight: FontWeight.w700,
                            color: Colors.white,
                          ),
                        ),
                        if (subtitle != null) ...[
                          Text(
                            subtitle!,
                            style: SFPro.font(
                              fontSize: 12.sp,
                              fontWeight: FontWeight.w300,
                              color: Colors.grey.shade300,
                            ),
                          ),
                        ],
                      ],
                    ),
                  ),
                ),
                if (isSelected)
                  Padding(
                    padding: EdgeInsets.only(right: 12.w),
                    child: Icon(
                      Icons.check_circle,
                      color: Colors.blue.shade200,
                      size: 24.r,
                    ),
                  ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
