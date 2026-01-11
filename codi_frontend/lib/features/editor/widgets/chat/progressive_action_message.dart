import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../../../core/constants/app_colors.dart';
import '../../constants/chat_icons.dart';
import '../../models/agent_message_model.dart';

class ProgressiveActionMessage extends StatelessWidget {
  final AgentMessage message;

  const ProgressiveActionMessage({
    super.key,
    required this.message,
  });

  @override
  Widget build(BuildContext context) {
    final progressItems = message.steps ?? [];
    // If no steps, fallback to single item using message text
    final itemsToDisplay = progressItems.isNotEmpty
        ? progressItems
        : [
            {'text': message.text, 'completed': false, 'type': 'processing'}
          ];

    final overallProgress = message.progress ?? 0.0;
    final showProgressBar = overallProgress > 0 && overallProgress < 1.0;
    final isStillWorking = message.isWorking ?? true;

    return Container(
      padding: EdgeInsets.all(16.r),
      margin: EdgeInsets.only(bottom: 12.h),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12.r),
        border: Border.all(color: AppColors.primary.withOpacity(0.2)),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.05),
            blurRadius: 10,
            offset: Offset(0, 4),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header with icon
          Row(
            children: [
              Container(
                width: 32.r,
                height: 32.r,
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    colors: [
                      AppColors.primary,
                      AppColors.primary.withOpacity(0.7)
                    ],
                  ),
                  borderRadius: BorderRadius.circular(8.r),
                ),
                child: Icon(
                  StatusIcons.deployed, // Rocket icon
                  size: 18.r,
                  color: Colors.white,
                ),
              ),
              SizedBox(width: 10.w),
              Expanded(
                child: Text(
                  message.text, // Main title e.g. "Building your login screen..."
                  style: GoogleFonts.inter(
                    fontSize: 14.sp,
                    fontWeight: FontWeight.w600,
                    color: AppColors.textPrimary,
                  ),
                ),
              ),
              if (isStillWorking)
                SizedBox(
                  width: 16.r,
                  height: 16.r,
                  child:
                      CircularProgressIndicator(strokeWidth: 2, color: AppColors.primary),
                ),
            ],
          ),

          if (itemsToDisplay.isNotEmpty) SizedBox(height: 12.h),

          // Progress items with professional icons
          ...itemsToDisplay.asMap().entries.map((entry) {
            final index = entry.key;
            final item = entry.value;
            final isCompleted = item['completed'] == true;
            final itemType = item['type'] as String? ?? 'processing';
            final text = item['text'] as String? ?? '';

            return Padding(
              padding: EdgeInsets.only(bottom: 8.h),
              child: Row(
                children: [
                  // Icon based on state
                  Container(
                    width: 20.r,
                    height: 20.r,
                    decoration: BoxDecoration(
                      color: isCompleted
                          ? AppColors.success.withOpacity(0.1)
                          : AppColors.textTertiary.withOpacity(0.1),
                      shape: BoxShape.circle,
                    ),
                    child: Icon(
                      isCompleted ? StatusIcons.completed : StatusIcons.processing,
                      size: 12.r,
                      color: isCompleted
                          ? AppColors.success
                          : AppColors.textTertiary,
                    ),
                  ),
                  SizedBox(width: 10.w),
                  // Icon for action type
                  Icon(
                    _getActionIcon(itemType),
                    size: 14.r,
                    color: AppColors.textSecondary,
                  ),
                  SizedBox(width: 8.w),
                  Expanded(
                    child: Text(
                      text,
                      style: GoogleFonts.inter(
                        fontSize: 12.sp,
                        color: isCompleted
                            ? AppColors.textPrimary
                            : AppColors.textSecondary,
                        fontWeight:
                            isCompleted ? FontWeight.w500 : FontWeight.w400,
                      ),
                    ),
                  ),
                  if (isCompleted)
                    Icon(
                      StatusIcons.success,
                      size: 14.r,
                      color: AppColors.success,
                    )
                        .animate()
                        .scale(duration: 200.ms, curve: Curves.easeOut),
                ],
              ),
            ).animate(delay: (index * 100).ms).fadeIn().slideX(begin: 0.1, end: 0); // Staggered animation
          }),

          // Overall progress bar
          if (showProgressBar) ...[
            SizedBox(height: 12.h),
            Row(
              children: [
                Icon(
                  StatusIcons.activity,
                  size: 14.r,
                  color: AppColors.primary,
                ),
                SizedBox(width: 8.w),
                Expanded(
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(4.r),
                    child: LinearProgressIndicator(
                      value: overallProgress,
                      backgroundColor: Colors.grey[200],
                      valueColor: AlwaysStoppedAnimation(AppColors.primary),
                      minHeight: 6.h,
                    ),
                  ),
                ),
                SizedBox(width: 8.w),
                Text(
                  '${(overallProgress * 100).toInt()}%',
                  style: GoogleFonts.inter(
                    fontSize: 11.sp,
                    fontWeight: FontWeight.w600,
                    color: AppColors.primary,
                  ),
                ),
              ],
            ),
          ],
        ],
      ),
    )
    .animate()
    .fadeIn(duration: 300.ms)
    .slideY(begin: 0.1, end: 0);
  }

  // Helper method
  IconData _getActionIcon(String type) {
    switch (type) {
      case 'file_create':
        return StatusIcons.fileCreate;
      case 'file_update':
        return StatusIcons.fileUpdate;
      case 'git_commit':
        return StatusIcons.gitCommit;
      case 'git_push':
        return StatusIcons.gitPush;
      case 'build':
        return StatusIcons.build;
      case 'deploy':
        return StatusIcons.deploy;
      default:
        return StatusIcons.processing;
    }
  }
}
