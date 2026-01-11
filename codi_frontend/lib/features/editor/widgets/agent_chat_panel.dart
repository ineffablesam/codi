/// Rich agent chat panel with professional icons and animations
library;

import 'package:codi_frontend/features/editor/widgets/chat/operation_messages.dart';
import 'package:codi_frontend/features/editor/widgets/chat/progressive_action_message.dart';
import 'package:codi_frontend/features/editor/widgets/chat/streaming_code_message.dart';
import 'package:codi_frontend/features/editor/widgets/chat/success_message.dart';
import 'package:codi_frontend/features/editor/widgets/chat/thinking_message.dart';
import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:get/get.dart';
import 'package:google_fonts/google_fonts.dart';

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
      color: Colors.white, // Clean white background for professional look
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
        itemCount:
            controller.messages.length + (controller.isTyping.value ? 1 : 0),
        itemBuilder: (context, index) {
          if (index == controller.messages.length) {
            // Typing indicator at the end if needed (though usually handled by ThinkingMessage)
            return SizedBox.shrink();
          }
          final message = controller.messages[index];
          return _buildMessage(message);
        },
      );
    });
  }

  Widget _buildMessage(AgentMessage message) {
    // Determine which widget to show based on message type
    Widget messageWidget;

    switch (message.type) {
      case MessageType.user:
        messageWidget = _buildUserMessage(message);
        break;

      // Thinking & Planning
      case MessageType.agentStatus:
        if (message.status == 'thinking' || message.status == 'planning') {
          messageWidget = ThinkingMessage(message: message);
        } else {
          messageWidget = _buildAgentStatusMessage(message);
        }
        break;

      // Progressive Action (Main Agent Work)
      case MessageType.backgroundTaskStarted:
      case MessageType.backgroundTaskProgress:
      case MessageType.backgroundTaskCompleted:
        messageWidget = ProgressiveActionMessage(message: message);
        break;

      // Code Generation
      case MessageType.llmStream:
        messageWidget = StreamingCodeMessage(message: message);
        break;

      // Completion & Success
      case MessageType.deploymentComplete:
      case MessageType.batchComplete: // Assuming a batch completion type
        messageWidget = SuccessMessage(message: message);
        break;

      // Operations
      case MessageType.fileOperation:
        messageWidget = FileOperationMessage(message: message);
        break;
      case MessageType.gitOperation:
        messageWidget = GitOperationMessage(message: message);
        break;
      case MessageType.buildProgress:
        messageWidget = BuildProgressMessage(message: message);
        break;
      case MessageType.error:
        messageWidget = ErrorMessage(message: message);
        break;

      // Fallback/Legacy
      default:
        messageWidget = _buildGenericMessage(message);
    }

    // Wrap in common layout if needed (e.g. avatar for some)
    // But most custom widgets handle their own layout
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

  // Legacy status message backup
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
                color: Colors.grey[100],
                borderRadius: BorderRadius.circular(12.r),
              ),
              child: Text(
                message.text,
                style: GoogleFonts.inter(
                    fontSize: 13.sp, color: AppColors.textPrimary),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildGenericMessage(AgentMessage message) {
    // Similar to status message but simpler
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

  Widget _buildInputArea(AgentChatController controller) {
    return Container(
      padding: EdgeInsets.all(16.r),
      decoration: BoxDecoration(
        color: Colors.white,
        border: Border(top: BorderSide(color: AppColors.border)),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.02),
            blurRadius: 10,
            offset: Offset(0, -2),
          ),
        ],
      ),
      child: SafeArea(
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            Expanded(
              child: Container(
                decoration: BoxDecoration(
                  color: AppColors.inputBackground,
                  borderRadius: BorderRadius.circular(24.r),
                  border: Border.all(color: AppColors.border),
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
                      child: TextField(
                        controller: controller.textController,
                        decoration: InputDecoration(
                          hintText: AppStrings.typeMessage,
                          hintStyle: GoogleFonts.inter(
                            fontSize: 14.sp,
                            color: AppColors.textTertiary,
                          ),
                          border: InputBorder.none,
                          contentPadding: EdgeInsets.symmetric(vertical: 12.h),
                        ),
                        style: GoogleFonts.inter(fontSize: 14.sp),
                        maxLines: 4,
                        minLines: 1,
                        textInputAction: TextInputAction.send,
                        onSubmitted: controller.sendMessage,
                      ),
                    ),
                    SizedBox(width: 8.w),
                  ],
                ),
              ),
            ),
            SizedBox(width: 12.w),
            Obx(() => AnimatedContainer(
                  duration: Duration(milliseconds: 200),
                  width: 48.r,
                  height: 48.r,
                  decoration: BoxDecoration(
                    gradient: controller.isAgentWorking.value
                        ? LinearGradient(
                            colors: [Colors.grey[400]!, Colors.grey[400]!])
                        : LinearGradient(
                            colors: [
                              AppColors.primary,
                              const Color(0xFF6366F1)
                            ], // Modern gradients
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
                          ? null
                          : () => controller
                              .sendMessage(controller.textController.text),
                      child: Center(
                        child: Icon(
                          controller.isAgentWorking.value
                              ? StatusIcons.processing
                              : StatusIcons.send,
                          color: Colors.white,
                          size: 20.r,
                        ),
                      ),
                    ),
                  ),
                )
                    .animate(target: controller.isAgentWorking.value ? 1 : 0)
                    .scale(
                        begin: Offset(1, 1),
                        end: Offset(0.9, 0.9),
                        duration: 200.ms)),
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
                color: AppColors.textPrimary,
              ),
            ).animate().fadeIn(delay: 200.ms).slideY(begin: 0.2, end: 0),
            SizedBox(height: 8.h),
            Text(
              AppStrings.startConversationSubtitle,
              style: GoogleFonts.inter(
                fontSize: 14.sp,
                color: AppColors.textSecondary,
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
            color: AppColors.textPrimary),
      ),
      onPressed: () {
        controller.textController.text = label;
        // Optionally auto-send or just fill
      },
      backgroundColor: Colors.white,
      shadowColor: Colors.black.withOpacity(0.05),
      elevation: 2,
      padding: EdgeInsets.all(8.r),
      shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(24.r),
          side: BorderSide(color: AppColors.border, width: 1.0)),
    );
  }
}
