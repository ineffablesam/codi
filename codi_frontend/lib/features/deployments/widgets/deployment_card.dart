/// Deployment card widget
library;

import 'package:flutter/material.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:intl/intl.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../../core/constants/app_colors.dart';
import '../models/deployment_model.dart';

/// Deployment card widget
class DeploymentCard extends StatelessWidget {
  final DeploymentModel deployment;

  const DeploymentCard({super.key, required this.deployment});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: EdgeInsets.all(16.r),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(12.r),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header
          Row(
            children: [
              _buildStatusBadge(),
              const Spacer(),
              Text(
                DateFormat.yMMMd().add_Hm().format(deployment.createdAt),
                style: GoogleFonts.inter(
                  fontSize: 12.sp,
                  color: AppColors.textSecondary,
                ),
              ),
            ],
          ),
          SizedBox(height: 12.h),

          // Commit info
          if (deployment.commitMessage != null)
            Text(
              deployment.commitMessage!,
              style: GoogleFonts.inter(
                fontSize: 14.sp,
                fontWeight: FontWeight.w500,
                color: AppColors.textPrimary,
              ),
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
          SizedBox(height: 8.h),

          // Git info row
          Row(
            children: [
              if (deployment.branch != null) ...[
                Icon(Icons.account_tree, size: 14.r, color: AppColors.textTertiary),
                SizedBox(width: 4.w),
                Text(
                  deployment.branch!,
                  style: GoogleFonts.jetBrainsMono(
                    fontSize: 11.sp,
                    color: AppColors.textSecondary,
                  ),
                ),
                SizedBox(width: 12.w),
              ],
              if (deployment.shortCommitSha.isNotEmpty) ...[
                Icon(Icons.commit, size: 14.r, color: AppColors.textTertiary),
                SizedBox(width: 4.w),
                Text(
                  deployment.shortCommitSha,
                  style: GoogleFonts.jetBrainsMono(
                    fontSize: 11.sp,
                    color: AppColors.textSecondary,
                  ),
                ),
              ],
            ],
          ),

          // Stats row
          if (deployment.buildTime != null || deployment.size != null) ...[
            SizedBox(height: 8.h),
            Row(
              children: [
                if (deployment.buildTime != null) ...[
                  Icon(Icons.timer, size: 14.r, color: AppColors.textTertiary),
                  SizedBox(width: 4.w),
                  Text(
                    deployment.buildTime!,
                    style: GoogleFonts.inter(
                      fontSize: 11.sp,
                      color: AppColors.textSecondary,
                    ),
                  ),
                  SizedBox(width: 16.w),
                ],
                if (deployment.size != null) ...[
                  Icon(Icons.data_usage, size: 14.r, color: AppColors.textTertiary),
                  SizedBox(width: 4.w),
                  Text(
                    deployment.size!,
                    style: GoogleFonts.inter(
                      fontSize: 11.sp,
                      color: AppColors.textSecondary,
                    ),
                  ),
                ],
              ],
            ),
          ],

          // Deployment URL
          if (deployment.deploymentUrl != null && deployment.isSuccess) ...[
            SizedBox(height: 12.h),
            GestureDetector(
              onTap: () => _openUrl(deployment.deploymentUrl!),
              child: Container(
                padding: EdgeInsets.symmetric(horizontal: 12.w, vertical: 8.h),
                decoration: BoxDecoration(
                  color: AppColors.deploymentSuccess,
                  borderRadius: BorderRadius.circular(6.r),
                ),
                child: Row(
                  children: [
                    Icon(Icons.link, size: 14.r, color: AppColors.success),
                    SizedBox(width: 8.w),
                    Expanded(
                      child: Text(
                        deployment.deploymentUrl!,
                        style: GoogleFonts.jetBrainsMono(
                          fontSize: 11.sp,
                          color: AppColors.success,
                        ),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                    Icon(Icons.open_in_new, size: 14.r, color: AppColors.success),
                  ],
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildStatusBadge() {
    Color color;
    String text;
    IconData icon;

    if (deployment.isSuccess) {
      color = AppColors.success;
      text = 'Success';
      icon = Icons.check_circle;
    } else if (deployment.isFailed) {
      color = AppColors.error;
      text = 'Failed';
      icon = Icons.error;
    } else {
      color = AppColors.warning;
      text = 'Building';
      icon = Icons.pending;
    }

    return Container(
      padding: EdgeInsets.symmetric(horizontal: 8.w, vertical: 4.h),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(4.r),
      ),
      child: Row(
        children: [
          Icon(icon, size: 14.r, color: color),
          SizedBox(width: 4.w),
          Text(
            text,
            style: GoogleFonts.inter(
              fontSize: 11.sp,
              fontWeight: FontWeight.w600,
              color: color,
            ),
          ),
        ],
      ),
    );
  }

  void _openUrl(String url) async {
    final uri = Uri.parse(url);
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    }
  }
}
