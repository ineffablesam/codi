/// Backend configuration card widget for OAuth connect and manual config
library;

import 'package:flutter/material.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:get/get.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../../../core/constants/app_colors.dart';
import '../../../core/utils/sf_font.dart';

/// Compact card showing backend provider with Connect button or Connected status
class BackendProviderCard extends StatelessWidget {
  final String id;
  final Widget iconWidget;
  final String title;
  final String description;
  final List<String> features;
  final List<Color> gradientColors;
  final bool isSelected;
  final bool isConnected;
  final bool isConnecting;
  final bool showManualConfig;
  final VoidCallback onSelect;
  final VoidCallback? onConnect;
  final VoidCallback? onDisconnect;
  final VoidCallback? onManualConfig;

  const BackendProviderCard({
    super.key,
    required this.id,
    required this.iconWidget,
    required this.title,
    required this.description,
    required this.features,
    required this.gradientColors,
    required this.isSelected,
    required this.isConnected,
    this.isConnecting = false,
    this.showManualConfig = false,
    required this.onSelect,
    this.onConnect,
    this.onDisconnect,
    this.onManualConfig,
  });

  @override
  Widget build(BuildContext context) {
    final primaryColor = gradientColors.first;

    return GestureDetector(
      onTap: onSelect,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        padding: EdgeInsets.all(14.r),
        decoration: BoxDecoration(
          color: isSelected
              ? primaryColor.withOpacity(0.1)
              : AppColors.surfaceDark,
          borderRadius: BorderRadius.circular(14.r),
          border: Border.all(
            color:
                isSelected ? primaryColor.withOpacity(0.4) : Colors.transparent,
            width: 1.5,
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header row
            Row(
              children: [
                // Icon
                Container(
                  width: 40.r,
                  height: 40.r,
                  decoration: BoxDecoration(
                    color: primaryColor.withOpacity(0.15),
                    borderRadius: BorderRadius.circular(10.r),
                  ),
                  child: Center(child: iconWidget),
                ),
                SizedBox(width: 12.w),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        title,
                        style: SFPro.semibold(
                          fontSize: 15.sp,
                          color: AppColors.textInverse,
                        ),
                      ),
                      SizedBox(height: 2.h),
                      // Connection status
                      if (isConnected)
                        Row(
                          children: [
                            Icon(
                              LucideIcons.circleCheck,
                              color: AppColors.success,
                              size: 12.r,
                            ),
                            SizedBox(width: 4.w),
                            Text(
                              'Connected',
                              style: SFPro.medium(
                                fontSize: 11.sp,
                                color: AppColors.success,
                              ),
                            ),
                          ],
                        )
                      else
                        Text(
                          'Not connected',
                          style: SFPro.regular(
                            fontSize: 11.sp,
                            color: AppColors.textSecondary,
                          ),
                        ),
                    ],
                  ),
                ),
                // Selection indicator
                AnimatedContainer(
                  duration: const Duration(milliseconds: 200),
                  width: 22.r,
                  height: 22.r,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: isSelected ? primaryColor : Colors.transparent,
                    border: Border.all(
                      color: isSelected
                          ? primaryColor
                          : AppColors.textSecondary.withOpacity(0.3),
                      width: 1.5,
                    ),
                  ),
                  child: isSelected
                      ? Icon(LucideIcons.check, color: Colors.white, size: 12.r)
                      : null,
                ),
              ],
            ),
            SizedBox(height: 10.h),
            // Description
            Text(
              description,
              style: SFPro.regular(
                fontSize: 12.sp,
                color: AppColors.textSecondary,
              ),
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
            SizedBox(height: 8.h),
            // Features
            Wrap(
              spacing: 6.w,
              runSpacing: 4.h,
              children: features.map((f) {
                return Container(
                  padding: EdgeInsets.symmetric(horizontal: 6.w, vertical: 2.h),
                  decoration: BoxDecoration(
                    color: primaryColor.withOpacity(0.08),
                    borderRadius: BorderRadius.circular(4.r),
                  ),
                  child: Text(
                    f,
                    style: SFPro.medium(
                      fontSize: 9.sp,
                      color: primaryColor.withOpacity(0.8),
                    ),
                  ),
                );
              }).toList(),
            ),
            SizedBox(height: 12.h),
            // Action button
            SizedBox(
              width: double.infinity,
              height: 36.h,
              child: _buildActionButton(primaryColor),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildActionButton(Color primaryColor) {
    if (showManualConfig) {
      return OutlinedButton.icon(
        onPressed: onManualConfig,
        icon: Icon(LucideIcons.settings, size: 14.r),
        label: Text('Configure', style: SFPro.medium(fontSize: 12.sp)),
        style: OutlinedButton.styleFrom(
          padding: EdgeInsets.symmetric(horizontal: 12.w),
          side: BorderSide(color: primaryColor.withOpacity(0.4)),
          foregroundColor: primaryColor,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(8.r),
          ),
        ),
      );
    }

    if (isConnected) {
      return OutlinedButton.icon(
        onPressed: onDisconnect,
        icon: Icon(LucideIcons.unlink, size: 14.r),
        label: Text('Disconnect', style: SFPro.medium(fontSize: 12.sp)),
        style: OutlinedButton.styleFrom(
          padding: EdgeInsets.symmetric(horizontal: 12.w),
          side: BorderSide(color: AppColors.error.withOpacity(0.4)),
          foregroundColor: AppColors.error,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(8.r),
          ),
        ),
      );
    }

    return ElevatedButton.icon(
      onPressed: isConnecting ? null : onConnect,
      icon: isConnecting
          ? SizedBox(
              width: 14.r,
              height: 14.r,
              child: CircularProgressIndicator(
                strokeWidth: 2,
                valueColor: AlwaysStoppedAnimation<Color>(
                    Colors.white.withOpacity(0.7)),
              ),
            )
          : Icon(LucideIcons.link, size: 14.r),
      label: Text(
        isConnecting ? 'Connecting...' : 'Connect',
        style: SFPro.medium(fontSize: 12.sp),
      ),
      style: ElevatedButton.styleFrom(
        padding: EdgeInsets.symmetric(horizontal: 12.w),
        // backgroundColor: primaryColor,
        foregroundColor: Colors.white,
        disabledBackgroundColor: primaryColor.withOpacity(0.5),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(8.r),
        ),
        elevation: 0,
      ),
    );
  }
}

/// Manual Serverpod configuration dialog
class ServerpodConfigDialog extends StatefulWidget {
  final void Function(String serverUrl, String? apiKey) onSave;

  const ServerpodConfigDialog({super.key, required this.onSave});

  @override
  State<ServerpodConfigDialog> createState() => _ServerpodConfigDialogState();
}

class _ServerpodConfigDialogState extends State<ServerpodConfigDialog> {
  final _serverUrlController = TextEditingController();
  final _apiKeyController = TextEditingController();

  @override
  void dispose() {
    _serverUrlController.dispose();
    _apiKeyController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      backgroundColor: AppColors.surfaceDark,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16.r),
      ),
      title: Text(
        'Configure Serverpod',
        style: SFPro.bold(
          fontSize: 18.sp,
          color: AppColors.textInverse,
        ),
      ),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            'Enter your Serverpod server details.',
            style: SFPro.regular(
              fontSize: 13.sp,
              color: AppColors.textSecondary,
            ),
          ),
          SizedBox(height: 16.h),
          TextField(
            controller: _serverUrlController,
            style: SFPro.regular(fontSize: 14.sp),
            decoration: InputDecoration(
              labelText: 'Server URL',
              hintText: 'https://api.myapp.com',
              prefixIcon: Icon(LucideIcons.server, size: 18.r),
              contentPadding:
                  EdgeInsets.symmetric(horizontal: 12.w, vertical: 12.h),
            ),
          ),
          SizedBox(height: 12.h),
          TextField(
            controller: _apiKeyController,
            style: SFPro.regular(fontSize: 14.sp),
            decoration: InputDecoration(
              labelText: 'API Key (Optional)',
              hintText: 'sk-...',
              prefixIcon: Icon(LucideIcons.key, size: 18.r),
              contentPadding:
                  EdgeInsets.symmetric(horizontal: 12.w, vertical: 12.h),
            ),
            obscureText: true,
          ),
        ],
      ),
      actions: [
        TextButton(
          onPressed: () => Get.back(),
          child: Text('Cancel', style: SFPro.medium(fontSize: 14.sp)),
        ),
        ElevatedButton(
          onPressed: () {
            if (_serverUrlController.text.isNotEmpty) {
              widget.onSave(
                _serverUrlController.text,
                _apiKeyController.text.isEmpty ? null : _apiKeyController.text,
              );
              Get.back();
            }
          },
          style: ElevatedButton.styleFrom(
            elevation: 0,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(8.r),
            ),
          ),
          child: Text('Save', style: SFPro.medium(fontSize: 14.sp)),
        ),
      ],
    );
  }
}
