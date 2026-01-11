import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:flutter_spinkit/flutter_spinkit.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../../../core/constants/app_colors.dart';
import '../../constants/chat_icons.dart';
import '../../models/agent_message_model.dart';

class ThinkingMessage extends StatelessWidget {
  final AgentMessage message;

  const ThinkingMessage({
    super.key,
    required this.message,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: EdgeInsets.all(16.r),
      margin: EdgeInsets.only(bottom: 12.h),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            const Color(0xFFF3F4F6),
            const Color(0xFFE5E7EB),
          ],
        ),
        borderRadius: BorderRadius.circular(12.r),
        border: Border.all(
          color: Colors.white.withOpacity(0.5),
          width: 1,
        ),
      ),
      child: Row(
        children: [
          // Animated thinking indicator with icon
          Container(
            width: 36.r,
            height: 36.r,
            decoration: BoxDecoration(
              color: AppColors.primary.withOpacity(0.1),
              shape: BoxShape.circle,
            ),
            child: Stack(
              alignment: Alignment.center,
              children: [
                SpinKitPulse(
                  color: AppColors.primary,
                  size: 36.r,
                ),
                Icon(
                  StatusIcons.thinking,
                  size: 18.r,
                  color: AppColors.primary,
                ),
              ],
            ),
          ),
          SizedBox(width: 12.w),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Thinking about your request...',
                  style: GoogleFonts.inter(
                    fontSize: 13.sp,
                    fontWeight: FontWeight.w600,
                    color: AppColors.primary,
                  ),
                ),
                if (message.text.isNotEmpty) ...[
                  SizedBox(height: 4.h),
                  Text(
                    message.text,
                    style: GoogleFonts.inter(
                      fontSize: 12.sp,
                      color: AppColors.textSecondary,
                      fontStyle: FontStyle.italic,
                    ),
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    )
        .animate()
        .fadeIn(duration: 400.ms, curve: Curves.easeOut)
        .slideX(begin: -0.1, end: 0, duration: 400.ms, curve: Curves.easeOut);
  }
}
