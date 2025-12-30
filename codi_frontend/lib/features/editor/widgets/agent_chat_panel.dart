/// Rich agent chat panel with 10+ message types
library;

import 'package:flutter/material.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:get/get.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:intl/intl.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../../core/constants/app_colors.dart';
import '../../../core/constants/app_strings.dart';
import '../../../core/constants/image_placeholders.dart';
import '../../../core/api/websocket_client.dart';
import '../controllers/agent_chat_controller.dart';
import '../models/agent_message_model.dart';


/// Agent chat panel with rich message rendering
class AgentChatPanel extends StatelessWidget {
  const AgentChatPanel({super.key});

  @override
  Widget build(BuildContext context) {
    final controller = Get.find<AgentChatController>();

    return Container(
      color: AppColors.surface,
      child: Column(
        children: [
          _buildChatHeader(controller),
          Expanded(child: _buildMessageList(controller)),
          _buildInputArea(controller),
        ],
      ),
    );
  }

  Widget _buildChatHeader(AgentChatController controller) {
    return Container(
      padding: EdgeInsets.symmetric(horizontal: 16.w, vertical: 12.h),
      decoration: BoxDecoration(
        color: AppColors.surface,
        border: Border(bottom: BorderSide(color: AppColors.border)),
      ),
      child: Row(
        children: [
          Icon(Icons.chat_bubble_outline, size: 18.r, color: AppColors.textSecondary),
          SizedBox(width: 8.w),
          Text(
            AppStrings.agentActivity,
            style: GoogleFonts.inter(
              fontSize: 14.sp,
              fontWeight: FontWeight.w600,
              color: AppColors.textPrimary,
            ),
          ),
          const Spacer(),
          Obx(() {
            if (controller.isAgentWorking.value) {
              return Row(
                children: [
                  SizedBox(
                    width: 12.r,
                    height: 12.r,
                    child: const CircularProgressIndicator(
                      strokeWidth: 2,
                      valueColor: AlwaysStoppedAnimation(AppColors.primary),
                    ),
                  ),
                  SizedBox(width: 6.w),
                  Text(
                    AppStrings.working,
                    style: GoogleFonts.inter(
                      fontSize: 11.sp,
                      color: AppColors.primary,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ],
              );
            }
            return const SizedBox.shrink();
          }),
        ],
      ),
    );
  }

  Widget _buildMessageList(AgentChatController controller) {
    return Obx(() {
      if (controller.messages.isEmpty) {
        return _buildEmptyState();
      }

      return ListView.builder(
        controller: controller.scrollController,
        padding: EdgeInsets.all(12.r),
        itemCount: controller.messages.length,
        itemBuilder: (context, index) {
          final message = controller.messages[index];
          return _buildMessage(message);
        },
      );
    });
  }

  Widget _buildMessage(AgentMessage message) {
    switch (message.type) {
      case MessageType.user:
        return _buildUserMessage(message);
      case MessageType.agentStatus:
        return _buildAgentStatusMessage(message);
      case MessageType.fileOperation:
        return _buildFileOperationMessage(message);
      case MessageType.toolExecution:
        return _buildToolExecutionMessage(message);
      case MessageType.gitOperation:
        return _buildGitOperationMessage(message);
      case MessageType.buildProgress:
        return _buildBuildProgressMessage(message);
      case MessageType.buildStatus:
        return _buildBuildStatusMessage(message);
      case MessageType.deploymentComplete:
        return _buildDeploymentCompleteMessage(message);
      case MessageType.reviewProgress:
        return _buildReviewProgressMessage(message);
      case MessageType.reviewIssue:
        return _buildReviewIssueMessage(message);
      case MessageType.error:
        return _buildErrorMessage(message);
      case MessageType.userInputRequired:
        return _buildUserInputMessage(message);
      case MessageType.llmStream:
        return _buildStreamingMessage(message);
    }
  }

  // ========== MESSAGE TYPE BUILDERS ==========

  Widget _buildStreamingMessage(AgentMessage message) {
    return Padding(
      padding: EdgeInsets.only(bottom: 10.h),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildAgentAvatar(message.agent ?? 'planner'),
          SizedBox(width: 8.w),
          Expanded(
            child: Container(
              padding: EdgeInsets.all(10.r),
              decoration: BoxDecoration(
                color: AppColors.messageAgent,
                borderRadius: BorderRadius.circular(8.r),
                border: Border.all(color: AppColors.primary.withOpacity(0.2)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Text(
                        '${_getAgentDisplayName(message.agent ?? '')} (Streaming)',
                        style: GoogleFonts.inter(
                          fontSize: 11.sp,
                          fontWeight: FontWeight.w600,
                          color: AppColors.primary,
                        ),
                      ),
                      SizedBox(width: 6.w),
                      SizedBox(
                        width: 10.r,
                        height: 10.r,
                        child: const CircularProgressIndicator(
                          strokeWidth: 2,
                          valueColor: AlwaysStoppedAnimation(AppColors.primary),
                        ),
                      ),
                    ],
                  ),
                  SizedBox(height: 6.h),
                  Text(
                    message.text,
                    style: GoogleFonts.jetBrainsMono(
                      fontSize: 12.sp,
                      color: AppColors.textPrimary,
                    ),
                  ),
                  SizedBox(height: 4.h),
                  Text(
                    _formatTime(message.timestamp),
                    style: GoogleFonts.inter(
                      fontSize: 9.sp,
                      color: AppColors.textTertiary,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildUserMessage(AgentMessage message) {
    return Padding(
      padding: EdgeInsets.only(bottom: 12.h),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.end,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Flexible(
            child: Container(
              padding: EdgeInsets.symmetric(horizontal: 14.w, vertical: 10.h),
              decoration: BoxDecoration(
                color: AppColors.messageUser,
                borderRadius: BorderRadius.circular(12.r),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Text(
                    message.text,
                    style: GoogleFonts.inter(
                      fontSize: 13.sp,
                      color: Colors.white,
                    ),
                  ),
                  SizedBox(height: 4.h),
                  Text(
                    _formatTime(message.timestamp),
                    style: GoogleFonts.inter(
                      fontSize: 9.sp,
                      color: Colors.white70,
                    ),
                  ),
                ],
              ),
            ),
          ),
          SizedBox(width: 8.w),
          CircleAvatar(
            radius: 14.r,
            backgroundImage: NetworkImage(
              ImagePlaceholders.userAvatar('user'),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildAgentStatusMessage(AgentMessage message) {
    return Padding(
      padding: EdgeInsets.only(bottom: 10.h),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildAgentAvatar(message.agent ?? 'planner'),
          SizedBox(width: 8.w),
          Expanded(
            child: Container(
              padding: EdgeInsets.all(10.r),
              decoration: BoxDecoration(
                color: _getStatusColor(message.status),
                borderRadius: BorderRadius.circular(8.r),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Text(
                        _getAgentDisplayName(message.agent ?? ''),
                        style: GoogleFonts.inter(
                          fontSize: 11.sp,
                          fontWeight: FontWeight.w600,
                          color: AppColors.textPrimary,
                        ),
                      ),
                      SizedBox(width: 6.w),
                      Text(
                        _getStatusEmoji(message.status),
                        style: TextStyle(fontSize: 14.sp),
                      ),
                    ],
                  ),
                  SizedBox(height: 4.h),
                  Text(
                    message.text,
                    style: GoogleFonts.inter(
                      fontSize: 12.sp,
                      color: AppColors.textPrimary,
                    ),
                  ),
                  // Show plan steps if available
                  if (message.planSteps.isNotEmpty) ...[
                    SizedBox(height: 6.h),
                    ...message.planSteps.map((step) => Padding(
                          padding: EdgeInsets.only(left: 8.w, top: 2.h),
                          child: Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text('•', style: TextStyle(fontSize: 12.sp)),
                              SizedBox(width: 4.w),
                              Expanded(
                                child: Text(
                                  step,
                                  style: GoogleFonts.inter(
                                    fontSize: 11.sp,
                                    color: AppColors.textSecondary,
                                  ),
                                ),
                              ),
                            ],
                          ),
                        )),
                  ],
                  SizedBox(height: 4.h),
                  Text(
                    _formatTime(message.timestamp),
                    style: GoogleFonts.inter(
                      fontSize: 9.sp,
                      color: AppColors.textTertiary,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildFileOperationMessage(AgentMessage message) {
    final icon = _getFileOperationIcon(message.operation ?? 'create');
    final color = _getFileOperationColor(message.operation ?? 'create');

    return Padding(
      padding: EdgeInsets.only(bottom: 8.h, left: 36.w),
      child: Container(
        padding: EdgeInsets.all(8.r),
        decoration: BoxDecoration(
          color: color.withOpacity(0.1),
          border: Border.all(color: color.withOpacity(0.3)),
          borderRadius: BorderRadius.circular(6.r),
        ),
        child: Row(
          children: [
            Text(icon, style: TextStyle(fontSize: 16.sp)),
            SizedBox(width: 6.w),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    _getOperationText(message.operation ?? 'create'),
                    style: GoogleFonts.inter(
                      fontSize: 10.sp,
                      fontWeight: FontWeight.w700,
                      color: color,
                    ),
                  ),
                  Text(
                    message.filePath ?? '',
                    style: GoogleFonts.jetBrainsMono(
                      fontSize: 10.sp,
                      color: AppColors.textPrimary,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                  if (message.stats != null)
                    Text(
                      message.stats!,
                      style: GoogleFonts.inter(
                        fontSize: 9.sp,
                        color: AppColors.textSecondary,
                      ),
                    ),
                ],
              ),
            ),
            Text(
              _formatTime(message.timestamp),
              style: GoogleFonts.inter(fontSize: 8.sp, color: AppColors.textTertiary),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildToolExecutionMessage(AgentMessage message) {
    return Padding(
      padding: EdgeInsets.only(bottom: 6.h, left: 36.w),
      child: Row(
        children: [
          Text('📄', style: TextStyle(fontSize: 12.sp)),
          SizedBox(width: 6.w),
          Expanded(
            child: Text(
              message.text,
              style: GoogleFonts.inter(
                fontSize: 11.sp,
                color: AppColors.textSecondary,
                fontStyle: FontStyle.italic,
              ),
            ),
          ),
          Text(
            _formatTime(message.timestamp),
            style: GoogleFonts.inter(fontSize: 8.sp, color: AppColors.textTertiary),
          ),
        ],
      ),
    );
  }

  Widget _buildGitOperationMessage(AgentMessage message) {
    final icon = _getGitOperationIcon(message.operation ?? 'commit');

    return Padding(
      padding: EdgeInsets.only(bottom: 10.h, left: 36.w),
      child: Container(
        padding: EdgeInsets.all(10.r),
        decoration: BoxDecoration(
          color: AppColors.gitSuccess,
          border: Border.all(color: AppColors.success.withOpacity(0.3)),
          borderRadius: BorderRadius.circular(8.r),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Text(icon, style: TextStyle(fontSize: 16.sp)),
                SizedBox(width: 6.w),
                Text(
                  _getGitOperationText(message.operation ?? 'commit'),
                  style: GoogleFonts.inter(
                    fontSize: 10.sp,
                    fontWeight: FontWeight.w700,
                    color: AppColors.success,
                  ),
                ),
                const Spacer(),
                Text(
                  _formatTime(message.timestamp),
                  style: GoogleFonts.inter(fontSize: 8.sp, color: AppColors.textTertiary),
                ),
              ],
            ),
            SizedBox(height: 4.h),
            Text(
              message.text,
              style: GoogleFonts.inter(fontSize: 11.sp, color: AppColors.textPrimary),
            ),
            if (message.gitStats.isNotEmpty) ...[
              SizedBox(height: 2.h),
              Text(
                message.gitStats,
                style: GoogleFonts.jetBrainsMono(
                  fontSize: 10.sp,
                  color: AppColors.textSecondary,
                ),
              ),
            ],
            if (message.commitSha != null) ...[
              SizedBox(height: 4.h),
              GestureDetector(
                onTap: () => _openCommit(message.commitSha!),
                child: Text(
                  'Commit: ${message.commitSha}',
                  style: GoogleFonts.jetBrainsMono(
                    fontSize: 9.sp,
                    color: AppColors.primary,
                    decoration: TextDecoration.underline,
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildBuildProgressMessage(AgentMessage message) {
    return Padding(
      padding: EdgeInsets.only(bottom: 10.h, left: 36.w),
      child: Container(
        padding: EdgeInsets.all(10.r),
        decoration: BoxDecoration(
          color: AppColors.buildProgress,
          border: Border.all(color: AppColors.info.withOpacity(0.3)),
          borderRadius: BorderRadius.circular(8.r),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Text('⏳', style: TextStyle(fontSize: 16.sp)),
                SizedBox(width: 6.w),
                Expanded(
                  child: Text(
                    message.text,
                    style: GoogleFonts.inter(fontSize: 11.sp, color: AppColors.textPrimary),
                  ),
                ),
                Text(
                  '${((message.progress ?? 0) * 100).toInt()}%',
                  style: GoogleFonts.inter(
                    fontSize: 11.sp,
                    fontWeight: FontWeight.w600,
                    color: AppColors.info,
                  ),
                ),
              ],
            ),
            SizedBox(height: 6.h),
            ClipRRect(
              borderRadius: BorderRadius.circular(4.r),
              child: LinearProgressIndicator(
                value: message.progress ?? 0,
                backgroundColor: Colors.grey[300],
                valueColor: const AlwaysStoppedAnimation(AppColors.info),
                minHeight: 6.h,
              ),
            ),
            SizedBox(height: 4.h),
            Text(
              _formatTime(message.timestamp),
              style: GoogleFonts.inter(fontSize: 8.sp, color: AppColors.textTertiary),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildBuildStatusMessage(AgentMessage message) {
    return Padding(
      padding: EdgeInsets.only(bottom: 10.h, left: 36.w),
      child: Container(
        padding: EdgeInsets.all(10.r),
        decoration: BoxDecoration(
          color: AppColors.buildProgress,
          border: Border.all(color: AppColors.info.withOpacity(0.3)),
          borderRadius: BorderRadius.circular(8.r),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Text('🔨', style: TextStyle(fontSize: 16.sp)),
                SizedBox(width: 6.w),
                Expanded(
                  child: Text(
                    message.text,
                    style: GoogleFonts.inter(fontSize: 11.sp, color: AppColors.textPrimary),
                  ),
                ),
              ],
            ),
            if (message.workflowUrl != null) ...[
              SizedBox(height: 6.h),
              GestureDetector(
                onTap: () => _openUrl(message.workflowUrl!),
                child: Text(
                  'View workflow',
                  style: GoogleFonts.inter(
                    fontSize: 10.sp,
                    color: AppColors.primary,
                    decoration: TextDecoration.underline,
                  ),
                ),
              ),
            ],
            SizedBox(height: 4.h),
            Text(
              _formatTime(message.timestamp),
              style: GoogleFonts.inter(fontSize: 8.sp, color: AppColors.textTertiary),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildDeploymentCompleteMessage(AgentMessage message) {
    return Padding(
      padding: EdgeInsets.only(bottom: 12.h, left: 36.w),
      child: Container(
        padding: EdgeInsets.all(12.r),
        decoration: BoxDecoration(
          color: AppColors.deploymentSuccess,
          border: Border.all(color: AppColors.success.withOpacity(0.5), width: 2),
          borderRadius: BorderRadius.circular(10.r),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Text('✅', style: TextStyle(fontSize: 22.sp)),
                SizedBox(width: 8.w),
                Expanded(
                  child: Text(
                    AppStrings.deployedSuccessfully,
                    style: GoogleFonts.inter(
                      fontSize: 14.sp,
                      fontWeight: FontWeight.w700,
                      color: AppColors.success,
                    ),
                  ),
                ),
              ],
            ),
            SizedBox(height: 8.h),
            GestureDetector(
              onTap: () => _openUrl(message.deploymentUrl!),
              child: Container(
                padding: EdgeInsets.symmetric(horizontal: 10.w, vertical: 8.h),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(6.r),
                  border: Border.all(color: AppColors.border),
                ),
                child: Row(
                  children: [
                    Icon(Icons.link, size: 14.r, color: AppColors.primary),
                    SizedBox(width: 6.w),
                    Expanded(
                      child: Text(
                        message.deploymentUrl ?? '',
                        style: GoogleFonts.jetBrainsMono(
                          fontSize: 10.sp,
                          color: AppColors.primary,
                          decoration: TextDecoration.underline,
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                    Icon(Icons.open_in_new, size: 12.r, color: AppColors.primary),
                  ],
                ),
              ),
            ),
            if (message.buildTime != null || message.size != null) ...[
              SizedBox(height: 8.h),
              Row(
                children: [
                  if (message.buildTime != null) ...[
                    Icon(Icons.timer, size: 12.r, color: AppColors.textSecondary),
                    SizedBox(width: 4.w),
                    Text(
                      message.buildTime!,
                      style: GoogleFonts.inter(fontSize: 10.sp, color: AppColors.textSecondary),
                    ),
                  ],
                  if (message.buildTime != null && message.size != null)
                    SizedBox(width: 12.w),
                  if (message.size != null) ...[
                    Icon(Icons.data_usage, size: 12.r, color: AppColors.textSecondary),
                    SizedBox(width: 4.w),
                    Text(
                      message.size!,
                      style: GoogleFonts.inter(fontSize: 10.sp, color: AppColors.textSecondary),
                    ),
                  ],
                ],
              ),
            ],
            SizedBox(height: 4.h),
            Text(
              _formatTime(message.timestamp),
              style: GoogleFonts.inter(fontSize: 8.sp, color: AppColors.textTertiary),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildReviewProgressMessage(AgentMessage message) {
    return Padding(
      padding: EdgeInsets.only(bottom: 8.h, left: 36.w),
      child: Container(
        padding: EdgeInsets.all(8.r),
        decoration: BoxDecoration(
          color: AppColors.accent.withOpacity(0.1),
          borderRadius: BorderRadius.circular(6.r),
        ),
        child: Row(
          children: [
            Text('🔍', style: TextStyle(fontSize: 14.sp)),
            SizedBox(width: 6.w),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    message.text,
                    style: GoogleFonts.inter(fontSize: 11.sp, color: AppColors.textPrimary),
                  ),
                  if (message.filePath != null)
                    Text(
                      message.filePath!,
                      style: GoogleFonts.jetBrainsMono(
                        fontSize: 9.sp,
                        color: AppColors.textSecondary,
                      ),
                    ),
                ],
              ),
            ),
            if (message.progress != null)
              Text(
                '${((message.progress ?? 0) * 100).toInt()}%',
                style: GoogleFonts.inter(
                  fontSize: 10.sp,
                  fontWeight: FontWeight.w600,
                  color: AppColors.accent,
                ),
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildReviewIssueMessage(AgentMessage message) {
    final color = message.severity == 'error'
        ? AppColors.error
        : message.severity == 'warning'
            ? AppColors.warning
            : AppColors.info;

    return Padding(
      padding: EdgeInsets.only(bottom: 8.h, left: 36.w),
      child: Container(
        padding: EdgeInsets.all(8.r),
        decoration: BoxDecoration(
          color: color.withOpacity(0.1),
          border: Border.all(color: color.withOpacity(0.3)),
          borderRadius: BorderRadius.circular(6.r),
        ),
        child: Row(
          children: [
            Icon(
              message.severity == 'error' ? Icons.error : Icons.warning,
              size: 16.r,
              color: color,
            ),
            SizedBox(width: 6.w),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    message.text,
                    style: GoogleFonts.inter(fontSize: 11.sp, color: AppColors.textPrimary),
                  ),
                  if (message.filePath != null || message.line != null)
                    Text(
                      '${message.filePath ?? ''}${message.line != null ? ':${message.line}' : ''}',
                      style: GoogleFonts.jetBrainsMono(
                        fontSize: 9.sp,
                        color: AppColors.textSecondary,
                      ),
                    ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildErrorMessage(AgentMessage message) {
    return Padding(
      padding: EdgeInsets.only(bottom: 12.h, left: 36.w),
      child: Container(
        padding: EdgeInsets.all(12.r),
        decoration: BoxDecoration(
          color: AppColors.errorBackground,
          border: Border.all(color: AppColors.error.withOpacity(0.5), width: 2),
          borderRadius: BorderRadius.circular(10.r),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Text('❌', style: TextStyle(fontSize: 18.sp)),
                SizedBox(width: 6.w),
                Expanded(
                  child: Text(
                    'Error',
                    style: GoogleFonts.inter(
                      fontSize: 13.sp,
                      fontWeight: FontWeight.w700,
                      color: AppColors.error,
                    ),
                  ),
                ),
              ],
            ),
            SizedBox(height: 6.h),
            Text(
              message.text,
              style: GoogleFonts.inter(fontSize: 12.sp, color: AppColors.textPrimary),
            ),
            if (message.errorDetails != null) ...[
              SizedBox(height: 6.h),
              Container(
                padding: EdgeInsets.all(6.r),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(4.r),
                ),
                child: Text(
                  message.errorDetails!,
                  style: GoogleFonts.jetBrainsMono(
                    fontSize: 9.sp,
                    color: AppColors.textSecondary,
                  ),
                ),
              ),
            ],
            SizedBox(height: 4.h),
            Text(
              _formatTime(message.timestamp),
              style: GoogleFonts.inter(fontSize: 8.sp, color: AppColors.textTertiary),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildUserInputMessage(AgentMessage message) {
    return Padding(
      padding: EdgeInsets.only(bottom: 12.h, left: 36.w),
      child: Container(
        padding: EdgeInsets.all(12.r),
        decoration: BoxDecoration(
          color: AppColors.warningBackground,
          border: Border.all(color: AppColors.warning.withOpacity(0.5)),
          borderRadius: BorderRadius.circular(10.r),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Text('❓', style: TextStyle(fontSize: 18.sp)),
                SizedBox(width: 6.w),
                Expanded(
                  child: Text(
                    'Input Required',
                    style: GoogleFonts.inter(
                      fontSize: 13.sp,
                      fontWeight: FontWeight.w700,
                      color: AppColors.warning,
                    ),
                  ),
                ),
              ],
            ),
            SizedBox(height: 6.h),
            Text(
              message.question ?? message.text,
              style: GoogleFonts.inter(fontSize: 12.sp, color: AppColors.textPrimary),
            ),
            if (message.options != null && message.options!.isNotEmpty) ...[
              SizedBox(height: 8.h),
              Wrap(
                spacing: 8.w,
                runSpacing: 6.h,
                children: message.options!.map((option) {
                  return ElevatedButton(
                    onPressed: () {
                      Get.find<WebSocketClient>()
                          .sendUserInputResponse(option);
                    },
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppColors.primary,
                      padding: EdgeInsets.symmetric(horizontal: 12.w, vertical: 6.h),
                      minimumSize: Size.zero,
                    ),
                    child: Text(
                      option,
                      style: GoogleFonts.inter(fontSize: 11.sp),
                    ),
                  );
                }).toList(),
              ),
            ],

          ],
        ),
      ),
    );
  }

  // ========== INPUT AREA ==========

  Widget _buildInputArea(AgentChatController controller) {
    return Container(
      padding: EdgeInsets.all(12.r),
      decoration: BoxDecoration(
        color: Colors.white,
        border: Border(top: BorderSide(color: AppColors.border)),
      ),
      child: SafeArea(
        child: Row(
          children: [
            Expanded(
              child: TextField(
                controller: controller.textController,
                decoration: InputDecoration(
                  hintText: AppStrings.typeMessage,
                  hintStyle: GoogleFonts.inter(fontSize: 13.sp, color: AppColors.textTertiary),
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(20.r),
                    borderSide: BorderSide(color: AppColors.border),
                  ),
                  enabledBorder: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(20.r),
                    borderSide: BorderSide(color: AppColors.border),
                  ),
                  focusedBorder: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(20.r),
                    borderSide: const BorderSide(color: AppColors.primary),
                  ),
                  contentPadding: EdgeInsets.symmetric(horizontal: 14.w, vertical: 10.h),
                  filled: true,
                  fillColor: AppColors.inputBackground,
                ),
                style: GoogleFonts.inter(fontSize: 13.sp),
                maxLines: 3,
                minLines: 1,
                textInputAction: TextInputAction.send,
                onSubmitted: controller.sendMessage,
              ),
            ),
            SizedBox(width: 8.w),
            Obx(() => Container(
                  decoration: BoxDecoration(
                    color: controller.isAgentWorking.value
                        ? AppColors.textTertiary
                        : AppColors.primary,
                    shape: BoxShape.circle,
                  ),
                  child: IconButton(
                    icon: Icon(Icons.send, color: Colors.white, size: 18.r),
                    onPressed: controller.isAgentWorking.value
                        ? null
                        : () => controller.sendMessage(controller.textController.text),
                    padding: EdgeInsets.all(10.r),
                    constraints: BoxConstraints(minWidth: 40.r, minHeight: 40.r),
                  ),
                )),
          ],
        ),
      ),
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Padding(
        padding: EdgeInsets.all(24.r),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Image.network(
              ImagePlaceholders.agentAvatar,
              width: 100.w,
              height: 100.h,
              errorBuilder: (_, __, ___) => Icon(
                Icons.smart_toy,
                size: 64.r,
                color: AppColors.textTertiary,
              ),
            ),
            SizedBox(height: 16.h),
            Text(
              AppStrings.startConversation,
              style: GoogleFonts.inter(
                fontSize: 16.sp,
                fontWeight: FontWeight.w600,
                color: AppColors.textPrimary,
              ),
            ),
            SizedBox(height: 6.h),
            Text(
              AppStrings.startConversationSubtitle,
              style: GoogleFonts.inter(
                fontSize: 13.sp,
                color: AppColors.textSecondary,
              ),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }

  // ========== HELPER METHODS ==========

  Widget _buildAgentAvatar(String agent) {
    return Container(
      width: 28.r,
      height: 28.r,
      decoration: BoxDecoration(
        color: _getAgentColor(agent).withOpacity(0.2),
        borderRadius: BorderRadius.circular(6.r),
      ),
      child: Center(
        child: Text(
          _getAgentEmoji(agent),
          style: TextStyle(fontSize: 14.sp),
        ),
      ),
    );
  }

  String _formatTime(DateTime timestamp) => DateFormat('HH:mm:ss').format(timestamp);

  Color _getStatusColor(String? status) {
    switch (status) {
      case 'started':
      case 'in_progress':
      case 'planning':
        return AppColors.warningBackground;
      case 'completed':
        return AppColors.deploymentSuccess;
      case 'failed':
        return AppColors.errorBackground;
      default:
        return AppColors.messageAgent;
    }
  }

  String _getStatusEmoji(String? status) {
    switch (status) {
      case 'started':
        return '🚀';
      case 'in_progress':
      case 'planning':
        return '⚙️';
      case 'completed':
        return '✅';
      case 'failed':
        return '❌';
      default:
        return '📋';
    }
  }

  String _getAgentDisplayName(String agent) {
    const names = {
      'planner': 'Planner',
      'flutter_engineer': 'Flutter Engineer',
      'code_reviewer': 'Code Reviewer',
      'git_operator': 'Git Operator',
      'build_deploy': 'Build & Deploy',
      'memory': 'Memory',
    };
    return names[agent] ?? agent;
  }

  String _getAgentEmoji(String agent) {
    const emojis = {
      'planner': '🤖',
      'flutter_engineer': '👨‍💻',
      'code_reviewer': '🔍',
      'git_operator': '🌿',
      'build_deploy': '🚀',
      'memory': '📊',
    };
    return emojis[agent] ?? '🤖';
  }

  Color _getAgentColor(String agent) {
    const colors = {
      'planner': AppColors.planner,
      'flutter_engineer': AppColors.flutterEngineer,
      'code_reviewer': AppColors.codeReviewer,
      'git_operator': AppColors.gitOperator,
      'build_deploy': AppColors.buildDeploy,
      'memory': AppColors.memory,
    };
    return colors[agent] ?? AppColors.primary;
  }

  String _getFileOperationIcon(String operation) {
    switch (operation) {
      case 'create':
        return '✨';
      case 'update':
        return '📝';
      case 'delete':
        return '🗑️';
      default:
        return '📄';
    }
  }

  Color _getFileOperationColor(String operation) {
    switch (operation) {
      case 'create':
        return AppColors.fileCreate;
      case 'update':
        return AppColors.fileUpdate;
      case 'delete':
        return AppColors.fileDelete;
      default:
        return AppColors.textSecondary;
    }
  }

  String _getOperationText(String operation) {
    switch (operation) {
      case 'create':
        return 'CREATED';
      case 'update':
        return 'UPDATED';
      case 'delete':
        return 'DELETED';
      default:
        return operation.toUpperCase();
    }
  }

  String _getGitOperationIcon(String operation) {
    switch (operation) {
      case 'create_branch':
        return '🌿';
      case 'commit':
        return '💾';
      case 'push':
        return '📤';
      case 'merge':
        return '🔀';
      default:
        return '📋';
    }
  }

  String _getGitOperationText(String operation) {
    switch (operation) {
      case 'create_branch':
        return 'CREATED BRANCH';
      case 'commit':
        return 'COMMITTED';
      case 'push':
        return 'PUSHED';
      case 'merge':
        return 'MERGED';
      default:
        return operation.toUpperCase();
    }
  }

  void _openCommit(String sha) {
    // Would typically open commit URL
  }

  void _openUrl(String url) async {
    final uri = Uri.parse(url);
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    }
  }
}
