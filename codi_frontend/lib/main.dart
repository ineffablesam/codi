/// Codi Frontend - AI-powered Flutter development platform
///
/// Main entry point for the mobile application (iOS/Android only)
library;

import 'package:codi_frontend/shared/controller/ui_controller.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:get/get.dart';

import 'app.dart';
import 'bindings/initial_binding.dart';
import 'core/storage/shared_prefs.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  Get.put(UIController(), permanent: true);

  // Set preferred orientations
  await SystemChrome.setPreferredOrientations([
    DeviceOrientation.portraitUp,
    DeviceOrientation.portraitDown,
    DeviceOrientation.landscapeLeft,
    DeviceOrientation.landscapeRight,
  ]);

  // Initialize shared preferences
  await SharedPrefs.init();

  // Initialize GetX bindings
  InitialBinding().dependencies();

  runApp(const CodiApp());
}

/// Main application widget with ScreenUtil initialization
class CodiApp extends StatelessWidget {
  const CodiApp({super.key});

  @override
  Widget build(BuildContext context) {
    return ScreenUtilInit(
      designSize: const Size(375, 812),
      minTextAdapt: true,
      splitScreenMode: true,
      builder: (context, child) {
        return const App();
      },
    );
  }
}
