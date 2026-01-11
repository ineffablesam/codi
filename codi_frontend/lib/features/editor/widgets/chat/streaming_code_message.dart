import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_highlight/flutter_highlight.dart';
import 'package:flutter_highlight/themes/vs2015.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:flutter_spinkit/flutter_spinkit.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../../../core/constants/app_colors.dart';
import '../../constants/chat_icons.dart';
import '../../models/agent_message_model.dart';

class StreamingCodeMessage extends StatelessWidget {
  final AgentMessage message;

  const StreamingCodeMessage({
    super.key,
    required this.message,
  });

  @override
  Widget build(BuildContext context) {
    final isStreaming = message.status == 'streaming' || (message.isWorking ?? false);
    
    return Container(
      padding: EdgeInsets.all(12.r),
      margin: EdgeInsets.only(bottom: 12.h),
      decoration: BoxDecoration(
        color: const Color(0xFF1E1E1E), // VS Code dark theme
        borderRadius: BorderRadius.circular(8.r),
        border: Border.all(color: Colors.white.withOpacity(0.1)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: EdgeInsets.all(6.r),
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(4.r),
                ),
                child: Icon(
                  StatusIcons.code,
                  size: 14.r,
                  color: Colors.white70,
                ),
              ),
              SizedBox(width: 8.w),
              Text(
                'Generating code...',
                style: GoogleFonts.inter(
                  fontSize: 11.sp,
                  fontWeight: FontWeight.w600,
                  color: Colors.white70,
                ),
              ),
              const Spacer(),
              if (isStreaming)
                SpinKitThreeBounce(
                  color: Colors.white54,
                  size: 12.r,
                ),
            ],
          ),
          SizedBox(height: 8.h),
          // Code with syntax highlighting
          // Ensure we have some text to display, otherwise highlight might error
          if (message.text.isNotEmpty)
            Stack(
              children: [
                HighlightView(
                  message.text,
                  language: 'dart', // Auto-detect would be better but dart is safe default
                  theme: vs2015Theme,
                  padding: EdgeInsets.all(8.r),
                  textStyle: GoogleFonts.jetBrainsMono(
                    fontSize: 11.sp,
                    color: Colors.white,
                  ),
                ),
                // Blinking cursor at end
                 if (isStreaming)
                  Positioned(
                    bottom: 0,
                    right: 0,
                    child: Container(
                      width: 8.w,
                      height: 14.h,
                      color: Colors.white,
                    ).animate(onPlay: (controller) => controller.repeat(reverse: true))
                    .fadeIn(duration: 500.ms)
                    .then()
                    .fadeOut(duration: 500.ms),
                  ),
              ],
            ),
        ],
      ),
    ).animate().fadeIn(duration: 300.ms).slideY(begin: 0.1, end: 0);
  }
}
