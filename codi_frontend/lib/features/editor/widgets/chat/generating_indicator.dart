import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:google_fonts/google_fonts.dart';

/// Animated indicator with smooth blurry fading dots
class GeneratingIndicator extends StatefulWidget {
  final String text;
  
  const GeneratingIndicator({super.key, this.text = 'Generating'});

  @override
  State<GeneratingIndicator> createState() => _GeneratingIndicatorState();
}

class _GeneratingIndicatorState extends State<GeneratingIndicator>
    with TickerProviderStateMixin {
  late AnimationController _controller;
  late List<Animation<double>> _dotAnimations;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      duration: const Duration(milliseconds: 1500),
      vsync: this,
    )..repeat();

    // Create staggered animations for each dot
    _dotAnimations = List.generate(3, (index) {
      final start = index * 0.2;
      final end = (start + 0.5).clamp(0.0, 1.0);
      return TweenSequence<double>([
        TweenSequenceItem(
          tween: Tween(begin: 0.0, end: 1.0)
              .chain(CurveTween(curve: Curves.easeInOut)),
          weight: 50,
        ),
        TweenSequenceItem(
          tween: Tween(begin: 1.0, end: 0.0)
              .chain(CurveTween(curve: Curves.easeInOut)),
          weight: 50,
        ),
      ]).animate(
        CurvedAnimation(
          parent: _controller,
          curve: Interval(start, end, curve: Curves.linear),
        ),
      );
    });
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: EdgeInsets.only(left: 0.13.sw),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            widget.text,
            style: GoogleFonts.inter(
              fontSize: 12.sp,
              color: Colors.grey[400],
              fontWeight: FontWeight.w500,
              letterSpacing: 0.5,
            ),
          ),
          SizedBox(width: 4.w),
          ...List.generate(3, (index) {
            return AnimatedBuilder(
              animation: _dotAnimations[index],
              builder: (context, child) {
                final value = _dotAnimations[index].value;
                return Padding(
                  padding: EdgeInsets.symmetric(horizontal: 1.w),
                  child: ImageFiltered(
                    imageFilter: ImageFilter.blur(
                      sigmaX: (1.0 - value) * 2.0,
                      sigmaY: (1.0 - value) * 2.0,
                    ),
                    child: Opacity(
                      opacity: value.clamp(0.0, 1.0),
                      child: Text(
                        '.',
                        style: GoogleFonts.inter(
                          fontSize: 16.sp,
                          color: Colors.grey[400],
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                  ),
                );
              },
            );
          }),
        ],
      ),
    );
  }
}
