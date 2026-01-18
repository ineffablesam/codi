/// Splash screen
library;

import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:flutter_svg/svg.dart';
import 'package:get/get.dart';
import 'package:lottie/lottie.dart';

import '../../../config/routes.dart';
import '../../../core/storage/shared_prefs.dart';

/// Splash screen shown on app launch
class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen>
    with TickerProviderStateMixin {
  late AnimationController _slideController;
  late AnimationController _blurController;
  late Animation<Offset> _slideAnimation;
  late Animation<double> _blurAnimation;

  bool _animationComplete = false;
  bool _showLogo = false; // Control logo visibility

  @override
  void initState() {
    super.initState();

    // Slide animation controller
    _slideController = AnimationController(
      duration: const Duration(milliseconds: 1200),
      vsync: this,
    );

    // Blur animation controller
    _blurController = AnimationController(
      duration: const Duration(milliseconds: 1200),
      vsync: this,
    );

    // Slide up animation from slightly below center
    _slideAnimation = Tween<Offset>(
      begin: const Offset(0, 0.15), // Start slightly below center
      end: Offset.zero, // End at center
    ).animate(CurvedAnimation(
      parent: _slideController,
      curve: Curves.easeInOutCubic,
    ));

    // Blur animation (starts blurry, ends clear)
    _blurAnimation = Tween<double>(
      begin: 12.0, // Start with heavy blur
      end: 0.0, // End with no blur
    ).animate(CurvedAnimation(
      parent: _blurController,
      curve: Curves.easeInOut,
    ));
  }

  Future<void> _checkAuthAndNavigate() async {
    // Check if user is logged in
    final isLoggedIn = SharedPrefs.isLoggedIn;

    if (isLoggedIn) {
      Get.offAllNamed(AppRoutes.layout);
    } else {
      Get.offAllNamed(AppRoutes.login);
    }
  }

  void _onLottieComplete() {
    if (!_animationComplete) {
      _animationComplete = true;

      // Show the logo and start animations
      setState(() {
        _showLogo = true;
      });

      // Start both slide and blur animations simultaneously
      _slideController.forward();
      _blurController.forward();

      // Navigate after 4 seconds from animation completion
      Future.delayed(const Duration(seconds: 4), () {
        if (mounted) {
          _checkAuthAndNavigate();
        }
      });
    }
  }

  @override
  void dispose() {
    _slideController.dispose();
    _blurController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.white,
      body: Stack(
        alignment: Alignment.center,
        children: [
          // Container(
          //   decoration: BoxDecoration(
          //     gradient: LinearGradient(
          //       begin: Alignment.topCenter,
          //       end: Alignment.bottomCenter,
          //       colors: [
          //         const Color(0xFFEEEEEE),
          //         const Color(0xFFD8F0FF),
          //       ],
          //     ),
          //   ),
          // ),

          // Animated logo with slide and blur (hidden initially)
          if (_showLogo)
            SlideTransition(
              position: _slideAnimation,
              child: AnimatedBuilder(
                animation: _blurAnimation,
                builder: (context, child) {
                  return ImageFiltered(
                    imageFilter: ImageFilter.blur(
                      sigmaX: _blurAnimation.value,
                      sigmaY: _blurAnimation.value,
                      tileMode: TileMode.decal,
                    ),
                    child: Opacity(
                      opacity: (1.0 - (_blurAnimation.value / 12.0) * 0.7)
                          .clamp(0.3, 1.0),
                      child: child,
                    ),
                  );
                },
                child: SvgPicture.asset(
                  "assets/images/splash-logo.svg",
                  width: 130.w,
                  fit: BoxFit.cover,
                ),
              ),
            ),

          // Lottie animation
          Lottie.asset(
            "assets/lottie/codi.json",
            width: 1.sw,
            height: 1.sh,
            fit: BoxFit.cover,
            frameRate: FrameRate.max,
            filterQuality: FilterQuality.high,
            repeat: false,
            onLoaded: (composition) {
              // Trigger animations when Lottie completes
              Future.delayed(
                  composition.duration - const Duration(milliseconds: 700),
                  _onLottieComplete);
            },
          ),
        ],
      ),
    );
  }
}
