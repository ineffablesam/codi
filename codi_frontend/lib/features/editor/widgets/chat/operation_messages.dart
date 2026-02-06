import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:flutter_spinkit/flutter_spinkit.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../../../core/constants/app_colors.dart';
import '../../../../core/utils/sf_font.dart';
import '../../constants/chat_icons.dart';
import '../../models/agent_message_model.dart';

class FileOperationMessage extends StatelessWidget {
  final AgentMessage message;

  const FileOperationMessage({super.key, required this.message});

  @override
  Widget build(BuildContext context) {
    final operation = message.operation ?? 'create';
    final color = _getFileOperationColor(operation);

    return Padding(
      padding: EdgeInsets.only(bottom: 6.h, left: 40.w),
      child: Container(
        padding: EdgeInsets.symmetric(horizontal: 10.w, vertical: 6.h),
        decoration: BoxDecoration(
          color: color.withOpacity(0.05),
          borderRadius: BorderRadius.circular(6.r),
          border: Border.all(
            color: color.withOpacity(0.2),
          ),
        ),
        child: Row(
          children: [
            Icon(
              _getFileOperationIcon(operation),
              size: 14.r,
              color: color,
            ),
            SizedBox(width: 8.w),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    message.filePath ?? 'Unknown file',
                    style: GoogleFonts.jetBrainsMono(
                      fontSize: 10.sp,
                      color: AppColors.textPrimary,
                      fontWeight: FontWeight.w500,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                  if (message.stats != null)
                    Text(
                      message.stats!,
                      style: SFPro.font(
                        fontSize: 9.sp,
                        color: AppColors.textSecondary,
                      ),
                    ),
                ],
              ),
            ),
            Container(
              padding: EdgeInsets.symmetric(horizontal: 6.w, vertical: 2.h),
              decoration: BoxDecoration(
                color: color.withOpacity(0.2),
                borderRadius: BorderRadius.circular(4.r),
              ),
              child: Text(
                operation.toUpperCase(),
                style: SFPro.font(
                  fontSize: 8.sp,
                  fontWeight: FontWeight.w700,
                  color: color,
                ),
              ),
            ),
          ],
        ),
      ),
    ).animate().fadeIn(duration: 300.ms).slideX(begin: 0.1, end: 0);
  }

  IconData _getFileOperationIcon(String operation) {
    switch (operation) {
      case 'create':
        return StatusIcons.fileCreate;
      case 'update':
        return StatusIcons.fileUpdate;
      case 'delete':
        return StatusIcons.fileDelete;
      case 'read':
        return StatusIcons.fileRead;
      default:
        return StatusIcons.file;
    }
  }

  Color _getFileOperationColor(String operation) {
    switch (operation) {
      case 'create':
        return AppColors.success;
      case 'update':
        return AppColors.info;
      case 'delete':
        return AppColors.error;
      default:
        return AppColors.textSecondary;
    }
  }
}

class GitOperationMessage extends StatelessWidget {
  final AgentMessage message;

  const GitOperationMessage({super.key, required this.message});

  @override
  Widget build(BuildContext context) {
    final operation = message.operation ?? 'commit';

    return Padding(
      padding: EdgeInsets.only(bottom: 8.h, left: 40.w),
      child: Container(
        padding: EdgeInsets.all(10.r),
        decoration: BoxDecoration(
          color: AppColors.gitSuccess.withOpacity(0.1),
          borderRadius: BorderRadius.circular(8.r),
          border: Border.all(color: AppColors.success.withOpacity(0.3)),
        ),
        child: Row(
          children: [
            Container(
              padding: EdgeInsets.all(6.r),
              decoration: BoxDecoration(
                color: AppColors.success.withOpacity(0.2),
                borderRadius: BorderRadius.circular(6.r),
              ),
              child: Icon(
                _getGitOperationIcon(operation),
                size: 16.r,
                color: AppColors.success,
              ),
            ),
            SizedBox(width: 10.w),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Text(
                        _getGitOperationText(operation),
                        style: SFPro.font(
                          fontSize: 10.sp,
                          fontWeight: FontWeight.w700,
                          color: AppColors.success,
                        ),
                      ),
                      if (message.branchName != null) ...[
                        SizedBox(width: 6.w),
                        Container(
                          padding: EdgeInsets.symmetric(
                              horizontal: 6.w, vertical: 2.h),
                          decoration: BoxDecoration(
                            color: AppColors.success.withOpacity(0.2),
                            borderRadius: BorderRadius.circular(4.r),
                          ),
                          child: Text(
                            message.branchName!,
                            style: GoogleFonts.jetBrainsMono(
                              fontSize: 9.sp,
                              color: AppColors.success,
                            ),
                          ),
                        ),
                      ],
                    ],
                  ),
                  SizedBox(height: 4.h),
                  Text(
                    message.text,
                    style: SFPro.font(
                      fontSize: 11.sp,
                      color: AppColors.textPrimary,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    ).animate().fadeIn(duration: 300.ms).slideX(begin: 0.1, end: 0);
  }

  IconData _getGitOperationIcon(String operation) {
    switch (operation) {
      case 'create_branch':
        return StatusIcons.gitBranch;
      case 'commit':
        return StatusIcons.gitCommit;
      case 'push':
        return StatusIcons.gitPush;
      case 'merge':
        return StatusIcons.gitMerge;
      case 'pull':
        return StatusIcons.gitPull;
      default:
        return StatusIcons.gitBranch;
    }
  }

  String _getGitOperationText(String operation) {
    // transform snake_case to Title Case
    return operation
        .split('_')
        .map((word) => word.isNotEmpty
            ? '${word[0].toUpperCase()}${word.substring(1)}'
            : '')
        .join(' ');
  }
}

class ErrorMessage extends StatelessWidget {
  final AgentMessage message;

  const ErrorMessage({super.key, required this.message});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(bottom: 12.h, left: 40.w),
      child: Container(
        padding: EdgeInsets.all(12.r),
        decoration: BoxDecoration(
          color: AppColors.errorBackground,
          borderRadius: BorderRadius.circular(10.r),
          border: Border.all(color: AppColors.error.withOpacity(0.5), width: 1),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  width: 32.r,
                  height: 32.r,
                  decoration: BoxDecoration(
                    color: AppColors.error,
                    shape: BoxShape.circle,
                  ),
                  child: Icon(
                    StatusIcons.error,
                    color: Colors.white,
                    size: 18.r,
                  ),
                ),
                SizedBox(width: 10.w),
                Expanded(
                  child: Text(
                    'Something went wrong',
                    style: SFPro.font(
                      fontSize: 13.sp,
                      fontWeight: FontWeight.w700,
                      color: AppColors.error,
                    ),
                  ),
                ),
              ],
            ),
            SizedBox(height: 10.h),
            Text(
              message.text,
              style: SFPro.font(
                fontSize: 12.sp,
                color: AppColors.textPrimary,
              ),
            ),
            if (message.error != null) ...[
              SizedBox(height: 8.h),
              Container(
                padding: EdgeInsets.all(8.r),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(6.r),
                ),
                child: Row(
                  children: [
                    Icon(
                      StatusIcons.terminal,
                      size: 12.r,
                      color: AppColors.textSecondary,
                    ),
                    SizedBox(width: 6.w),
                    Expanded(
                      child: Text(
                        message.error!,
                        style: GoogleFonts.jetBrainsMono(
                          fontSize: 9.sp,
                          color: AppColors.textSecondary,
                        ),
                        maxLines: 3,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ],
                ),
              ),
            ],
            SizedBox(height: 10.h),
            ElevatedButton.icon(
              onPressed: () {}, // Retry logic here
              icon: Icon(StatusIcons.refresh, size: 14.r),
              label: Text('Retry'),
              style: ElevatedButton.styleFrom(
                backgroundColor: AppColors.error,
                foregroundColor: Colors.white,
                padding: EdgeInsets.symmetric(horizontal: 12.w, vertical: 8.h),
                shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(8.r)),
              ),
            ),
          ],
        ),
      ),
    ).animate().fadeIn(duration: 300.ms).shake(duration: 500.ms);
  }
}

class BuildProgressMessage extends StatelessWidget {
  final AgentMessage message;

  const BuildProgressMessage({super.key, required this.message});

  @override
  Widget build(BuildContext context) {
    final progress = message.progress ?? 0.0;

    return Padding(
      padding: EdgeInsets.only(bottom: 10.h, left: 40.w),
      child: Container(
        padding: EdgeInsets.all(12.r),
        decoration: BoxDecoration(
          color: AppColors.buildProgress,
          borderRadius: BorderRadius.circular(8.r),
          border: Border.all(color: AppColors.info.withOpacity(0.3)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                SpinKitRing(
                  color: AppColors.info,
                  size: 20.r,
                  lineWidth: 2,
                ),
                SizedBox(width: 10.w),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        message.stage ?? 'Building',
                        style: SFPro.font(
                          fontSize: 11.sp,
                          fontWeight: FontWeight.w600,
                          color: AppColors.info,
                        ),
                      ),
                      Text(
                        message.text,
                        style: SFPro.font(
                          fontSize: 10.sp,
                          color: AppColors.textSecondary,
                        ),
                      ),
                    ],
                  ),
                ),
                Text(
                  '${(progress * 100).toInt()}%',
                  style: SFPro.font(
                    fontSize: 12.sp,
                    fontWeight: FontWeight.w700,
                    color: AppColors.info,
                  ),
                ),
              ],
            ),
            SizedBox(height: 10.h),
            Stack(
              children: [
                Container(
                  height: 8.h,
                  decoration: BoxDecoration(
                    color: Colors.grey[200],
                    borderRadius: BorderRadius.circular(4.r),
                  ),
                ),
                FractionallySizedBox(
                  widthFactor: progress.clamp(0.0, 1.0),
                  child: Container(
                    height: 8.h,
                    decoration: BoxDecoration(
                      gradient: LinearGradient(
                        colors: [
                          AppColors.info,
                          AppColors.info.withOpacity(0.7)
                        ],
                      ),
                      borderRadius: BorderRadius.circular(4.r),
                    ),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    ).animate().fadeIn(duration: 300.ms);
  }
}
