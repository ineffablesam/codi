import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:get/get.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../../../core/constants/app_colors.dart';
import '../../constants/chat_icons.dart';
import '../../models/agent_message_model.dart';
import '../../controllers/preview_controller.dart';
import '../../controllers/agent_chat_controller.dart';

class SuccessMessage extends StatelessWidget {
  final AgentMessage message;

  const SuccessMessage({
    super.key,
    required this.message,
  });

  @override
  Widget build(BuildContext context) {
    // Extract features/changes from message text or details
    // This is a simplification; ideally we parse structured data
    final features = <Map<String, dynamic>>[];
    if (message.details != null && message.details!.containsKey('features')) {
      features.addAll((message.details!['features'] as List).cast<Map<String, dynamic>>());
    } else {
        // Fallback: if text contains bullet points, split them
        final lines = message.text.split('\n');
        for (var line in lines) {
            if (line.trim().startsWith('•') || line.trim().startsWith('-')) {
                features.add({'text': line.trim().substring(1).trim(), 'type': 'feature'});
            }
        }
    }
    
    final deploymentUrl = message.deploymentUrl ?? 'https://yourapp.github.io';

    return Container(
      padding: EdgeInsets.all(16.r),
      margin: EdgeInsets.only(bottom: 12.h),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            const Color(0xFFECFDF5),
            const Color(0xFFD1FAE5)
          ],
        ),
        borderRadius: BorderRadius.circular(12.r),
        border: Border.all(color: AppColors.success.withOpacity(0.3)),
         boxShadow: [
          BoxShadow(
            color: AppColors.success.withOpacity(0.1),
            blurRadius: 10,
            offset: Offset(0, 4),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 40.r,
                height: 40.r,
                decoration: BoxDecoration(
                  color: AppColors.success,
                  shape: BoxShape.circle,
                  boxShadow: [
                    BoxShadow(
                      color: AppColors.success.withOpacity(0.3),
                      blurRadius: 8,
                      offset: Offset(0, 4),
                    ),
                  ],
                ),
                child: Icon(
                  StatusIcons.success,
                  color: Colors.white,
                  size: 22.r,
                ),
              ).animate().scale(duration: 400.ms, curve: Curves.elasticOut),
              SizedBox(width: 12.w),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Your app is ready!',
                      style: GoogleFonts.inter(
                        fontSize: 15.sp,
                        fontWeight: FontWeight.w700,
                        color: AppColors.success,
                      ),
                    ),
                    if (message.buildTime != null)
                    Text(
                      'Deployed successfully in ${message.buildTime}',
                      style: GoogleFonts.inter(
                        fontSize: 11.sp,
                        color: AppColors.textSecondary,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          
          if (features.isNotEmpty) ...[
            SizedBox(height: 12.h),
            Container(
              padding: EdgeInsets.all(12.r),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(8.r),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Icon(
                        StatusIcons.planning,
                        size: 16.r,
                        color: AppColors.warning,
                      ),
                      SizedBox(width: 6.w),
                      Text(
                        'What I built:',
                        style: GoogleFonts.inter(
                          fontSize: 12.sp,
                          fontWeight: FontWeight.w600,
                          color: AppColors.textPrimary,
                        ),
                      ),
                    ],
                  ),
                  SizedBox(height: 8.h),
                  ...features.map((feature) {
                      final text = feature['text'] as String? ?? '';
                      final type = feature['type'] as String? ?? 'feature';
                      return Padding(
                    padding: EdgeInsets.only(bottom: 6.h),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Padding(
                          padding: EdgeInsets.only(top: 4.h),
                          child: Container(
                            width: 6.r,
                            height: 6.r,
                            decoration: BoxDecoration(
                              color: AppColors.success,
                              shape: BoxShape.circle,
                            ),
                          ),
                        ),
                        SizedBox(width: 8.w),
                        Expanded(
                          child: Text(
                            text,
                            style: GoogleFonts.inter(
                              fontSize: 11.sp,
                              color: AppColors.textSecondary,
                            ),
                          ),
                        ),
                      ],
                    ),
                  );
                  }),
                ],
              ),
            ),
          ],
          
          SizedBox(height: 12.h),
          
          // Deployment URL
          if (message.deploymentUrl != null)
          Container(
            padding: EdgeInsets.all(10.r),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(6.r),
              border: Border.all(color: AppColors.border),
            ),
            child: Row(
              children: [
                Icon(
                  StatusIcons.link,
                  size: 14.r,
                  color: AppColors.primary,
                ),
                SizedBox(width: 8.w),
                Expanded(
                  child: Text(
                    deploymentUrl,
                    style: GoogleFonts.jetBrainsMono(
                      fontSize: 10.sp,
                      color: AppColors.primary,
                      decoration: TextDecoration.underline,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                Icon(
                  StatusIcons.externalLink,
                  size: 12.r,
                  color: AppColors.primary,
                ),
              ],
            ),
          ),
          
          SizedBox(height: 12.h),
          
          // Action buttons with icons
          Row(
            children: [
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: () {
                     try {
                        final previewController = Get.find<PreviewController>();
                        previewController.openInBrowser();
                      } catch (_) {}
                  },
                  icon: Icon(StatusIcons.externalLink, size: 14.r),
                  label: Text('View Live'),
                  style: OutlinedButton.styleFrom(
                    padding: EdgeInsets.symmetric(vertical: 10.h),
                    side: BorderSide(color: AppColors.success),
                    foregroundColor: AppColors.success,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8.r)),
                  ),
                ),
              ),
              SizedBox(width: 8.w),
              Expanded(
                child: ElevatedButton.icon(
                  onPressed: () {
                      // Navigate to code view
                      // This might need context or controller access
                  },
                  icon: Icon(StatusIcons.code, size: 14.r),
                  label: Text('View Code'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppColors.success,
                    foregroundColor: Colors.white,
                    padding: EdgeInsets.symmetric(vertical: 10.h),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8.r)),
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    ).animate().fadeIn(duration: 500.ms).slideY(begin: 0.2, end: 0);
  }
  
    IconData _getFeatureIcon(String type) {
    // Helper if we want specific icons per feature type
    return StatusIcons.checkSquare;
  }
}
