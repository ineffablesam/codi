/// Backend configuration card widget for OAuth connect and manual config
library;

import 'package:flutter/material.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:get/get.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../../core/constants/app_colors.dart';

/// Card showing backend provider with Connect button or Connected status
class BackendProviderCard extends StatelessWidget {
  final String id;
  final String icon;
  final String title;
  final String description;
  final List<String> features;
  final List<String> gradientColors;
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
    required this.icon,
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

  Color _parseColor(String hex) {
    return Color(int.parse(hex.replaceFirst('#', '0xFF')));
  }

  @override
  Widget build(BuildContext context) {
    final primaryColor = _parseColor(gradientColors.first);
    final secondaryColor = _parseColor(gradientColors.last);

    return GestureDetector(
      onTap: onSelect,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        padding: EdgeInsets.all(20.r),
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: isSelected
                ? [
                    primaryColor.withOpacity(0.15),
                    secondaryColor.withOpacity(0.08),
                  ]
                : [
                    AppColors.surface,
                    AppColors.surface.withOpacity(0.8),
                  ],
          ),
          borderRadius: BorderRadius.circular(20.r),
          border: Border.all(
            color: isSelected
                ? primaryColor.withOpacity(0.6)
                : AppColors.border.withOpacity(0.3),
            width: isSelected ? 2 : 1,
          ),
          boxShadow: isSelected
              ? [
                  BoxShadow(
                    color: primaryColor.withOpacity(0.2),
                    blurRadius: 15,
                    spreadRadius: 1,
                  )
                ]
              : null,
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header
            Row(
              children: [
                Container(
                  width: 52.r,
                  height: 52.r,
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      colors: [primaryColor, secondaryColor],
                    ),
                    borderRadius: BorderRadius.circular(14.r),
                  ),
                  child: Center(
                    child: Text(icon, style: TextStyle(fontSize: 26.sp)),
                  ),
                ),
                SizedBox(width: 14.w),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        title,
                        style: GoogleFonts.inter(
                          fontSize: 18.sp,
                          fontWeight: FontWeight.w700,
                          color: isSelected
                              ? primaryColor
                              : AppColors.textPrimary,
                        ),
                      ),
                      SizedBox(height: 2.h),
                      // Connection status
                      if (isConnected)
                        Row(
                          children: [
                            Icon(
                              Icons.check_circle,
                              color: AppColors.success,
                              size: 14.r,
                            ),
                            SizedBox(width: 4.w),
                            Text(
                              'Connected',
                              style: GoogleFonts.inter(
                                fontSize: 12.sp,
                                fontWeight: FontWeight.w500,
                                color: AppColors.success,
                              ),
                            ),
                          ],
                        )
                      else
                        Text(
                          'Not connected',
                          style: GoogleFonts.inter(
                            fontSize: 12.sp,
                            color: AppColors.textSecondary,
                          ),
                        ),
                    ],
                  ),
                ),
                // Selection indicator
                AnimatedContainer(
                  duration: const Duration(milliseconds: 200),
                  width: 26.r,
                  height: 26.r,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: isSelected ? primaryColor : Colors.transparent,
                    border: Border.all(
                      color: isSelected ? primaryColor : AppColors.border,
                      width: 2,
                    ),
                  ),
                  child: isSelected
                      ? Icon(Icons.check, color: Colors.white, size: 14.r)
                      : null,
                ),
              ],
            ),
            SizedBox(height: 12.h),
            // Description
            Text(
              description,
              style: GoogleFonts.inter(
                fontSize: 13.sp,
                color: AppColors.textSecondary,
                height: 1.4,
              ),
            ),
            SizedBox(height: 12.h),
            // Features
            Wrap(
              spacing: 6.w,
              runSpacing: 6.h,
              children: features.map((f) {
                return Container(
                  padding: EdgeInsets.symmetric(horizontal: 8.w, vertical: 3.h),
                  decoration: BoxDecoration(
                    color: primaryColor.withOpacity(0.1),
                    borderRadius: BorderRadius.circular(6.r),
                  ),
                  child: Text(
                    f,
                    style: GoogleFonts.inter(
                      fontSize: 10.sp,
                      fontWeight: FontWeight.w500,
                      color: primaryColor,
                    ),
                  ),
                );
              }).toList(),
            ),
            SizedBox(height: 16.h),
            // Action buttons
            Row(
              children: [
                if (showManualConfig) ...[
                  Expanded(
                    child: OutlinedButton.icon(
                      onPressed: onManualConfig,
                      icon: Icon(Icons.settings, size: 16.r),
                      label: const Text('Configure'),
                      style: OutlinedButton.styleFrom(
                        padding: EdgeInsets.symmetric(vertical: 10.h),
                        side: BorderSide(color: primaryColor.withOpacity(0.5)),
                        foregroundColor: primaryColor,
                      ),
                    ),
                  ),
                ] else if (isConnected) ...[
                  Expanded(
                    child: OutlinedButton.icon(
                      onPressed: onDisconnect,
                      icon: Icon(Icons.link_off, size: 16.r),
                      label: const Text('Disconnect'),
                      style: OutlinedButton.styleFrom(
                        padding: EdgeInsets.symmetric(vertical: 10.h),
                        side: BorderSide(color: AppColors.error.withOpacity(0.5)),
                        foregroundColor: AppColors.error,
                      ),
                    ),
                  ),
                ] else ...[
                  Expanded(
                    child: ElevatedButton.icon(
                      onPressed: isConnecting ? null : onConnect,
                      icon: isConnecting
                          ? SizedBox(
                              width: 16.r,
                              height: 16.r,
                              child: const CircularProgressIndicator(strokeWidth: 2),
                            )
                          : Icon(Icons.link, size: 16.r),
                      label: Text(isConnecting ? 'Connecting...' : 'Connect Account'),
                      style: ElevatedButton.styleFrom(
                        padding: EdgeInsets.symmetric(vertical: 10.h),
                        backgroundColor: primaryColor,
                      ),
                    ),
                  ),
                ],
              ],
            ),
          ],
        ),
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
      backgroundColor: AppColors.surface,
      title: Text(
        'Configure Serverpod',
        style: GoogleFonts.inter(
          fontWeight: FontWeight.w700,
          color: AppColors.textPrimary,
        ),
      ),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            'Enter your Serverpod server details.',
            style: GoogleFonts.inter(
              fontSize: 14.sp,
              color: AppColors.textSecondary,
            ),
          ),
          SizedBox(height: 20.h),
          TextField(
            controller: _serverUrlController,
            decoration: InputDecoration(
              labelText: 'Server URL',
              hintText: 'https://api.myapp.com',
              prefixIcon: const Icon(Icons.dns_outlined),
            ),
          ),
          SizedBox(height: 16.h),
          TextField(
            controller: _apiKeyController,
            decoration: InputDecoration(
              labelText: 'API Key (Optional)',
              hintText: 'sk-...',
              prefixIcon: const Icon(Icons.key_outlined),
            ),
            obscureText: true,
          ),
        ],
      ),
      actions: [
        TextButton(
          onPressed: () => Get.back(),
          child: const Text('Cancel'),
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
          child: const Text('Save'),
        ),
      ],
    );
  }
}
