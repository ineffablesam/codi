import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:flutter_spinkit/flutter_spinkit.dart';

/// Minimal thinking indicator - just animated dots
/// Auto-hides when next message arrives (handled by controller)
class ThinkingMessage extends StatelessWidget {
  const ThinkingMessage({super.key});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.symmetric(horizontal: 16.w, vertical: 12.h),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.start,
        children: [
          SpinKitThreeBounce(
            color: Colors.grey[400],
            size: 20.r,
          ),
        ],
      ),
    ).animate().fadeIn(duration: 300.ms);
  }
}
