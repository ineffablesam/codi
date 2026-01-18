/// Settings screen
library;

import 'package:flutter/material.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:get/get.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../../core/constants/app_colors.dart';
import '../../../core/constants/app_strings.dart';
import '../../../core/constants/image_placeholders.dart';
import '../../../core/storage/shared_prefs.dart';
import '../../auth/controllers/auth_controller.dart';

/// Settings screen
class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final authController = Get.find<AuthController>();

    return Scaffold(
      backgroundColor: Get.theme.scaffoldBackgroundColor,
      appBar: AppBar(
        title: Text(
          AppStrings.settings,
          style: GoogleFonts.inter(fontWeight: FontWeight.w600),
        ),
      ),
      body: ListView(
        padding: EdgeInsets.all(16.r),
        children: [
          // User profile card
          _buildProfileCard(authController),
          SizedBox(height: 24.h),

          // Appearance section
          _buildSectionHeader(AppStrings.appearance),
          SizedBox(height: 8.h),
          _buildSettingsCard([
            _buildToggleTile(
              icon: Icons.dark_mode,
              title: AppStrings.darkMode,
              value: SharedPrefs.getDarkMode(),
              onChanged: (value) async {
                await SharedPrefs.setDarkMode(value);
                Get.changeThemeMode(value ? ThemeMode.dark : ThemeMode.light);
              },
            ),
            _buildDivider(),
            _buildToggleTile(
              icon: Icons.notifications,
              title: AppStrings.notifications,
              value: SharedPrefs.getNotifications(),
              onChanged: (value) => SharedPrefs.setNotifications(value),
            ),
          ]),
          SizedBox(height: 24.h),

          // About section
          _buildSectionHeader(AppStrings.about),
          SizedBox(height: 8.h),
          _buildSettingsCard([
            _buildInfoTile(
              icon: Icons.info_outline,
              title: AppStrings.version,
              subtitle: '1.0.0',
            ),
            _buildDivider(),
            _buildLinkTile(
              icon: Icons.description_outlined,
              title: AppStrings.privacyPolicy,
              onTap: () => _openUrl('https://codi.app/privacy'),
            ),
            _buildDivider(),
            _buildLinkTile(
              icon: Icons.article_outlined,
              title: AppStrings.termsOfService,
              onTap: () => _openUrl('https://codi.app/terms'),
            ),
          ]),
          SizedBox(height: 24.h),

          // Logout button
          ElevatedButton(
            onPressed: authController.confirmLogout,
            style: ElevatedButton.styleFrom(
              backgroundColor: AppColors.error,
              foregroundColor: Colors.white,
            ),
            child: Text(AppStrings.logout),
          ),
          SizedBox(height: 32.h),
        ],
      ),
    );
  }

  Widget _buildProfileCard(AuthController authController) {
    return Obx(() {
      final user = authController.currentUser.value;
      return Container(
        padding: EdgeInsets.all(16.r),
        decoration: BoxDecoration(
          color: Get.theme.cardTheme.color,
          borderRadius: BorderRadius.circular(12.r),
          border: Border.all(color: Get.theme.dividerColor),
        ),
        child: Row(
          children: [
            CircleAvatar(
              radius: 32.r,
              backgroundImage: NetworkImage(
                ImagePlaceholders.userAvatarWithFallback(
                  user?.githubAvatarUrl,
                  user?.githubUsername,
                ),
              ),
            ),
            SizedBox(width: 16.w),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    user?.displayName ?? 'User',
                    style: GoogleFonts.inter(
                      fontSize: 18.sp,
                      fontWeight: FontWeight.w600,
                      color: Get.textTheme.titleLarge?.color,
                    ),
                  ),
                  SizedBox(height: 4.h),
                  Text(
                    '@${user?.githubUsername ?? 'unknown'}',
                    style: GoogleFonts.inter(
                      fontSize: 14.sp,
                      color: Get.textTheme.bodyMedium?.color,
                    ),
                  ),
                ],
              ),
            ),
            Icon(
              Icons.verified,
              color: Get.theme.primaryColor,
              size: 24.r,
            ),
          ],
        ),
      );
    });
  }

  Widget _buildSectionHeader(String title) {
    return Text(
      title,
      style: GoogleFonts.inter(
        fontSize: 13.sp,
        fontWeight: FontWeight.w600,
        color: Get.textTheme.bodySmall?.color,
      ),
    );
  }

  Widget _buildSettingsCard(List<Widget> children) {
    return Container(
      decoration: BoxDecoration(
        color: Get.theme.cardTheme.color,
        borderRadius: BorderRadius.circular(12.r),
        border: Border.all(color: Get.theme.dividerColor),
      ),
      child: Column(children: children),
    );
  }

  Widget _buildToggleTile({
    required IconData icon,
    required String title,
    required bool value,
    required ValueChanged<bool> onChanged,
  }) {
    return StatefulBuilder(
      builder: (context, setState) {
        return ListTile(
          leading: Icon(icon, color: Get.textTheme.bodyMedium?.color),
          title: Text(
            title,
            style: GoogleFonts.inter(fontSize: 15.sp),
          ),
          trailing: Switch(
            value: value,
            onChanged: (newValue) {
              setState(() {});
              onChanged(newValue);
            },
            activeColor: Get.theme.primaryColor,
          ),
        );
      },
    );
  }

  Widget _buildInfoTile({
    required IconData icon,
    required String title,
    required String subtitle,
  }) {
    return ListTile(
      leading: Icon(icon, color: Get.textTheme.bodyMedium?.color),
      title: Text(
        title,
        style: GoogleFonts.inter(fontSize: 15.sp),
      ),
      trailing: Text(
        subtitle,
        style: GoogleFonts.inter(
          fontSize: 14.sp,
          color: Get.textTheme.bodyMedium?.color,
        ),
      ),
    );
  }

  Widget _buildLinkTile({
    required IconData icon,
    required String title,
    required VoidCallback onTap,
  }) {
    return ListTile(
      leading: Icon(icon, color: Get.textTheme.bodyMedium?.color),
      title: Text(
        title,
        style: GoogleFonts.inter(fontSize: 15.sp),
      ),
      trailing: Icon(
        Icons.chevron_right,
        color: Get.textTheme.bodySmall?.color,
      ),
      onTap: onTap,
    );
  }

  Widget _buildDivider() {
    return Divider(height: 1, indent: 56.w, color: Get.theme.dividerColor);
  }

  void _openUrl(String url) async {
    final uri = Uri.parse(url);
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    }
  }
}
