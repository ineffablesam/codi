/// Codi App - GetMaterialApp configuration
library;

import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'package:google_fonts/google_fonts.dart';

import 'config/routes.dart';
import 'config/theme.dart';

/// Root application widget using GetMaterialApp
class App extends StatelessWidget {
  const App({super.key});

  @override
  Widget build(BuildContext context) {
    return GetMaterialApp(
      title: 'Codi',
      debugShowCheckedModeBanner: false,
      
      // Theme configuration
      theme: AppTheme.lightTheme,
      darkTheme: AppTheme.darkTheme,
      themeMode: ThemeMode.light,
      
      // Default text style
      builder: (context, child) {
        return MediaQuery(
          data: MediaQuery.of(context).copyWith(
            textScaler: const TextScaler.linear(1.0),
          ),
          child: child ?? const SizedBox.shrink(),
        );
      },
      
      // GetX routing
      initialRoute: AppRoutes.splash,
      getPages: AppRoutes.routes,
      
      // Transitions
      defaultTransition: Transition.cupertino,
      transitionDuration: const Duration(milliseconds: 300),
      
      // Localization (can be extended)
      locale: const Locale('en', 'US'),
      fallbackLocale: const Locale('en', 'US'),
    );
  }
}
