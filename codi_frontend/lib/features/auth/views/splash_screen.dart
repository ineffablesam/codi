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
  late AnimationController _fadeController;
  late AnimationController _scaleController;
  late AnimationController _blurController;

  late Animation<Offset> _slideAnimation;
  late Animation<double> _fadeAnimation;
  late Animation<double> _scaleAnimation;
  late Animation<double> _blurAnimation;

  bool _animationComplete = false;
  bool _showLogo = false;
  bool _hasNavigated = false;

  @override
  void initState() {
    super.initState();
    _initializeAnimations();
  }

  void _initializeAnimations() {
    // Slide animation controller - smoother duration
    _slideController = AnimationController(
      duration: const Duration(milliseconds: 1500),
      vsync: this,
    );

    // Fade animation controller
    _fadeController = AnimationController(
      duration: const Duration(milliseconds: 1000),
      vsync: this,
    );

    // Scale animation controller
    _scaleController = AnimationController(
      duration: const Duration(milliseconds: 1500),
      vsync: this,
    );

    // Blur animation controller
    _blurController = AnimationController(
      duration: const Duration(milliseconds: 1800),
      vsync: this,
    );

    // Slide up animation with improved curve
    _slideAnimation = Tween<Offset>(
      begin: const Offset(0, 0.2),
      end: Offset.zero,
    ).animate(CurvedAnimation(
      parent: _slideController,
      curve: Curves.easeOutCubic,
    ));

    // Fade in animation
    _fadeAnimation = Tween<double>(
      begin: 0.0,
      end: 1.0,
    ).animate(CurvedAnimation(
      parent: _fadeController,
      curve: Curves.easeIn,
    ));

    // Scale animation (slight zoom in effect)
    _scaleAnimation = Tween<double>(
      begin: 0.8,
      end: 1.0,
    ).animate(CurvedAnimation(
      parent: _scaleController,
      curve: Curves.easeOutBack,
    ));

    // Blur animation (starts blurry, ends clear)
    _blurAnimation = Tween<double>(
      begin: 15.0,
      end: 0.0,
    ).animate(CurvedAnimation(
      parent: _blurController,
      curve: Curves.easeOutQuart,
    ));
  }

  Future<void> _checkAuthAndNavigate() async {
    if (_hasNavigated) return;
    _hasNavigated = true;

    try {
      final isLoggedIn = SharedPrefs.isLoggedIn;

      if (!mounted) return;

      if (isLoggedIn) {
        await Get.offAllNamed(AppRoutes.layout);
      } else {
        await Get.offAllNamed(AppRoutes.login);
      }
    } catch (e) {
      debugPrint('Navigation error: $e');
    }
  }

  void _onLottieComplete() {
    if (!_animationComplete && mounted) {
      _animationComplete = true;

      // Show the logo with a slight delay for smoothness
      Future.delayed(const Duration(milliseconds: 100), () {
        if (!mounted) return;

        setState(() {
          _showLogo = true;
        });

        // Stagger the animations for a more polished effect
        _fadeController.forward();

        Future.delayed(const Duration(milliseconds: 100), () {
          if (!mounted) return;
          _blurController.forward();
          _scaleController.forward();
        });

        Future.delayed(const Duration(milliseconds: 200), () {
          if (!mounted) return;
          _slideController.forward();
        });

        // Navigate after animations complete
        Future.delayed(const Duration(milliseconds: 3500), () {
          if (mounted && !_hasNavigated) {
            _checkAuthAndNavigate();
          }
        });
      });
    }
  }

  @override
  void dispose() {
    _slideController.dispose();
    _fadeController.dispose();
    _scaleController.dispose();
    _blurController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Get.theme.scaffoldBackgroundColor,
      body: Stack(
        alignment: Alignment.center,
        children: [
          // Optional gradient background
          // Uncomment if needed
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

          // Lottie animation layer
          Positioned.fill(
            child: Lottie.asset(
              "assets/lottie/codi.json",
              width: 1.sw,
              height: 1.sh,
              fit: BoxFit.cover,
              frameRate: FrameRate.max,
              filterQuality: FilterQuality.high,
              repeat: false,
              alignment: Alignment.center,
              onLoaded: (composition) {
                if (!mounted) return;
                // Trigger animations when Lottie is near completion
                final delay =
                    composition.duration - const Duration(milliseconds: 700);
                Future.delayed(delay, _onLottieComplete);
              },
            ),
          ),

          // Animated logo layer (appears after Lottie)
          if (_showLogo)
            Align(
              alignment: Alignment.center,
              child: AnimatedBuilder(
                animation: Listenable.merge([
                  _slideAnimation,
                  _fadeAnimation,
                  _scaleAnimation,
                  _blurAnimation,
                ]),
                builder: (context, child) {
                  return SlideTransition(
                    position: _slideAnimation,
                    child: FadeTransition(
                      opacity: _fadeAnimation,
                      child: ScaleTransition(
                        scale: _scaleAnimation,
                        child: ImageFiltered(
                          imageFilter: ImageFilter.blur(
                            sigmaX: _blurAnimation.value,
                            sigmaY: _blurAnimation.value,
                            tileMode: TileMode.decal,
                          ),
                          child: SvgPicture.asset(
                            "assets/images/splash-logo.svg",
                            width: 130.w,
                            fit: BoxFit.contain,
                          ),
                        ),
                      ),
                    ),
                  );
                },
              ),
            ),
        ],
      ),
    );
  }
}
