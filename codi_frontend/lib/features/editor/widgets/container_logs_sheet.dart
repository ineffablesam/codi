import 'package:flutter/material.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:get/get.dart';
import 'package:iconsax_flutter/iconsax_flutter.dart';

import '../controllers/container_logs_controller.dart';

/// Bottom sheet for viewing container logs
class ContainerLogsSheet extends StatefulWidget {
  final String containerId;
  final String? containerName;

  const ContainerLogsSheet({
    super.key,
    required this.containerId,
    this.containerName,
  });

  static Future<void> show(
    BuildContext context, {
    required String containerId,
    String? containerName,
  }) {
    return showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => ContainerLogsSheet(
        containerId: containerId,
        containerName: containerName,
      ),
    );
  }

  @override
  State<ContainerLogsSheet> createState() => _ContainerLogsSheetState();
}

class _ContainerLogsSheetState extends State<ContainerLogsSheet> {
  late final ContainerLogsController _controller;
  final ScrollController _scrollController = ScrollController();

  @override
  void initState() {
    super.initState();
    if (!Get.isRegistered<ContainerLogsController>()) {
      Get.put(ContainerLogsController());
    }
    _controller = Get.find<ContainerLogsController>();
    _controller.containerName.value = widget.containerName;
    
    // Initialize logs with proper deduplication
    _controller.initializeLogs(widget.containerId);

    // Auto-scroll when new logs arrive
    _controller.logs.listen((_) {
      if (_controller.autoScroll.value) {
        WidgetsBinding.instance.addPostFrameCallback((_) {
          if (_scrollController.hasClients) {
            _scrollController.animateTo(
              _scrollController.position.maxScrollExtent,
              duration: const Duration(milliseconds: 100),
              curve: Curves.easeOut,
            );
          }
        });
      }
    });
  }

  @override
  void dispose() {
    _controller.stopLogStream();
    _scrollController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      height: MediaQuery.of(context).size.height * 0.7,
      decoration: BoxDecoration(
        color: const Color(0xFF0D1117), // GitHub dark background
        borderRadius: BorderRadius.vertical(top: Radius.circular(20.r)),
      ),
      child: Column(
        children: [
          _buildHeader(),
          _buildToolbar(),
          Expanded(child: _buildLogViewer()),
        ],
      ),
    );
  }

  Widget _buildHeader() {
    return Container(
      padding: EdgeInsets.symmetric(horizontal: 16.w, vertical: 12.h),
      decoration: BoxDecoration(
        color: const Color(0xFF161B22),
        borderRadius: BorderRadius.vertical(top: Radius.circular(20.r)),
      ),
      child: Row(
        children: [
          // Handle bar
          Container(
            margin: EdgeInsets.only(right: 12.w),
            width: 40.w,
            height: 4.h,
            decoration: BoxDecoration(
              color: Colors.grey[700],
              borderRadius: BorderRadius.circular(2.r),
            ),
          ),
          Container(
            padding: EdgeInsets.all(6.w),
            decoration: BoxDecoration(
              color: Colors.green.withOpacity(0.15),
              borderRadius: BorderRadius.circular(6.r),
            ),
            child: Icon(Iconsax.monitor, color: Colors.green[400], size: 18.sp),
          ),
          SizedBox(width: 10.w),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  widget.containerName ?? 'Container Logs',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 15.sp,
                    fontWeight: FontWeight.w600,
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
                Obx(() => Text(
                  '${_controller.logs.length} lines',
                  style: TextStyle(
                    color: Colors.grey[500],
                    fontSize: 11.sp,
                  ),
                )),
              ],
            ),
          ),
          Obx(() => _buildStatusBadge()),
          IconButton(
            onPressed: () => Navigator.pop(context),
            icon: Icon(Icons.close, color: Colors.grey[400], size: 22.sp),
          ),
        ],
      ),
    );
  }

  Widget _buildStatusBadge() {
    final isLive = _controller.isStreaming.value;
    return Container(
      padding: EdgeInsets.symmetric(horizontal: 10.w, vertical: 5.h),
      decoration: BoxDecoration(
        color: isLive 
            ? Colors.green.withOpacity(0.15)
            : Colors.grey.withOpacity(0.15),
        borderRadius: BorderRadius.circular(20.r),
        border: Border.all(
          color: isLive 
              ? Colors.green.withOpacity(0.3)
              : Colors.grey.withOpacity(0.3),
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 6.w,
            height: 6.w,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: isLive ? Colors.green[400] : Colors.grey[500],
              boxShadow: isLive ? [
                BoxShadow(
                  color: Colors.green.withOpacity(0.5),
                  blurRadius: 4,
                  spreadRadius: 1,
                ),
              ] : null,
            ),
          ),
          SizedBox(width: 6.w),
          Text(
            isLive ? 'Live' : 'Paused',
            style: TextStyle(
              color: isLive ? Colors.green[400] : Colors.grey[500],
              fontSize: 11.sp,
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildToolbar() {
    return Container(
      padding: EdgeInsets.symmetric(horizontal: 12.w, vertical: 8.h),
      decoration: BoxDecoration(
        color: const Color(0xFF161B22),
        border: Border(
          bottom: BorderSide(color: Colors.grey[800]!, width: 0.5),
        ),
      ),
      child: SingleChildScrollView(
        physics: const BouncingScrollPhysics(),
        scrollDirection: Axis.horizontal,
        child: Row(
          children: [
            // Stream toggle
            Obx(() => _buildToolbarButton(
                  icon: _controller.isStreaming.value
                      ? Iconsax.pause
                      : Iconsax.play,
                  label: _controller.isStreaming.value ? 'Pause' : 'Resume',
                  onTap: () {
                    if (_controller.isStreaming.value) {
                      _controller.stopLogStream();
                    } else {
                      // Use resumeLogStream to avoid duplicates
                      _controller.resumeLogStream();
                    }
                  },
                )),
            SizedBox(width: 8.w),
            // Auto-scroll toggle
            Obx(() => _buildToolbarButton(
                  icon: Iconsax.arrow_down_1,
                  label: 'Auto-scroll',
                  isActive: _controller.autoScroll.value,
                  onTap: _controller.toggleAutoScroll,
                )),
            SizedBox(width: 8.w),
            // Clear logs
            _buildToolbarButton(
              icon: Iconsax.trash,
              label: 'Clear',
              onTap: _controller.clearLogs,
            ),
            SizedBox(width: 8.w),
            // Restart container
            _buildToolbarButton(
              icon: Iconsax.refresh,
              label: 'Restart',
              color: Colors.orange[400],
              onTap: () async {
                final success =
                    await _controller.restartContainer(widget.containerId);
                if (success) {
                  Get.snackbar('Success', 'Container restarting...',
                      backgroundColor: Colors.green, colorText: Colors.white);
                }
              },
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildToolbarButton({
    required IconData icon,
    required String label,
    bool isActive = false,
    Color? color,
    required VoidCallback onTap,
  }) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(6.r),
      child: Container(
        padding: EdgeInsets.symmetric(horizontal: 10.w, vertical: 6.h),
        decoration: BoxDecoration(
          color: isActive 
              ? Colors.blue.withOpacity(0.15)
              : Colors.grey.withOpacity(0.1),
          borderRadius: BorderRadius.circular(6.r),
          border: Border.all(
            color: isActive
                ? Colors.blue.withOpacity(0.4)
                : Colors.grey.withOpacity(0.2),
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 14.sp, color: color ?? (isActive ? Colors.blue[400] : Colors.grey[400])),
            SizedBox(width: 5.w),
            Text(
              label,
              style: TextStyle(
                color: color ?? (isActive ? Colors.blue[400] : Colors.grey[400]),
                fontSize: 11.sp,
                fontWeight: FontWeight.w500,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildLogViewer() {
    return Obx(() {
      if (_controller.isLoading.value && _controller.logs.isEmpty) {
        return Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              SizedBox(
                width: 32.w,
                height: 32.w,
                child: CircularProgressIndicator(
                  strokeWidth: 2,
                  color: Colors.blue[400],
                ),
              ),
              SizedBox(height: 12.h),
              Text(
                'Loading logs...',
                style: TextStyle(color: Colors.grey[500], fontSize: 14.sp),
              ),
            ],
          ),
        );
      }

      if (_controller.logs.isEmpty) {
        return Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Iconsax.document_text, size: 48.sp, color: Colors.grey[700]),
              SizedBox(height: 12.h),
              Text(
                'No logs yet',
                style: TextStyle(color: Colors.grey[500], fontSize: 16.sp),
              ),
              if (_controller.isStreaming.value)
                Padding(
                  padding: EdgeInsets.only(top: 8.h),
                  child: Text(
                    'Waiting for log output...',
                    style: TextStyle(color: Colors.grey[600], fontSize: 12.sp),
                  ),
                ),
            ],
          ),
        );
      }

      return ListView.builder(
        controller: _scrollController,
        padding: EdgeInsets.symmetric(horizontal: 12.w, vertical: 8.h),
        itemCount: _controller.logs.length,
        itemBuilder: (context, index) {
          final log = _controller.logs[index];
          final showTimeSeparator = _shouldShowTimeSeparator(index);
          
          return Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (showTimeSeparator) _buildTimeSeparator(log.timestamp),
              _buildLogLine(log),
            ],
          );
        },
      );
    });
  }

  /// Determine if we should show a time separator between log groups
  bool _shouldShowTimeSeparator(int index) {
    if (index == 0) return true;
    
    final current = _controller.logs[index];
    final previous = _controller.logs[index - 1];
    
    // Show separator if more than 30 seconds between logs
    final diff = current.timestamp.difference(previous.timestamp);
    return diff.inSeconds.abs() > 30;
  }

  Widget _buildTimeSeparator(DateTime timestamp) {
    return Padding(
      padding: EdgeInsets.only(top: 12.h, bottom: 6.h),
      child: Row(
        children: [
          Expanded(child: Divider(color: Colors.grey[800], thickness: 0.5)),
          Padding(
            padding: EdgeInsets.symmetric(horizontal: 12.w),
            child: Text(
              _formatTimestamp(timestamp),
              style: TextStyle(
                color: Colors.grey[600],
                fontSize: 10.sp,
                fontWeight: FontWeight.w500,
              ),
            ),
          ),
          Expanded(child: Divider(color: Colors.grey[800], thickness: 0.5)),
        ],
      ),
    );
  }

  String _formatTimestamp(DateTime timestamp) {
    final now = DateTime.now();
    final diff = now.difference(timestamp);
    
    if (diff.inMinutes < 1) {
      return 'Just now';
    } else if (diff.inHours < 1) {
      return '${diff.inMinutes}m ago';
    } else if (diff.inDays < 1) {
      return '${timestamp.hour.toString().padLeft(2, '0')}:${timestamp.minute.toString().padLeft(2, '0')}';
    } else {
      return '${timestamp.month}/${timestamp.day} ${timestamp.hour.toString().padLeft(2, '0')}:${timestamp.minute.toString().padLeft(2, '0')}';
    }
  }

  Widget _buildLogLine(LogLine log) {
    // Special styling for system messages
    if (log.isSystemMessage) {
      return _buildSystemLogLine(log);
    }
    
    final (textColor, bgColor, icon) = _getLogStyle(log.level);

    return Container(
      margin: EdgeInsets.symmetric(vertical: 1.h),
      padding: EdgeInsets.symmetric(horizontal: 8.w, vertical: 4.h),
      decoration: BoxDecoration(
        color: bgColor,
        borderRadius: BorderRadius.circular(4.r),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Level indicator
          if (log.level != LogLevel.info)
            Padding(
              padding: EdgeInsets.only(right: 6.w, top: 2.h),
              child: Icon(icon, size: 12.sp, color: textColor),
            ),
          // Timestamp (compact)
          Text(
            '${log.timestamp.hour.toString().padLeft(2, '0')}:${log.timestamp.minute.toString().padLeft(2, '0')}:${log.timestamp.second.toString().padLeft(2, '0')} ',
            style: TextStyle(
              color: Colors.grey[600],
              fontSize: 11.sp,
              fontFamily: 'monospace',
            ),
          ),
          // Log text
          Expanded(
            child: SelectableText(
              log.text,
              style: TextStyle(
                color: textColor,
                fontSize: 11.sp,
                fontFamily: 'monospace',
                height: 1.4,
              ),
            ),
          ),
        ],
      ),
    );
  }

  /// Build a system message with Codi branding
  Widget _buildSystemLogLine(LogLine log) {
    // Determine colors based on level
    Color accentColor;
    Color bgColor;
    
    switch (log.level) {
      case LogLevel.error:
        accentColor = Colors.red[400]!;
        bgColor = Colors.red.withOpacity(0.1);
        break;
      case LogLevel.warning:
        accentColor = Colors.orange[400]!;
        bgColor = Colors.orange.withOpacity(0.08);
        break;
      case LogLevel.success:
        accentColor = Colors.green[400]!;
        bgColor = Colors.green.withOpacity(0.1);
        break;
      default:
        accentColor = Colors.cyan[400]!;
        bgColor = Colors.cyan.withOpacity(0.08);
    }

    return Container(
      margin: EdgeInsets.symmetric(vertical: 4.h),
      padding: EdgeInsets.symmetric(horizontal: 12.w, vertical: 8.h),
      decoration: BoxDecoration(
        color: bgColor,
        borderRadius: BorderRadius.circular(8.r),
        border: Border.all(
          color: accentColor.withOpacity(0.3),
          width: 1,
        ),
      ),
      child: Row(
        children: [
          // Codi logo/icon
          Container(
            padding: EdgeInsets.all(4.w),
            decoration: BoxDecoration(
              color: accentColor.withOpacity(0.2),
              borderRadius: BorderRadius.circular(4.r),
            ),
            child: Text(
              'CODI',
              style: TextStyle(
                color: accentColor,
                fontSize: 8.sp,
                fontWeight: FontWeight.w800,
                letterSpacing: 0.5,
              ),
            ),
          ),
          SizedBox(width: 10.w),
          // Message
          Expanded(
            child: Text(
              log.text,
              style: TextStyle(
                color: accentColor,
                fontSize: 12.sp,
                fontWeight: FontWeight.w500,
                height: 1.3,
              ),
            ),
          ),
          // Timestamp
          Text(
            '${log.timestamp.hour.toString().padLeft(2, '0')}:${log.timestamp.minute.toString().padLeft(2, '0')}',
            style: TextStyle(
              color: accentColor.withOpacity(0.6),
              fontSize: 10.sp,
            ),
          ),
        ],
      ),
    );
  }

  (Color, Color, IconData) _getLogStyle(LogLevel level) {
    switch (level) {
      case LogLevel.error:
        return (
          Colors.red[400]!,
          Colors.red.withOpacity(0.08),
          Iconsax.close_circle,
        );
      case LogLevel.warning:
        return (
          Colors.orange[400]!,
          Colors.orange.withOpacity(0.06),
          Iconsax.warning_2,
        );
      case LogLevel.success:
        return (
          Colors.green[400]!,
          Colors.green.withOpacity(0.06),
          Iconsax.tick_circle,
        );
      case LogLevel.debug:
        return (
          Colors.grey[500]!,
          Colors.transparent,
          Iconsax.code,
        );
      case LogLevel.system:
        return (
          Colors.cyan[400]!,
          Colors.cyan.withOpacity(0.08),
          Iconsax.message_programming,
        );
      case LogLevel.info:
      default:
        return (
          Colors.grey[300]!,
          Colors.transparent,
          Iconsax.info_circle,
        );
    }
  }
}
