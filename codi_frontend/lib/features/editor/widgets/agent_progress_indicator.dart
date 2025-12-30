/// Agent progress indicator widget
library;

import 'package:flutter/material.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:get/get.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../../core/constants/app_colors.dart';
import '../controllers/editor_controller.dart';

/// Circular progress indicator for build/deploy status
class AgentProgressIndicator extends StatelessWidget {
  final double size;
  final double strokeWidth;

  const AgentProgressIndicator({
    super.key,
    this.size = 48,
    this.strokeWidth = 4,
  });

  @override
  Widget build(BuildContext context) {
    final controller = Get.find<EditorController>();

    return Obx(() {
      final progress = controller.buildProgress.value;
      final isWorking = controller.isAgentWorking.value;

      if (!isWorking && progress == 0) {
        return const SizedBox.shrink();
      }

      return Container(
        width: size.r,
        height: size.r,
        child: Stack(
          alignment: Alignment.center,
          children: [
            // Background circle
            SizedBox(
              width: size.r,
              height: size.r,
              child: CircularProgressIndicator(
                value: 1.0,
                strokeWidth: strokeWidth,
                valueColor: AlwaysStoppedAnimation(AppColors.border),
              ),
            ),
            // Progress circle
            SizedBox(
              width: size.r,
              height: size.r,
              child: CircularProgressIndicator(
                value: progress > 0 ? progress : null,
                strokeWidth: strokeWidth,
                valueColor: AlwaysStoppedAnimation(
                  progress > 0 ? AppColors.primary : AppColors.info,
                ),
              ),
            ),
            // Percentage text
            if (progress > 0)
              Text(
                '${(progress * 100).toInt()}%',
                style: GoogleFonts.inter(
                  fontSize: (size / 4).sp,
                  fontWeight: FontWeight.w600,
                  color: AppColors.primary,
                ),
              ),
          ],
        ),
      );
    });
  }
}
