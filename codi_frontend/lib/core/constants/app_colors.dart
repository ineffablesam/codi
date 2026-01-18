/// Application color palette
library;

import 'package:flutter/material.dart';

/// Application colors following Material 3 design
class AppColors {
  AppColors._();

  // Primary colors
  static const Color primary = Color(0xFF6366F1); // Indigo
  static const Color primaryLight = Color(0xFF818CF8);
  static const Color primaryDark = Color(0xFF4F46E5);

  // Secondary colors
  static const Color secondary = Color(0xFF8B5CF6); // Purple
  static const Color secondaryLight = Color(0xFFA78BFA);
  static const Color secondaryDark = Color(0xFF7C3AED);

  // Accent colors
  static const Color accent = Color(0xFF10B981); // Emerald
  static const Color accentLight = Color(0xFF34D399);
  static const Color accentDark = Color(0xFF059669);

  // Status colors
  static const Color success = Color(0xFF22C55E);
  static const Color warning = Color(0xFFF59E0B);
  static const Color error = Color(0xFFEF4444);
  static const Color info = Color(0xFF3B82F6);

  // Background colors (Light theme)
  static const Color background = Color(0xFFF9FAFB);
  static const Color surface = Color(0xFFFFFFFF);
  static const Color cardBackground = Color(0xFFFFFFFF);
  static const Color inputBackground = Color(0xFFF3F4F6);

  // Background colors (Dark theme)
  static const Color backgroundDark = Color(0xFF1E1E1E); // Terminal dark background
  static const Color surfaceDark = Color(0xFF252526); // Header background
  static const Color surfaceDarkVariant = Color(0xFF2D2D2D); // Toolbar background

  // Text colors
  static const Color textPrimary = Color(0xFF111827);
  static const Color textSecondary = Color(0xFF6B7280);
  static const Color textTertiary = Color(0xFFB0B0B0);
  static const Color textInverse = Color(0xFFFFFFFF);

  // Border colors
  static const Color border = Color(0xFFE5E7EB);
  static const Color borderDark = Color(0xFFD1D5DB);
  static const Color divider = Color(0xFFF3F4F6);

  // Agent-specific colors
  static const Color planner = Color(0xFF8B5CF6);
  static const Color flutterEngineer = Color(0xFF3B82F6);
  static const Color codeReviewer = Color(0xFF10B981);
  static const Color gitOperator = Color(0xFFF59E0B);
  static const Color buildDeploy = Color(0xFFEF4444);
  static const Color memory = Color(0xFF6366F1);

  // Message type colors
  static const Color messageUser = Color(0xFF6366F1);
  static const Color messageAgent = Color(0xFFF3F4F6);
  static const Color fileCreate = Color(0xFF10B981);
  static const Color fileUpdate = Color(0xFF3B82F6);
  static const Color fileDelete = Color(0xFFEF4444);
  static const Color gitSuccess = Color(0xFFF0FDF4);
  static const Color buildProgress = Color(0xFFEFF6FF);
  static const Color deploymentSuccess = Color(0xFFF0FDF4);
  static const Color errorBackground = Color(0xFFFEF2F2);
  static const Color warningBackground = Color(0xFFFEF3C7);

  // GitHub brand color
  static const Color github = Color(0xFFF0FDF4);

  // Google brand color
  static const Color google = Color(0xFFF0FDF4);
}
