/// Project card widget
library;

import 'package:flutter/material.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:get/get.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:intl/intl.dart';

import '../../../core/constants/app_colors.dart';
import '../../../core/utils/sf_font.dart';
import '../models/project_model.dart';

/// Project card widget for list display
class ProjectCard extends StatelessWidget {
  final ProjectModel project;
  final VoidCallback onTap;
  final VoidCallback? onArchive;
  final VoidCallback? onRestore;
  final VoidCallback? onDelete;

  const ProjectCard({
    super.key,
    required this.project,
    required this.onTap,
    this.onArchive,
    this.onRestore,
    this.onDelete,
  });

  @override
  Widget build(BuildContext context) {
    bool isArchived = project.status == 'archived';

    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: EdgeInsets.all(16.r),
        decoration: BoxDecoration(
          color: Get.theme.cardTheme.color,
          borderRadius: BorderRadius.circular(12.r),
          border: Border.all(color: Get.theme.focusColor.withOpacity(0.1)),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.03),
              blurRadius: 10,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header row
            Row(
              children: [
                // Project icon
                Container(
                  width: 44.r,
                  height: 44.r,
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                      colors: [
                        isArchived
                            ? Colors.grey
                            : AppColors.primary.withOpacity(0.8),
                        isArchived
                            ? Colors.grey.shade400
                            : AppColors.secondary.withOpacity(0.8),
                      ],
                    ),
                    borderRadius: BorderRadius.circular(12.r),
                  ),
                  child: Center(
                    child: Text(
                      project.name.substring(0, 1).toUpperCase(),
                      style: SFPro.font(
                        fontSize: 18.sp,
                        fontWeight: FontWeight.w700,
                        color: Colors.white,
                      ),
                    ),
                  ),
                ),
                SizedBox(width: 12.w),

                // Name and status
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        project.name,
                        style: SFPro.font(
                          fontSize: 16.sp,
                          fontWeight: FontWeight.w600,
                          color: Get.textTheme.titleMedium?.color,
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                      SizedBox(height: 2.h),
                      Row(
                        children: [
                          Container(
                            width: 8.r,
                            height: 8.r,
                            decoration: BoxDecoration(
                              color: _getStatusColor(),
                              shape: BoxShape.circle,
                            ),
                          ),
                          SizedBox(width: 6.w),
                          Text(
                            _getStatusText(),
                            style: SFPro.font(
                              fontSize: 12.sp,
                              color: Get.textTheme.bodyMedium?.color,
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),

                // Actions Menu
                PopupMenuButton<String>(
                  icon: Icon(
                    Icons.more_vert,
                    color: AppColors.textTertiary,
                    size: 24.r,
                  ),
                  onSelected: (value) {
                    if (value == 'archive' && onArchive != null) {
                      onArchive!();
                    } else if (value == 'restore' && onRestore != null) {
                      onRestore!();
                    } else if (value == 'delete' && onDelete != null) {
                      onDelete!();
                    }
                  },
                  itemBuilder: (context) => [
                    if (!isArchived)
                      PopupMenuItem(
                        value: 'archive',
                        child: Row(
                          children: [
                            Icon(Icons.archive_outlined,
                                size: 20.r, color: AppColors.textSecondary),
                            SizedBox(width: 8.w),
                            Text('Archive',
                                style: TextStyle(
                                    color: Get.textTheme.bodyMedium?.color)),
                          ],
                        ),
                      ),
                    if (isArchived)
                      PopupMenuItem(
                        value: 'restore',
                        child: Row(
                          children: [
                            Icon(Icons.restore,
                                size: 20.r, color: AppColors.success),
                            SizedBox(width: 8.w),
                            Text('Restore',
                                style: TextStyle(
                                    color: Get.textTheme.bodyMedium?.color)),
                          ],
                        ),
                      ),
                    PopupMenuItem(
                      value: 'delete',
                      child: Row(
                        children: [
                          Icon(Icons.delete_outline,
                              size: 20.r, color: AppColors.error),
                          SizedBox(width: 8.w),
                          Text(
                            isArchived ? 'Delete Permanently' : 'Delete',
                            style: TextStyle(color: AppColors.error),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ],
            ),

            // Description
            if (project.description != null && project.description!.isNotEmpty)
              Padding(
                padding: EdgeInsets.only(top: 12.h),
                child: Text(
                  project.description!,
                  style: SFPro.font(
                    fontSize: 13.sp,
                    color: AppColors.textSecondary,
                  ),
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
              ),

            // Footer
            Padding(
              padding: EdgeInsets.only(top: 12.h),
              child: Row(
                children: [
                  // Branch
                  if (project.githubCurrentBranch != null) ...[
                    Icon(
                      Icons.account_tree,
                      size: 14.r,
                      color: AppColors.textTertiary,
                    ),
                    SizedBox(width: 4.w),
                    Text(
                      project.githubCurrentBranch!,
                      style: GoogleFonts.jetBrainsMono(
                        fontSize: 11.sp,
                        color: Get.textTheme.bodySmall?.color,
                      ),
                    ),
                    SizedBox(width: 16.w),
                  ],

                  // Last updated
                  Icon(
                    Icons.access_time,
                    size: 14.r,
                    color: AppColors.textTertiary,
                  ),
                  SizedBox(width: 4.w),
                  Text(
                    _formatDate(project.updatedAt),
                    style: SFPro.font(
                      fontSize: 11.sp,
                      color: AppColors.textTertiary,
                    ),
                  ),

                  const Spacer(),

                  // Deploy badge
                  if (project.hasDeployment && !isArchived)
                    Container(
                      padding:
                          EdgeInsets.symmetric(horizontal: 8.w, vertical: 4.h),
                      decoration: BoxDecoration(
                        color: AppColors.success.withOpacity(0.1),
                        borderRadius: BorderRadius.circular(4.r),
                      ),
                      child: Row(
                        children: [
                          Icon(
                            Icons.rocket_launch,
                            size: 12.r,
                            color: AppColors.success,
                          ),
                          SizedBox(width: 4.w),
                          Text(
                            'Live',
                            style: SFPro.font(
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
            ),
          ],
        ),
      ),
    );
  }

  Color _getStatusColor() {
    switch (project.status) {
      case 'active':
        return AppColors.success;
      case 'archived':
        return Colors.grey;
      case 'building':
        return AppColors.warning;
      case 'deploying':
        return AppColors.info;
      case 'error':
        return AppColors.error;
      default:
        return AppColors.textTertiary;
    }
  }

  String _getStatusText() {
    switch (project.status) {
      case 'active':
        return 'Active';
      case 'archived':
        return 'Archived';
      case 'building':
        return 'Building...';
      case 'deploying':
        return 'Deploying...';
      case 'error':
        return 'Error';
      default:
        return project.status;
    }
  }

  String _formatDate(DateTime date) {
    final now = DateTime.now();
    final diff = now.difference(date);

    if (diff.inDays == 0) {
      if (diff.inHours == 0) {
        return '${diff.inMinutes}m ago';
      }
      return '${diff.inHours}h ago';
    } else if (diff.inDays < 7) {
      return '${diff.inDays}d ago';
    }
    return DateFormat.MMMd().format(date);
  }
}
