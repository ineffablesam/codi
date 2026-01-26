/// Settings screen with enhanced UX
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
        elevation: 0,
      ),
      body: ListView(
        padding: EdgeInsets.symmetric(horizontal: 16.w, vertical: 8.h),
        children: [
          SizedBox(height: 8.h),

          // User profile card
          _buildProfileCard(authController),
          SizedBox(height: 32.h),

          // Preferences section
          _buildSectionHeader(AppStrings.appearance),
          SizedBox(height: 12.h),
          _buildSettingsCard([
            _buildToggleTile(
              icon: Icons.notifications_outlined,
              title: AppStrings.notifications,
              subtitle: 'Get updates and alerts',
              value: SharedPrefs.getNotifications(),
              onChanged: (value) => SharedPrefs.setNotifications(value),
            ),
          ]),
          SizedBox(height: 32.h),

          // About section
          _buildSectionHeader(AppStrings.about),
          SizedBox(height: 12.h),
          _buildSettingsCard([
            _buildInfoTile(
              icon: Icons.info_outline,
              title: AppStrings.version,
              subtitle: '1.0.0',
            ),
            _buildDivider(),
            _buildLinkTile(
              icon: Icons.privacy_tip_outlined,
              title: AppStrings.privacyPolicy,
              onTap: () => _openUrl('https://codi.app/privacy'),
            ),
            _buildDivider(),
            _buildLinkTile(
              icon: Icons.article_outlined,
              title: AppStrings.termsOfService,
              onTap: () => _openUrl('https://codi.app/terms'),
            ),
            _buildDivider(),
            _buildLinkTile(
              icon: Icons.bug_report_outlined,
              title: 'Report an Issue',
              onTap: () => _openUrl('https://codi.app/support'),
            ),
          ]),
          SizedBox(height: 32.h),

          // Logout button
          _buildLogoutButton(authController),
          SizedBox(height: 48.h),
        ],
      ),
    );
  }

  Widget _buildProfileCard(AuthController authController) {
    return Obx(() {
      final user = authController.currentUser.value;
      return Container(
        padding: EdgeInsets.all(20.r),
        decoration: BoxDecoration(
          color: Get.theme.cardTheme.color,
          borderRadius: BorderRadius.circular(16.r),
          border: Border.all(
            color: Get.theme.focusColor.withOpacity(0.08),
            width: 1.5,
          ),
          boxShadow: [
            BoxShadow(
              color: Get.theme.shadowColor.withOpacity(0.03),
              blurRadius: 10,
              offset: Offset(0, 2),
            ),
          ],
        ),
        child: Row(
          children: [
            Container(
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                border: Border.all(
                  color: Get.theme.focusColor.withOpacity(0.1),
                  width: 2,
                ),
              ),
              child: CircleAvatar(
                radius: 34.r,
                backgroundImage: NetworkImage(
                  ImagePlaceholders.userAvatarWithFallback(
                    user?.githubAvatarUrl,
                    user?.githubUsername,
                  ),
                ),
              ),
            ),
            SizedBox(width: 16.w),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Flexible(
                        child: Text(
                          user?.displayName ?? 'User',
                          style: GoogleFonts.inter(
                            fontSize: 18.sp,
                            fontWeight: FontWeight.w600,
                            color: Get.textTheme.titleLarge?.color,
                            letterSpacing: -0.3,
                          ),
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                      SizedBox(width: 6.w),
                      Icon(
                        Icons.verified,
                        color: Get.theme.primaryColor,
                        size: 20.r,
                      ),
                    ],
                  ),
                  SizedBox(height: 6.h),
                  Text(
                    '@${user?.githubUsername ?? 'unknown'}',
                    style: GoogleFonts.inter(
                      fontSize: 14.sp,
                      color: Get.textTheme.bodyMedium?.color?.withOpacity(0.7),
                      letterSpacing: -0.2,
                    ),
                  ),
                ],
              ),
            ),
            Icon(
              Icons.chevron_right,
              color: Get.textTheme.bodySmall?.color?.withOpacity(0.4),
              size: 20.r,
            ),
          ],
        ),
      );
    });
  }

  Widget _buildSectionHeader(String title) {
    return Padding(
      padding: EdgeInsets.only(left: 4.w, bottom: 0.h),
      child: Text(
        title.toUpperCase(),
        style: GoogleFonts.inter(
          fontSize: 12.sp,
          fontWeight: FontWeight.w700,
          color: Get.textTheme.bodySmall?.color?.withOpacity(0.6),
          letterSpacing: 0.8,
        ),
      ),
    );
  }

  Widget _buildSettingsCard(List<Widget> children) {
    return Container(
      decoration: BoxDecoration(
        color: Get.theme.cardTheme.color,
        borderRadius: BorderRadius.circular(16.r),
        border: Border.all(
          color: Get.theme.focusColor.withOpacity(0.08),
          width: 1.5,
        ),
        boxShadow: [
          BoxShadow(
            color: Get.theme.shadowColor.withOpacity(0.03),
            blurRadius: 10,
            offset: Offset(0, 2),
          ),
        ],
      ),
      child: Column(children: children),
    );
  }

  Widget _buildToggleTile({
    required IconData icon,
    required String title,
    required String subtitle,
    required bool value,
    required ValueChanged<bool> onChanged,
  }) {
    return StatefulBuilder(
      builder: (context, setState) {
        return ListTile(
          contentPadding: EdgeInsets.symmetric(horizontal: 20.w, vertical: 8.h),
          leading: Container(
            padding: EdgeInsets.all(10.r),
            decoration: BoxDecoration(
              color: Get.theme.primaryColor.withOpacity(0.08),
              borderRadius: BorderRadius.circular(10.r),
            ),
            child: Icon(
              icon,
              color: Get.theme.primaryColor,
              size: 20.r,
            ),
          ),
          title: Text(
            title,
            style: GoogleFonts.inter(
              fontSize: 15.sp,
              fontWeight: FontWeight.w600,
              letterSpacing: -0.2,
            ),
          ),
          subtitle: Padding(
            padding: EdgeInsets.only(top: 4.h),
            child: Text(
              subtitle,
              style: GoogleFonts.inter(
                fontSize: 13.sp,
                color: Get.textTheme.bodySmall?.color?.withOpacity(0.6),
                letterSpacing: -0.1,
              ),
            ),
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
      contentPadding: EdgeInsets.symmetric(horizontal: 20.w, vertical: 12.h),
      leading: Container(
        padding: EdgeInsets.all(10.r),
        decoration: BoxDecoration(
          color: Get.theme.focusColor.withOpacity(0.05),
          borderRadius: BorderRadius.circular(10.r),
        ),
        child: Icon(
          icon,
          color: Get.textTheme.bodyMedium?.color?.withOpacity(0.8),
          size: 20.r,
        ),
      ),
      title: Text(
        title,
        style: GoogleFonts.inter(
          fontSize: 15.sp,
          fontWeight: FontWeight.w500,
          letterSpacing: -0.2,
        ),
      ),
      trailing: Container(
        padding: EdgeInsets.symmetric(horizontal: 12.w, vertical: 6.h),
        decoration: BoxDecoration(
          color: Get.theme.focusColor.withOpacity(0.06),
          borderRadius: BorderRadius.circular(8.r),
          border: Border.all(
            color: Get.theme.focusColor.withOpacity(0.1),
            width: 1,
          ),
        ),
        child: Text(
          subtitle,
          style: GoogleFonts.inter(
            fontSize: 13.sp,
            fontWeight: FontWeight.w600,
            color: Get.textTheme.bodyMedium?.color,
            letterSpacing: -0.1,
          ),
        ),
      ),
    );
  }

  Widget _buildLinkTile({
    required IconData icon,
    required String title,
    required VoidCallback onTap,
  }) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(0),
      child: ListTile(
        contentPadding: EdgeInsets.symmetric(horizontal: 20.w, vertical: 12.h),
        leading: Container(
          padding: EdgeInsets.all(10.r),
          decoration: BoxDecoration(
            color: Get.theme.focusColor.withOpacity(0.05),
            borderRadius: BorderRadius.circular(10.r),
          ),
          child: Icon(
            icon,
            color: Get.textTheme.bodyMedium?.color?.withOpacity(0.8),
            size: 20.r,
          ),
        ),
        title: Text(
          title,
          style: GoogleFonts.inter(
            fontSize: 15.sp,
            fontWeight: FontWeight.w500,
            letterSpacing: -0.2,
          ),
        ),
        trailing: Icon(
          Icons.chevron_right,
          color: Get.textTheme.bodySmall?.color?.withOpacity(0.4),
          size: 20.r,
        ),
      ),
    );
  }

  Widget _buildLogoutButton(AuthController authController) {
    return Container(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(12.r),
        border: Border.all(
          color: AppColors.error.withOpacity(0.2),
          width: 1.5,
        ),
      ),
      child: ElevatedButton(
        onPressed: authController.confirmLogout,
        style: ElevatedButton.styleFrom(
          backgroundColor: AppColors.error,
          foregroundColor: Colors.white,
          elevation: 0,
          padding: EdgeInsets.symmetric(vertical: 16.h),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12.r),
          ),
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.logout, size: 20.r),
            SizedBox(width: 8.w),
            Text(
              AppStrings.logout,
              style: GoogleFonts.inter(
                fontSize: 15.sp,
                fontWeight: FontWeight.w600,
                letterSpacing: -0.2,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildDivider() {
    return Divider(
      height: 1,
      thickness: 1,
      indent: 68.w,
      endIndent: 20.w,
      color: Get.theme.focusColor.withOpacity(0.06),
    );
  }

  void _openUrl(String url) async {
    final uri = Uri.parse(url);
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    }
  }
}
