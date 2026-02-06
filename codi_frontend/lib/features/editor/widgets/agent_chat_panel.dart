/// Simplified agent chat panel
library;

import 'package:codi_frontend/features/editor/widgets/chat/generating_indicator.dart';
import 'package:codi_frontend/features/editor/widgets/chat/operation_messages.dart';
import 'package:codi_frontend/features/editor/widgets/chat/success_message.dart';
import 'package:codi_frontend/features/editor/widgets/chat/thinking_message.dart';
import 'package:codi_frontend/features/editor/widgets/chat/tool_execution_card.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:get/get.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';
import 'package:super_context_menu/super_context_menu.dart';

import '../../../core/constants/app_colors.dart';
import '../../../core/constants/app_strings.dart';
import '../../../core/utils/sf_font.dart';
import '../../projects/controllers/project_setup_controller.dart';
import '../constants/chat_icons.dart';
import '../controllers/agent_chat_controller.dart';
import '../models/agent_message_model.dart';
import 'chat_list_sidebar.dart';

/// Helper class for grouping tool messages
class _ToolGroup {
  final List<AgentMessage> messages;
  _ToolGroup(this.messages);
}

/// Helper class for pairing tool execution with its result
class _ToolPair {
  final AgentMessage execution;
  final AgentMessage? result;
  _ToolPair(this.execution, this.result);
}

/// Helper class for a sequential group of the same tool type
class _SequentialToolGroup {
  final String tool;
  final List<_ToolPair> pairs;
  _SequentialToolGroup(this.tool, this.pairs);
}

/// Expandable widget for grouped tool messages with hierarchical nesting
class _ExpandableToolGroup extends StatefulWidget {
  final _ToolGroup group;
  final IconData Function(String) getIcon;
  final bool isLatest;

  const _ExpandableToolGroup({
    required this.group,
    required this.getIcon,
    this.isLatest = false,
  });

  @override
  State<_ExpandableToolGroup> createState() => _ExpandableToolGroupState();
}

class _ExpandableToolGroupState extends State<_ExpandableToolGroup> {
  bool _isExpanded = false;
  int? _expandedGroupIndex;

  @override
  void initState() {
    super.initState();
    // Latest group starts expanded
    _isExpanded = widget.isLatest;
  }

  @override
  void didUpdateWidget(_ExpandableToolGroup oldWidget) {
    super.didUpdateWidget(oldWidget);
    // Auto-expand when this becomes the latest group
    if (widget.isLatest && !oldWidget.isLatest) {
      setState(() => _isExpanded = true);
    }
  }

  @override
  Widget build(BuildContext context) {
    // 1. First, pair all executions with results into a flat list of _ToolPair
    final allPairs = <_ToolPair>[];
    AgentMessage? pendingExecution;
    for (final msg in widget.group.messages) {
      if (msg.type == MessageType.toolExecution) {
        if (pendingExecution != null) {
          allPairs.add(_ToolPair(pendingExecution, null));
        }
        pendingExecution = msg;
      } else if (msg.type == MessageType.toolResult &&
          pendingExecution != null) {
        allPairs.add(_ToolPair(pendingExecution, msg));
        pendingExecution = null;
      }
    }
    if (pendingExecution != null) {
      allPairs.add(_ToolPair(pendingExecution, null));
    }

    // 2. Group the consecutive _ToolPair objects by tool type
    final sequentialGroups = <_SequentialToolGroup>[];
    for (final pair in allPairs) {
      final tool = pair.execution.tool ?? 'unknown';
      if (sequentialGroups.isNotEmpty && sequentialGroups.last.tool == tool) {
        sequentialGroups.last.pairs.add(pair);
      } else {
        sequentialGroups.add(_SequentialToolGroup(tool, [pair]));
      }
    }

    // Count total executions
    final totalExecutions = allPairs.length;

    // Latest group index for auto-expansion and highlighting
    final latestGroupIndex = sequentialGroups.length - 1;

    return Padding(
      padding: EdgeInsets.only(bottom: 4.h, left: 40.w),
      child: Container(
        decoration: BoxDecoration(
          color: Colors.grey[900],
          borderRadius: BorderRadius.circular(6.r),
          border: Border.all(color: Colors.grey[800]!, width: 0.5),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Top level header
            GestureDetector(
              onTap: () => setState(() => _isExpanded = !_isExpanded),
              behavior: HitTestBehavior.opaque,
              child: Padding(
                padding: EdgeInsets.symmetric(horizontal: 10.w, vertical: 8.h),
                child: Row(
                  children: [
                    Icon(
                      LucideIcons.layers,
                      size: 12.r,
                      color: Colors.blue[400],
                    ),
                    SizedBox(width: 6.w),
                    Text(
                      '$totalExecutions operations',
                      style: GoogleFonts.jetBrainsMono(
                        fontSize: 10.sp,
                        fontWeight: FontWeight.w500,
                        color: Colors.grey[300],
                      ),
                    ),
                    const Spacer(),
                    AnimatedRotation(
                      turns: _isExpanded ? 0.5 : 0,
                      duration: const Duration(milliseconds: 200),
                      child: Icon(
                        LucideIcons.chevronDown,
                        size: 12.r,
                        color: Colors.grey[600],
                      ),
                    ),
                  ],
                ),
              ),
            ),
            // Second level: Tool type groups
            AnimatedSize(
              duration: const Duration(milliseconds: 200),
              curve: Curves.easeInOut,
              child: _isExpanded
                  ? Padding(
                      padding:
                          EdgeInsets.only(left: 8.w, right: 8.w, bottom: 8.h),
                      child: Column(
                        children: sequentialGroups.asMap().entries.map((entry) {
                          final index = entry.key;
                          final sGroup = entry.value;
                          final toolName = sGroup.tool
                              .split('_')
                              .map((w) => w.isNotEmpty
                                  ? '${w[0].toUpperCase()}${w.substring(1)}'
                                  : '')
                              .join(' ');
                          final messages = sGroup.pairs;
                          final isLatestType = index == latestGroupIndex;
                          final isTypeExpanded =
                              _expandedGroupIndex == index || isLatestType;

                          return Container(
                            margin: EdgeInsets.only(bottom: 2.h),
                            decoration: BoxDecoration(
                              color: Colors.grey[850],
                              borderRadius: BorderRadius.circular(4.r),
                            ),
                            child: Column(
                              children: [
                                // Tool type header
                                GestureDetector(
                                  onTap: () => setState(() {
                                    _expandedGroupIndex =
                                        isTypeExpanded ? -1 : index;
                                  }),
                                  behavior: HitTestBehavior.opaque,
                                  child: Padding(
                                    padding: EdgeInsets.symmetric(
                                      horizontal: 8.w,
                                      vertical: 6.h,
                                    ),
                                    child: Row(
                                      children: [
                                        Icon(
                                          widget.getIcon(sGroup.tool),
                                          size: 10.r,
                                          color: isLatestType && widget.isLatest
                                              ? Colors.blue[400]
                                              : Colors.grey[500],
                                        ),
                                        SizedBox(width: 6.w),
                                        Text(
                                          '$toolName × ${messages.length}',
                                          style: GoogleFonts.jetBrainsMono(
                                            fontSize: 9.sp,
                                            color:
                                                isLatestType && widget.isLatest
                                                    ? Colors.grey[300]
                                                    : Colors.grey[500],
                                          ),
                                        ),
                                        const Spacer(),
                                        if (messages.length > 1)
                                          AnimatedRotation(
                                            turns: isTypeExpanded ? 0.5 : 0,
                                            duration: const Duration(
                                                milliseconds: 150),
                                            child: Icon(
                                              LucideIcons.chevronDown,
                                              size: 10.r,
                                              color: Colors.grey[600],
                                            ),
                                          ),
                                      ],
                                    ),
                                  ),
                                ),
                                // Third level: Individual files with results
                                AnimatedSize(
                                  duration: const Duration(milliseconds: 150),
                                  curve: Curves.easeInOut,
                                  child: isTypeExpanded && messages.length > 0
                                      ? Padding(
                                          padding: EdgeInsets.only(
                                            left: 16.w,
                                            right: 8.w,
                                            bottom: 4.h,
                                          ),
                                          child: Column(
                                            crossAxisAlignment:
                                                CrossAxisAlignment.start,
                                            children: messages.map((pair) {
                                              final isLast =
                                                  pair == messages.last &&
                                                      isLatestType &&
                                                      widget.isLatest;
                                              final hasResult =
                                                  pair.result != null &&
                                                      pair.result!.toolResult !=
                                                          null &&
                                                      pair.result!.toolResult!
                                                          .isNotEmpty;

                                              return Column(
                                                crossAxisAlignment:
                                                    CrossAxisAlignment.start,
                                                children: [
                                                  // File/operation row
                                                  Padding(
                                                    padding: EdgeInsets.only(
                                                        bottom: 2.h),
                                                    child: Row(
                                                      children: [
                                                        Container(
                                                          width: 4.r,
                                                          height: 4.r,
                                                          decoration:
                                                              BoxDecoration(
                                                            shape:
                                                                BoxShape.circle,
                                                            color: isLast
                                                                ? Colors
                                                                    .blue[400]
                                                                : Colors
                                                                    .grey[600],
                                                          ),
                                                        ),
                                                        SizedBox(width: 6.w),
                                                        Expanded(
                                                          child: Text(
                                                            pair.execution
                                                                    .filePath ??
                                                                pair.execution
                                                                    .text,
                                                            style: GoogleFonts
                                                                .jetBrainsMono(
                                                              fontSize: 8.sp,
                                                              color: isLast
                                                                  ? Colors
                                                                      .grey[300]
                                                                  : Colors.grey[
                                                                      600],
                                                            ),
                                                            maxLines: 1,
                                                            overflow:
                                                                TextOverflow
                                                                    .ellipsis,
                                                          ),
                                                        ),
                                                        if (hasResult)
                                                          Icon(
                                                            LucideIcons.check,
                                                            size: 8.r,
                                                            color: Colors
                                                                .green[400],
                                                          ),
                                                      ],
                                                    ),
                                                  ),
                                                  // Result preview (truncated)
                                                  if (hasResult &&
                                                      pair.result!.toolResult!
                                                              .length >
                                                          10)
                                                    Padding(
                                                      padding: EdgeInsets.only(
                                                          left: 10.w,
                                                          bottom: 4.h),
                                                      child: Text(
                                                        pair.result!.toolResult!
                                                                    .length >
                                                                100
                                                            ? '${pair.result!.toolResult!.substring(0, 100)}...'
                                                            : pair.result!
                                                                .toolResult!,
                                                        style: GoogleFonts
                                                            .jetBrainsMono(
                                                          fontSize: 7.sp,
                                                          color:
                                                              Colors.grey[700],
                                                        ),
                                                        maxLines: 2,
                                                        overflow: TextOverflow
                                                            .ellipsis,
                                                      ),
                                                    ),
                                                ],
                                              );
                                            }).toList(),
                                          ),
                                        )
                                      : const SizedBox.shrink(),
                                ),
                              ],
                            ),
                          );
                        }).toList(),
                      ),
                    )
                  : const SizedBox.shrink(),
            ),
          ],
        ),
      ),
    );
  }
}

class AgentChatPanel extends StatelessWidget {
  const AgentChatPanel({super.key});

  @override
  Widget build(BuildContext context) {
    final controller = Get.find<AgentChatController>();
    final projectSetupController = Get.find<ProjectSetupController>();

    return Container(
      color: Get.theme.cardTheme.color,
      child: Obx(() {
        final isInitialSetup = projectSetupController.isInitialSetup.value;

        return Stack(
          children: [
            // Main chat area
            Column(
              children: [
                // Header with menu button
                if (!isInitialSetup) _buildHeader(controller),
                Expanded(child: _buildMessageList(controller)),
                _buildInputArea(controller),
              ],
            ),

            // Sliding drawer for chat list
            if (!isInitialSetup) _buildChatListDrawer(controller),
          ],
        );
      }),
    );
  }

  Widget _buildHeader(AgentChatController controller) {
    return Container(
      padding: EdgeInsets.symmetric(horizontal: 16.w, vertical: 12.h),
      decoration: BoxDecoration(
        color: Get.theme.cardTheme.color,
        border: Border(
          bottom: BorderSide(
            color: Get.theme.dividerColor.withOpacity(0.2),
          ),
        ),
      ),
      child: SafeArea(
        bottom: false,
        child: Row(
          children: [
            // Menu button to open drawer
            IconButton(
              onPressed: () {
                controller.toggleChatListDrawer();
              },
              icon: Icon(
                LucideIcons.menu,
                size: 24.r,
                color: Get.textTheme.titleMedium?.color,
              ),
              padding: EdgeInsets.zero,
              constraints: BoxConstraints(
                minWidth: 40.r,
                minHeight: 40.r,
              ),
            ),
            SizedBox(width: 12.w),

            // Current chat title or app name
            Expanded(
              child: Obx(() {
                final currentChat = controller.currentChatTitle.value;
                return Text(
                  currentChat.isEmpty ? 'AI Agent' : currentChat,
                  style: SFPro.font(
                    fontSize: 16.sp,
                    fontWeight: FontWeight.w600,
                    color: Get.textTheme.titleMedium?.color,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                );
              }),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildChatListDrawer(AgentChatController controller) {
    return Obx(() {
      final isOpen = controller.isChatListDrawerOpen.value;

      return AnimatedPositioned(
        duration: Duration(milliseconds: 300),
        curve: Curves.easeInOut,
        left: isOpen ? 0 : -280.w,
        top: 0,
        bottom: 0,
        width: 280.w,
        child: GestureDetector(
          onHorizontalDragEnd: (details) {
            if (details.primaryVelocity! < -500) {
              controller.closeChatListDrawer();
            }
          },
          child: Material(
            elevation: 16,
            shadowColor: Colors.black.withOpacity(0.3),
            child: Container(
              color: Get.theme.scaffoldBackgroundColor,
              child: SafeArea(
                child: Column(
                  children: [
                    // Drawer header
                    Container(
                      padding: EdgeInsets.all(16.r),
                      decoration: BoxDecoration(
                        border: Border(
                          bottom: BorderSide(
                            color: Get.theme.dividerColor.withOpacity(0.2),
                          ),
                        ),
                      ),
                      child: Row(
                        children: [
                          Text(
                            'Chats',
                            style: SFPro.font(
                              fontSize: 18.sp,
                              fontWeight: FontWeight.w600,
                              color: Get.textTheme.titleMedium?.color,
                            ),
                          ),
                          Spacer(),
                          IconButton(
                            onPressed: () => controller.closeChatListDrawer(),
                            icon: Icon(
                              LucideIcons.x,
                              size: 20.r,
                              color: Get.textTheme.bodyMedium?.color,
                            ),
                            padding: EdgeInsets.zero,
                            constraints: BoxConstraints(
                              minWidth: 32.r,
                              minHeight: 32.r,
                            ),
                          ),
                        ],
                      ),
                    ),

                    // Chat list content
                    Expanded(
                      child: ChatListSidebar(),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      );
    });
  }

  // Overlay to close drawer when tapping outside
  Widget _buildDrawerOverlay(AgentChatController controller) {
    return Obx(() {
      final isOpen = controller.isChatListDrawerOpen.value;

      return AnimatedOpacity(
        duration: Duration(milliseconds: 300),
        opacity: isOpen ? 1.0 : 0.0,
        child: isOpen
            ? GestureDetector(
                onTap: () => controller.closeChatListDrawer(),
                child: Container(
                  color: Colors.black.withOpacity(0.5),
                ),
              )
            : SizedBox.shrink(),
      );
    });
  }

  Widget _buildMessageList(AgentChatController controller) {
    return Obx(() {
      if (controller.messages.isEmpty) {
        return _buildEmptyState(controller);
      }

      // Group consecutive tool messages
      final groupedMessages = _groupMessages(controller.messages);

      final showIndicator = controller.showGeneratingIndicator.value;

      return ListView.builder(
        controller: controller.scrollController,
        padding: EdgeInsets.symmetric(horizontal: 16.w, vertical: 20.h),
        itemCount: groupedMessages.length + (showIndicator ? 1 : 0),
        itemBuilder: (context, index) {
          if (index == groupedMessages.length) {
            // Show "Crawling" for browser mode, "Generating" otherwise
            final indicatorText =
                controller.isBrowserAgentMode.value ? 'Crawling' : 'Generating';
            return GeneratingIndicator(text: indicatorText);
          }

          final item = groupedMessages[index];
          if (item is _ToolGroup) {
            // Check if this is the last group AND agent is still working
            final isLastGroup = index == groupedMessages.length - 1 ||
                !groupedMessages.skip(index + 1).any((m) => m is _ToolGroup);
            // Only show as "active" if agent is still working
            final isLatest = isLastGroup && controller.isAgentWorking.value;
            return _buildToolGroup(item, isLatest: isLatest);
          }
          return _buildMessage(item as AgentMessage);
        },
      );
    });
  }

  /// Group consecutive tool execution/result messages
  List<dynamic> _groupMessages(List<AgentMessage> messages) {
    final result = <dynamic>[];
    List<AgentMessage> currentToolGroup = [];

    for (final message in messages) {
      // Group both tool executions and their results
      if (message.type == MessageType.toolExecution ||
          message.type == MessageType.toolResult) {
        currentToolGroup.add(message);
      } else {
        // Flush tool group if any
        if (currentToolGroup.isNotEmpty) {
          if (currentToolGroup.length >= 2) {
            result.add(_ToolGroup(currentToolGroup.toList()));
          } else {
            result.addAll(currentToolGroup);
          }
          currentToolGroup.clear();
        }
        result.add(message);
      }
    }

    // Flush remaining tool group
    if (currentToolGroup.isNotEmpty) {
      if (currentToolGroup.length >= 2) {
        result.add(_ToolGroup(currentToolGroup.toList()));
      } else {
        result.addAll(currentToolGroup);
      }
    }

    return result;
  }

  Widget _buildToolGroup(_ToolGroup group, {bool isLatest = false}) {
    return _ExpandableToolGroup(
      group: group,
      getIcon: _getToolIcon,
      isLatest: isLatest,
    );
  }

  IconData _getToolIcon(String toolName) {
    switch (toolName) {
      case 'read_file':
        return LucideIcons.fileText;
      case 'write_file':
        return LucideIcons.filePlus;
      case 'edit_file':
        return LucideIcons.pen;
      case 'list_files':
        return LucideIcons.folderOpen;
      case 'search_files':
        return LucideIcons.search;
      case 'run_bash':
        return LucideIcons.terminal;
      case 'git_commit':
        return LucideIcons.gitCommitHorizontal;
      case 'docker_preview':
        return LucideIcons.cloud;
      default:
        return LucideIcons.wrench;
    }
  }

  Widget _buildMessage(AgentMessage message) {
    Widget messageWidget;

    switch (message.type) {
      case MessageType.user:
        messageWidget = _buildUserMessage(message);
        break;

      case MessageType.agentStatus:
        if (message.status == 'thinking' ||
            message.status == 'started' ||
            message.status == 'planning') {
          messageWidget = const ThinkingMessage();
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
    return ContextMenuWidget(
      child: Padding(
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
                  style: SFPro.font(
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
              child:
                  Icon(StatusIcons.user, size: 16.r, color: Colors.grey[600]),
            ),
          ],
        ),
      ).animate().fadeIn(duration: 300.ms).slideY(begin: 0.1, end: 0),
      menuProvider: (_) {
        return Menu(
          children: [
            MenuAction(
              title: "Copy",
              callback: () async {
                await Clipboard.setData(ClipboardData(text: message.text));
              },
            ),
          ],
        );
      },
    );
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
                style: SFPro.font(
                    fontSize: 13.sp, color: Get.textTheme.bodyMedium?.color),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildAgentResponseMessage(AgentMessage message) {
    return ContextMenuWidget(
      child: Padding(
        padding: EdgeInsets.only(bottom: 16.h),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            CircleAvatar(
              radius: 16.r,
              backgroundColor: AppColors.primary.withOpacity(0.1),
              child: Icon(AgentAvatarIcons.ai,
                  size: 20.r, color: AppColors.primary),
            ),
            SizedBox(width: 12.w),
            Expanded(
              child: Container(
                padding: EdgeInsets.all(16.r),
                decoration: BoxDecoration(
                  color: Colors.grey[900],
                  border: Border.all(color: Colors.grey[800]!),
                  borderRadius: BorderRadius.only(
                    topLeft: Radius.circular(4.r),
                    topRight: Radius.circular(16.r),
                    bottomLeft: Radius.circular(16.r),
                    bottomRight: Radius.circular(16.r),
                  ),
                ),
                child: MarkdownBody(
                  data: message.text,
                  styleSheet: MarkdownStyleSheet(
                    p: SFPro.font(
                      fontSize: 14.sp,
                      color: Colors.grey[300],
                      height: 1.5,
                    ),
                    h1: SFPro.font(
                      fontSize: 20.sp,
                      fontWeight: FontWeight.bold,
                      color: Colors.white,
                    ),
                    h2: SFPro.font(
                      fontSize: 18.sp,
                      fontWeight: FontWeight.bold,
                      color: Colors.white,
                    ),
                    h3: SFPro.font(
                      fontSize: 16.sp,
                      fontWeight: FontWeight.w600,
                      color: Colors.white,
                    ),
                    code: GoogleFonts.jetBrainsMono(
                      fontSize: 12.sp,
                      backgroundColor: Colors.grey[850],
                      color: Colors.blue[300],
                    ),
                    codeblockDecoration: BoxDecoration(
                      color: Colors.grey[850],
                      borderRadius: BorderRadius.circular(8.r),
                    ),
                    blockquoteDecoration: BoxDecoration(
                      color: Colors.grey[850],
                      border: Border(
                        left: BorderSide(color: Colors.grey[600]!, width: 4),
                      ),
                    ),
                    listBullet: SFPro.font(
                      fontSize: 14.sp,
                      color: Colors.grey[400],
                    ),
                    strong: SFPro.font(
                      fontWeight: FontWeight.bold,
                      color: Colors.white,
                    ),
                    em: SFPro.font(
                      style: FontStyle.italic,
                      color: Colors.grey[300],
                    ),
                  ),
                ),
              ),
            ),
          ],
        ),
      ).animate().fadeIn(duration: 300.ms).slideY(begin: 0.1, end: 0),
      menuProvider: (_) {
        return Menu(
          children: [
            MenuAction(
              title: "Copy",
              callback: () async {
                await Clipboard.setData(ClipboardData(text: message.text));
              },
            ),
          ],
        );
      },
    );
  }

  Widget _buildToolExecutionMessage(AgentMessage message) {
    return ToolExecutionCard(
      toolName: message.tool ?? 'unknown',
      details: message.text.isNotEmpty ? message.text : null,
      filePath: message.filePath,
      initiallyExpanded: !message.isCollapsed,
    );
  }

  Widget _buildToolResultMessage(AgentMessage message) {
    if (message.toolResult == null || message.toolResult!.isEmpty) {
      return const SizedBox.shrink();
    }

    // Use ToolExecutionCard for all tool results
    return ToolExecutionCard(
      toolName: message.tool ?? 'result',
      details: message.toolResult,
      filePath: message.filePath,
      initiallyExpanded: !message.isCollapsed,
    );
  }

  Widget _buildGenericMessage(AgentMessage message) {
    return Padding(
      padding: EdgeInsets.only(bottom: 12.h, left: 36.w),
      child: Text(
        message.text,
        style: SFPro.font(
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
                                  style: SFPro.font(
                                    fontSize: 14.sp,
                                    fontWeight: FontWeight.w600,
                                    color: Get.textTheme.titleMedium?.color,
                                  ),
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                ),
                              ),
                              Obx(() {
                                final isPending = message.planId ==
                                    controller.currentPendingPlanId.value;
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
                                    style: SFPro.font(
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
                                style: SFPro.font(
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
                                style: SFPro.font(
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
                                          style: SFPro.font(
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
                                          style: SFPro.font(
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
              style: SFPro.font(
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
      padding: EdgeInsets.only(
        left: 16.w,
        right: 16.w,
        top: 12.h,
        bottom: 32.h,
      ),
      decoration: BoxDecoration(
        color: Get.theme.cardTheme.color,
        border: Border(
          top: BorderSide(
            color: Get.theme.dividerColor.withOpacity(0.2),
          ),
        ),
      ),
      child: SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            // Browser Agent Mode Banner
            if (controller.isBrowserAgentMode.value)
              Container(
                margin: EdgeInsets.only(bottom: 12.h),
                padding: EdgeInsets.symmetric(horizontal: 12.w, vertical: 8.h),
                decoration: BoxDecoration(
                  color: AppColors.primary.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(8.r),
                  border: Border.all(
                    color: Get.theme.dividerColor.withOpacity(0.2),
                  ),
                ),
                child: Row(
                  children: [
                    Icon(
                      LucideIcons.globe,
                      size: 16.r,
                      color: AppColors.primary,
                    ),
                    SizedBox(width: 8.w),
                    Expanded(
                      child: Text(
                        'Browser Agent Mode - AI will control the browser',
                        style: SFPro.font(
                          fontSize: 10.sp,
                          color: AppColors.primary,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ),
                    GestureDetector(
                      onTap: controller.toggleBrowserAgentMode,
                      child: Icon(
                        LucideIcons.x,
                        size: 16.r,
                        color: AppColors.primary,
                      ),
                    ),
                  ],
                ),
              ),

            // Input Row
            Row(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                // Browser mode toggle
                GestureDetector(
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
                            : Get.theme.dividerColor.withOpacity(0.2),
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
                ),

                // Text input
                Expanded(
                  child: AnimatedContainer(
                    duration: const Duration(milliseconds: 150),
                    decoration: BoxDecoration(
                      color: Get.theme.inputDecorationTheme.fillColor,
                      borderRadius: BorderRadius.circular(24.r),
                      border: Border.all(
                        color: controller.isFocused.value
                            ? AppColors.primary
                            : Get.theme.dividerColor.withOpacity(0.2),
                        width: controller.isFocused.value ? 1.5 : 1,
                      ),
                    ),
                    child: Row(
                      children: [
                        SizedBox(width: 16.w),
                        Expanded(
                          child: TextField(
                            focusNode: controller.focusNode,
                            controller: controller.textController,
                            decoration: InputDecoration(
                              hintText: controller.isBrowserAgentMode.value
                                  ? 'Tell the browser what to do...'
                                  : AppStrings.typeMessage,
                              border: OutlineInputBorder(
                                borderRadius: BorderRadius.circular(24.r),
                                borderSide: BorderSide.none,
                              ),
                              enabledBorder: OutlineInputBorder(
                                borderRadius: BorderRadius.circular(24.r),
                                borderSide: BorderSide.none,
                              ),
                              focusedBorder: OutlineInputBorder(
                                borderRadius: BorderRadius.circular(24.r),
                                borderSide: BorderSide.none,
                              ),
                              contentPadding:
                                  EdgeInsets.symmetric(vertical: 12.h),
                            ),
                            maxLines: 4,
                            minLines: 1,
                            onSubmitted: (value) {
                              if (value.isNotEmpty) {
                                controller.sendMessage(value);
                              }
                            },
                          ),
                        ),
                        SizedBox(width: 8.w),
                      ],
                    ),
                  ),
                ),

                SizedBox(width: 12.w),

                // Send / Stop button
                AnimatedContainer(
                  duration: const Duration(milliseconds: 200),
                  width: 48.r,
                  height: 48.r,
                  decoration: BoxDecoration(
                    gradient: controller.isAgentWorking.value
                        ? LinearGradient(
                            colors: [
                              AppColors.error,
                              AppColors.error.withOpacity(0.8),
                            ],
                          )
                        : const LinearGradient(
                            colors: [
                              AppColors.primary,
                              Color(0xFF6366F1),
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
                          ? controller.stopTask
                          : () => controller.sendMessage(
                                controller.textController.text,
                              ),
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
                      target: controller.isAgentWorking.value ? 1 : 0,
                    )
                    .scale(
                      begin: Offset(1, 1),
                      end: Offset(0.9, 0.9),
                      duration: 200.ms,
                    ),
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
        padding: EdgeInsets.all(20.r),
        child: SingleChildScrollView(
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
                style: SFPro.font(
                  fontSize: 18.sp,
                  fontWeight: FontWeight.w600,
                  color: Get.textTheme.titleLarge?.color,
                ),
              ).animate().fadeIn(delay: 200.ms).slideY(begin: 0.2, end: 0),
              SizedBox(height: 8.h),
              Text(
                AppStrings.startConversationSubtitle,
                style: SFPro.font(
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
      ),
    );
  }

  Widget _buildSuggestionChip(
      IconData icon, String label, AgentChatController controller) {
    return ActionChip(
      avatar: Icon(icon, size: 16.r, color: AppColors.primary),
      label: Text(
        label,
        style: SFPro.font(
            fontSize: 13.sp,
            fontWeight: FontWeight.w500,
            color: Get.textTheme.bodyMedium?.color),
      ),
      onPressed: () {
        controller.textController.text = label;
      },
      backgroundColor: Get.theme.focusColor.withOpacity(0.05),
      shadowColor: Colors.black.withOpacity(0.05),
      elevation: 2,
      padding: EdgeInsets.all(8.r),
      shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(24.r),
          side: BorderSide(
              color: Get.theme.focusColor.withOpacity(0.1), width: 1.0)),
    );
  }
}
