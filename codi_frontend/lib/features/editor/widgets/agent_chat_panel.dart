/// Simplified agent chat panel
library;

import 'package:codi_frontend/features/editor/widgets/chat/operation_messages.dart';
import 'package:codi_frontend/features/editor/widgets/chat/success_message.dart';
import 'package:codi_frontend/features/editor/widgets/chat/thinking_message.dart';
import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:get/get.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../../../core/constants/app_colors.dart';
import '../../../core/constants/app_strings.dart';
import '../constants/chat_icons.dart';
import '../controllers/agent_chat_controller.dart';
import '../models/agent_message_model.dart';

class AgentChatPanel extends StatelessWidget {
  const AgentChatPanel({super.key});

  @override
  Widget build(BuildContext context) {
    final controller = Get.find<AgentChatController>();

    return Container(
      color: Get.theme.cardTheme.color,
      child: Column(
        children: [
          Expanded(child: _buildMessageList(controller)),
          _buildInputArea(controller),
        ],
      ),
    );
  }

  Widget _buildMessageList(AgentChatController controller) {
    return Obx(() {
      if (controller.messages.isEmpty) {
        return _buildEmptyState(controller);
      }

      return ListView.builder(
        controller: controller.scrollController,
        padding: EdgeInsets.symmetric(horizontal: 16.w, vertical: 20.h),
        itemCount: controller.messages.length,
        itemBuilder: (context, index) {
          final message = controller.messages[index];
          return _buildMessage(message);
        },
      );
    });
  }

  Widget _buildMessage(AgentMessage message) {
    Widget messageWidget;

    switch (message.type) {
      case MessageType.user:
        messageWidget = _buildUserMessage(message);
        break;

      case MessageType.agentStatus:
        if (message.status == 'thinking' || message.status == 'started') {
          messageWidget = ThinkingMessage(message: message);
        } else {
          messageWidget = _buildAgentStatusMessage(message);
        }
        break;

      case MessageType.agentResponse:
      case MessageType.conversationalResponse:
        messageWidget = _buildAgentResponseMessage(message);
        break;

      case MessageType.toolExecution:
        messageWidget = _buildToolExecutionMessage(message);
        break;

      case MessageType.toolResult:
        messageWidget = _buildToolResultMessage(message);
        break;

      case MessageType.fileOperation:
        messageWidget = FileOperationMessage(message: message);
        break;

      case MessageType.gitOperation:
        messageWidget = GitOperationMessage(message: message);
        break;

      case MessageType.buildProgress:
        messageWidget = BuildProgressMessage(message: message);
        break;

      case MessageType.deploymentComplete:
        messageWidget = SuccessMessage(message: message);
        break;

      case MessageType.error:
        messageWidget = ErrorMessage(message: message);
        break;

      case MessageType.planCreated:
        messageWidget = _buildPlanApprovalMessage(message);
        break;

      case MessageType.planApproved:
      case MessageType.planRejected:
        messageWidget = _buildPlanStatusMessage(message);
        break;

      default:
        messageWidget = _buildGenericMessage(message);
    }

    return messageWidget;
  }

  Widget _buildUserMessage(AgentMessage message) {
    return Padding(
      padding: EdgeInsets.only(bottom: 16.h),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.end,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Flexible(
            child: Container(
              padding: EdgeInsets.symmetric(horizontal: 16.w, vertical: 12.h),
              decoration: BoxDecoration(
                color: AppColors.messageUser,
                borderRadius: BorderRadius.only(
                  topLeft: Radius.circular(16.r),
                  topRight: Radius.circular(4.r),
                  bottomLeft: Radius.circular(16.r),
                  bottomRight: Radius.circular(16.r),
                ),
                boxShadow: [
                  BoxShadow(
                    color: AppColors.primary.withOpacity(0.1),
                    blurRadius: 8,
                    offset: Offset(0, 2),
                  ),
                ],
              ),
              child: Text(
                message.text,
                style: GoogleFonts.inter(
                  fontSize: 14.sp,
                  color: Colors.white,
                  height: 1.4,
                ),
              ),
            ),
          ),
          SizedBox(width: 8.w),
          CircleAvatar(
            radius: 16.r,
            backgroundColor: Colors.grey[200],
            child: Icon(StatusIcons.user, size: 16.r, color: Colors.grey[600]),
          ),
        ],
      ),
    ).animate().fadeIn(duration: 300.ms).slideY(begin: 0.1, end: 0);
  }

  Widget _buildAgentStatusMessage(AgentMessage message) {
    return Padding(
      padding: EdgeInsets.only(bottom: 12.h),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(AgentAvatarIcons.ai, size: 24.r, color: AppColors.primary),
          SizedBox(width: 12.w),
          Expanded(
            child: Container(
              padding: EdgeInsets.all(12.r),
              decoration: BoxDecoration(
                color: Get.theme.canvasColor,
                borderRadius: BorderRadius.circular(12.r),
              ),
              child: Text(
                message.text,
                style: GoogleFonts.inter(
                    fontSize: 13.sp, color: Get.textTheme.bodyMedium?.color),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildAgentResponseMessage(AgentMessage message) {
    return Padding(
      padding: EdgeInsets.only(bottom: 16.h),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          CircleAvatar(
            radius: 16.r,
            backgroundColor: AppColors.primary.withOpacity(0.1),
            child:
                Icon(AgentAvatarIcons.ai, size: 20.r, color: AppColors.primary),
          ),
          SizedBox(width: 12.w),
          Expanded(
            child: Container(
              padding: EdgeInsets.all(16.r),
              decoration: BoxDecoration(
                color: Get.theme.cardTheme.color,
                border: Border.all(color: Get.theme.dividerColor),
                borderRadius: BorderRadius.only(
                  topLeft: Radius.circular(4.r),
                  topRight: Radius.circular(16.r),
                  bottomLeft: Radius.circular(16.r),
                  bottomRight: Radius.circular(16.r),
                ),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withOpacity(0.03),
                    blurRadius: 8,
                    offset: Offset(0, 2),
                  ),
                ],
              ),
              child: Text(
                message.text,
                style: GoogleFonts.inter(
                  fontSize: 14.sp,
                  color: Get.textTheme.bodyLarge?.color,
                  height: 1.5,
                ),
              ),
            ),
          ),
        ],
      ),
    ).animate().fadeIn(duration: 300.ms).slideY(begin: 0.1, end: 0);
  }

  Widget _buildToolExecutionMessage(AgentMessage message) {
    return Padding(
      padding: EdgeInsets.only(bottom: 8.h, left: 40.w),
      child: Row(
        children: [
          Icon(StatusIcons.tool, size: 16.r, color: AppColors.info),
          SizedBox(width: 8.w),
          Text(
            message.text.isNotEmpty
                ? message.text
                : 'Using ${message.tool ?? "tool"}...',
            overflow: TextOverflow.ellipsis,
            style: GoogleFonts.inter(
              fontSize: 12.sp,
              color: AppColors.textSecondary,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildToolResultMessage(AgentMessage message) {
    if (message.toolResult == null || message.toolResult!.isEmpty) {
      return const SizedBox.shrink();
    }

    final toolResult = message.toolResult!;

    // For list_files, we might want to show a more compact view
    if (message.tool == 'list_files') {
      final files =
          toolResult.split('\n').where((f) => f.trim().isNotEmpty).toList();
      if (files.isNotEmpty) {
        return Padding(
          padding: EdgeInsets.only(bottom: 8.h, left: 60.w),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Found ${files.length} items:',
                style: GoogleFonts.inter(
                    fontSize: 11.sp,
                    fontWeight: FontWeight.w600,
                    color: AppColors.textSecondary),
              ),
              SizedBox(height: 4.h),
              ...files.take(5).map((f) => Padding(
                    padding: EdgeInsets.only(bottom: 2.h),
                    child: Row(
                      children: [
                        Icon(LucideIcons.file, size: 10.r, color: Colors.grey),
                        SizedBox(width: 4.w),
                        Expanded(
                          child: Text(
                            f.trim(),
                            style: GoogleFonts.jetBrainsMono(
                                fontSize: 10.sp, color: AppColors.textPrimary),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                      ],
                    ),
                  )),
              if (files.length > 5)
                Text(
                  '...and ${files.length - 5} more',
                  style: GoogleFonts.inter(
                      fontSize: 10.sp,
                      fontStyle: FontStyle.italic,
                      color: Colors.grey),
                ),
            ],
          ),
        );
      }
    }

    // Generic tool result (truncated)
    final displayResult = toolResult.length > 200
        ? '${toolResult.substring(0, 200)}...'
        : toolResult;

    return Padding(
      padding: EdgeInsets.only(bottom: 8.h, left: 60.w),
      child: Container(
        padding: EdgeInsets.all(8.r),
        decoration: BoxDecoration(
          color: Get.theme.canvasColor,
          border: Border.all(color: Get.theme.dividerColor),
        ),
        child: Text(
          displayResult,
          style: GoogleFonts.jetBrainsMono(
            fontSize: 10.sp,
            color: AppColors.textSecondary,
          ),
        ),
      ),
    );
  }

  Widget _buildGenericMessage(AgentMessage message) {
    return Padding(
      padding: EdgeInsets.only(bottom: 12.h, left: 36.w),
      child: Text(
        message.text,
        style: GoogleFonts.inter(
          fontSize: 13.sp,
          color: AppColors.textSecondary,
        ),
      ),
    );
  }

  Widget _buildPlanApprovalMessage(AgentMessage message) {
    final controller = Get.find<AgentChatController>();
    final planMarkdown = message.planMarkdown ?? message.text;

    // Extract title from markdown (first # line)
    String title = 'Implementation Plan';
    final titleMatch =
        RegExp(r'^#\s*(.+)$', multiLine: true).firstMatch(planMarkdown);
    if (titleMatch != null) {
      title = titleMatch
              .group(1)
              ?.replaceAll(RegExp(r'^Implementation Plan:?\s*'), '')
              .trim() ??
          title;
    }

    // Count tasks from markdown - match various formats:
    // "1. [ ] Task" or "- [ ] Task"
    int taskCount = 0;
    
    // First try: numbered tasks with checkboxes like "1. [ ] Task"
    final numberedCheckboxTasks = RegExp(
      r'^\s*\d+\.\s*\[\s*[x ]?\s*\]',
      multiLine: true,
      caseSensitive: false,
    ).allMatches(planMarkdown);
    taskCount = numberedCheckboxTasks.length;
    
    // Fallback: bullet points with checkboxes like "- [ ] Task"
    if (taskCount == 0) {
      final bulletCheckboxTasks = RegExp(
        r'^\s*[-*]\s*\[\s*[x ]?\s*\]',
        multiLine: true,
      ).allMatches(planMarkdown);
      taskCount = bulletCheckboxTasks.length;
    }

    // Last fallback: count numbered lines in ## Tasks section
    if (taskCount == 0) {
      final tasksSection = RegExp(
        r'##\s*Tasks\s*\n([\s\S]*?)(?=\n##|\n#|$)',
        caseSensitive: false,
      ).firstMatch(planMarkdown);
      if (tasksSection != null) {
        taskCount = RegExp(r'^\s*\d+\.', multiLine: true)
            .allMatches(tasksSection.group(1) ?? '')
            .length;
      }
    }

    return Padding(
      padding: EdgeInsets.only(bottom: 16.h),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          CircleAvatar(
            radius: 16.r,
            backgroundColor: AppColors.warning.withOpacity(0.1),
            child: Icon(LucideIcons.fileCheck,
                size: 20.r, color: AppColors.warning),
          ),
          SizedBox(width: 12.w),
          Expanded(
            child: GestureDetector(
              onTap: () {
                // Navigate to full plan review screen
                if (message.planId != null) {
                  Get.toNamed('/plan-review',
                      arguments: {'planId': message.planId});
                }
              },
              child: Container(
                decoration: BoxDecoration(
                  color: Get.theme.cardTheme.color,
                  border: Border.all(color: AppColors.warning.withOpacity(0.3)),
                  borderRadius: BorderRadius.circular(12.r),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Compact header
                    Container(
                      padding: EdgeInsets.all(12.r),
                      decoration: BoxDecoration(
                        color: AppColors.warning.withOpacity(0.1),
                        borderRadius: BorderRadius.only(
                          topLeft: Radius.circular(11.r),
                          topRight: Radius.circular(11.r),
                        ),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Expanded(
                                child: Text(
                                  title,
                                  style: GoogleFonts.inter(
                                    fontSize: 14.sp,
                                    fontWeight: FontWeight.w600,
                                    color: Get.textTheme.titleMedium?.color,
                                  ),
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                ),
                              ),
                              Obx(() {
                                final isPending = message.planId == controller.currentPendingPlanId.value;
                                if (!isPending) return const SizedBox.shrink();
                                
                                return Container(
                                  padding: EdgeInsets.symmetric(
                                      horizontal: 8.w, vertical: 4.h),
                                  decoration: BoxDecoration(
                                    color: AppColors.warning,
                                    borderRadius: BorderRadius.circular(12.r),
                                  ),
                                  child: Text(
                                    'Pending',
                                    style: GoogleFonts.inter(
                                      fontSize: 10.sp,
                                      fontWeight: FontWeight.w600,
                                      color: Colors.white,
                                    ),
                                  ),
                                );
                              }),
                            ],
                          ),
                          SizedBox(height: 8.h),
                          Row(
                            children: [
                              Icon(LucideIcons.listChecks,
                                  size: 12.r, color: AppColors.textSecondary),
                              SizedBox(width: 4.w),
                              Text(
                                '$taskCount tasks',
                                style: GoogleFonts.inter(
                                  fontSize: 11.sp,
                                  color: AppColors.textSecondary,
                                ),
                              ),
                              SizedBox(width: 12.w),
                              Icon(LucideIcons.arrowRight,
                                  size: 12.r, color: AppColors.primary),
                              SizedBox(width: 4.w),
                              Text(
                                'Tap to review',
                                style: GoogleFonts.inter(
                                  fontSize: 11.sp,
                                  color: AppColors.primary,
                                  fontWeight: FontWeight.w500,
                                ),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),

                    // Quick action buttons
                    Obx(
                      () => controller.isAwaitingApproval.value
                          ? Container(
                              padding: EdgeInsets.symmetric(
                                  horizontal: 12.w, vertical: 10.h),
                              child: Row(
                                children: [
                                  Expanded(
                                    child: OutlinedButton(
                                      onPressed: () => controller.rejectPlan(),
                                      style: OutlinedButton.styleFrom(
                                        foregroundColor: AppColors.error,
                                        side: BorderSide(
                                            color: AppColors.error
                                                .withOpacity(0.5)),
                                        padding:
                                            EdgeInsets.symmetric(vertical: 8.h),
                                        shape: RoundedRectangleBorder(
                                          borderRadius:
                                              BorderRadius.circular(8.r),
                                        ),
                                      ),
                                      child: Text('Decline',
                                          style: GoogleFonts.inter(
                                              fontSize: 12.sp,
                                              fontWeight: FontWeight.w600)),
                                    ),
                                  ),
                                  SizedBox(width: 10.w),
                                  Expanded(
                                    flex: 2,
                                    child: ElevatedButton.icon(
                                      onPressed: () => controller.approvePlan(),
                                      icon: Icon(LucideIcons.check, size: 14.r),
                                      label: Text('Approve',
                                          style: GoogleFonts.inter(
                                              fontSize: 12.sp,
                                              fontWeight: FontWeight.w600)),
                                      style: ElevatedButton.styleFrom(
                                        backgroundColor: AppColors.success,
                                        foregroundColor: Colors.white,
                                        padding:
                                            EdgeInsets.symmetric(vertical: 8.h),
                                        shape: RoundedRectangleBorder(
                                          borderRadius:
                                              BorderRadius.circular(8.r),
                                        ),
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                            )
                          : const SizedBox.shrink(),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    ).animate().fadeIn(duration: 300.ms).slideY(begin: 0.1, end: 0);
  }

  Widget _buildPlanStatusMessage(AgentMessage message) {
    final isApproved = message.type == MessageType.planApproved;

    return Padding(
      padding: EdgeInsets.only(bottom: 12.h, left: 40.w),
      child: Container(
        padding: EdgeInsets.symmetric(horizontal: 12.w, vertical: 8.h),
        decoration: BoxDecoration(
          color: (isApproved ? AppColors.success : AppColors.error)
              .withOpacity(0.1),
          borderRadius: BorderRadius.circular(8.r),
          border: Border.all(
            color: (isApproved ? AppColors.success : AppColors.error)
                .withOpacity(0.3),
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              isApproved ? LucideIcons.circleCheck : LucideIcons.circleX,
              size: 16.r,
              color: isApproved ? AppColors.success : AppColors.error,
            ),
            SizedBox(width: 8.w),
            Text(
              isApproved
                  ? 'Plan approved - starting implementation...'
                  : 'Plan rejected',
              style: GoogleFonts.inter(
                fontSize: 12.sp,
                fontWeight: FontWeight.w500,
                color: isApproved ? AppColors.success : AppColors.error,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildInputArea(AgentChatController controller) {
    return Container(
      padding: EdgeInsets.all(16.r),
      decoration: BoxDecoration(
        color: Get.theme.cardTheme.color,
        border: Border(top: BorderSide(color: Get.theme.dividerColor)),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.02),
            blurRadius: 10,
            offset: Offset(0, -2),
          ),
        ],
      ),
      child: SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            // Browser mode indicator banner
            Obx(() => controller.isBrowserAgentMode.value
                ? Container(
                    margin: EdgeInsets.only(bottom: 12.h),
                    padding:
                        EdgeInsets.symmetric(horizontal: 12.w, vertical: 8.h),
                    decoration: BoxDecoration(
                      color: AppColors.primary.withOpacity(0.1),
                      borderRadius: BorderRadius.circular(8.r),
                      border:
                          Border.all(color: AppColors.primary.withOpacity(0.3)),
                    ),
                    child: Row(
                      children: [
                        Icon(LucideIcons.globe,
                            size: 16.r, color: AppColors.primary),
                        SizedBox(width: 8.w),
                        Expanded(
                          child: Text(
                            'Browser Agent Mode - AI will control the browser',
                            style: GoogleFonts.inter(
                              fontSize: 12.sp,
                              color: AppColors.primary,
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                        ),
                        GestureDetector(
                          onTap: controller.toggleBrowserAgentMode,
                          child: Icon(LucideIcons.x,
                              size: 16.r, color: AppColors.primary),
                        ),
                      ],
                    ),
                  )
                : const SizedBox.shrink()),

            // Input row
            Row(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                // Browser mode toggle button
                Obx(() => GestureDetector(
                      onTap: controller.toggleBrowserAgentMode,
                      child: AnimatedContainer(
                        duration: const Duration(milliseconds: 200),
                        width: 44.r,
                        height: 44.r,
                        margin: EdgeInsets.only(right: 8.w),
                        decoration: BoxDecoration(
                          color: controller.isBrowserAgentMode.value
                              ? AppColors.primary.withOpacity(0.15)
                              : Get.theme.inputDecorationTheme.fillColor,
                          borderRadius: BorderRadius.circular(22.r),
                          border: Border.all(
                            color: controller.isBrowserAgentMode.value
                                ? AppColors.primary
                                : Get.theme.dividerColor,
                            width: controller.isBrowserAgentMode.value ? 2 : 1,
                          ),
                        ),
                        child: Icon(
                          LucideIcons.globe,
                          size: 20.r,
                          color: controller.isBrowserAgentMode.value
                              ? AppColors.primary
                              : AppColors.textTertiary,
                        ),
                      ),
                    )),

                // Text input
                Expanded(
                  child: Container(
                    decoration: BoxDecoration(
                      color: Get.theme.inputDecorationTheme.fillColor,
                      borderRadius: BorderRadius.circular(24.r),
                      border: Border.all(color: Get.theme.dividerColor),
                    ),
                    child: Row(
                      children: [
                        SizedBox(width: 16.w),
                        Icon(
                          StatusIcons.message,
                          size: 20.r,
                          color: AppColors.textTertiary,
                        ),
                        SizedBox(width: 10.w),
                        Expanded(
                          child: Obx(() => TextField(
                                controller: controller.textController,
                                decoration: InputDecoration(
                                  hintText: controller.isBrowserAgentMode.value
                                      ? 'Tell the browser what to do...'
                                      : AppStrings.typeMessage,
                                  hintStyle: GoogleFonts.inter(
                                    fontSize: 14.sp,
                                    color: AppColors.textTertiary,
                                  ),
                                  border: InputBorder.none,
                                  contentPadding:
                                      EdgeInsets.symmetric(vertical: 12.h),
                                ),
                                style: GoogleFonts.inter(fontSize: 14.sp),
                                maxLines: 4,
                                minLines: 1,
                                textInputAction: TextInputAction.send,
                                onSubmitted: controller.sendMessage,
                              )),
                        ),
                        SizedBox(width: 8.w),
                      ],
                    ),
                  ),
                ),
                SizedBox(width: 12.w),

                // Send/Stop button
                Obx(() => AnimatedContainer(
                      duration: Duration(milliseconds: 200),
                      width: 48.r,
                      height: 48.r,
                      decoration: BoxDecoration(
                        gradient: controller.isAgentWorking.value
                            ? LinearGradient(colors: [
                                AppColors.error,
                                AppColors.error.withOpacity(0.8)
                              ])
                            : LinearGradient(
                                colors: [
                                  AppColors.primary,
                                  const Color(0xFF6366F1)
                                ],
                              ),
                        shape: BoxShape.circle,
                        boxShadow: controller.isAgentWorking.value
                            ? []
                            : [
                                BoxShadow(
                                  color: AppColors.primary.withOpacity(0.3),
                                  blurRadius: 8,
                                  offset: Offset(0, 4),
                                ),
                              ],
                      ),
                      child: Material(
                        color: Colors.transparent,
                        child: InkWell(
                          borderRadius: BorderRadius.circular(24.r),
                          onTap: controller.isAgentWorking.value
                              ? () => controller.stopTask()
                              : () => controller
                                  .sendMessage(controller.textController.text),
                          child: Center(
                            child: Icon(
                              controller.isAgentWorking.value
                                  ? LucideIcons.square
                                  : LucideIcons.send,
                              color: Colors.white,
                              size: 20.r,
                            ),
                          ),
                        ),
                      ),
                    )
                        .animate(
                            target: controller.isAgentWorking.value ? 1 : 0)
                        .scale(
                            begin: Offset(1, 1),
                            end: Offset(0.9, 0.9),
                            duration: 200.ms)),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildEmptyState(AgentChatController controller) {
    return Center(
      child: Padding(
        padding: EdgeInsets.all(32.r),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              width: 100.r,
              height: 100.r,
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  colors: [
                    AppColors.primary.withOpacity(0.05),
                    AppColors.accent.withOpacity(0.05),
                  ],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                ),
                shape: BoxShape.circle,
              ),
              child: Icon(
                AgentAvatarIcons.ai,
                size: 48.r,
                color: AppColors.primary.withOpacity(0.8),
              ),
            ).animate().scale(duration: 600.ms, curve: Curves.easeOutBack),
            SizedBox(height: 24.h),
            Text(
              AppStrings.startConversation,
              style: GoogleFonts.inter(
                fontSize: 18.sp,
                fontWeight: FontWeight.w600,
                color: Get.textTheme.titleLarge?.color,
              ),
            ).animate().fadeIn(delay: 200.ms).slideY(begin: 0.2, end: 0),
            SizedBox(height: 8.h),
            Text(
              AppStrings.startConversationSubtitle,
              style: GoogleFonts.inter(
                fontSize: 14.sp,
                color: Get.textTheme.bodyMedium?.color,
                height: 1.5,
              ),
              textAlign: TextAlign.center,
            ).animate().fadeIn(delay: 300.ms).slideY(begin: 0.2, end: 0),
            SizedBox(height: 32.h),
            Wrap(
              spacing: 12.w,
              runSpacing: 12.h,
              alignment: WrapAlignment.center,
              children: [
                _buildSuggestionChip(
                    StatusIcons.plus, 'Add feature', controller),
                _buildSuggestionChip(
                    StatusIcons.palette, 'Change design', controller),
                _buildSuggestionChip(StatusIcons.bug, 'Fix bug', controller),
              ],
            ).animate().fadeIn(delay: 500.ms),
          ],
        ),
      ),
    );
  }

  Widget _buildSuggestionChip(
      IconData icon, String label, AgentChatController controller) {
    return ActionChip(
      avatar: Icon(icon, size: 16.r, color: AppColors.primary),
      label: Text(
        label,
        style: GoogleFonts.inter(
            fontSize: 13.sp,
            fontWeight: FontWeight.w500,
            color: Get.textTheme.bodyMedium?.color),
      ),
      onPressed: () {
        controller.textController.text = label;
      },
      backgroundColor: Get.theme.cardTheme.color,
      shadowColor: Colors.black.withOpacity(0.05),
      elevation: 2,
      padding: EdgeInsets.all(8.r),
      shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(24.r),
          side: BorderSide(color: Get.theme.dividerColor, width: 1.0)),
    );
  }
}
