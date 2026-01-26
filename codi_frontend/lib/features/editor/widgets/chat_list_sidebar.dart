import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'package:timeago/timeago.dart' as timeago;

import '../../../core/constants/app_colors.dart';
import '../controllers/multi_chat_controller.dart';
import '../models/chat_session_model.dart';

class ChatListSidebar extends GetView<MultiChatController> {
  const ChatListSidebar({super.key});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 250,
      decoration: const BoxDecoration(
        color: Color(0xFF1E1E1E), // Slightly fast sidebar background
        border: Border(right: BorderSide(color: AppColors.border, width: 1)),
      ),
      child: Column(
        children: [
          // Header with New Chat button
          Padding(
            padding: const EdgeInsets.all(12),
            child: SizedBox(
              width: double.infinity,
              child: ElevatedButton.icon(
                onPressed: controller.createNewChat,
                icon: const Icon(Icons.add, size: 18),
                label: const Text('New Chat'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppColors.primary,
                  foregroundColor: Colors.white,
                  elevation: 0,
                  padding: const EdgeInsets.symmetric(vertical: 12),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(8),
                  ),
                ),
              ),
            ),
          ),
          
          // Chat List
          Expanded(
            child: Obx(() {
              if (controller.isLoading.value) {
                return const Center(child: CircularProgressIndicator());
              }
              
              if (controller.sessions.isEmpty) {
                return const Center(
                  child: Text(
                    'No active chats',
                    style: TextStyle(color: Colors.grey),
                  ),
                );
              }

              return ListView.builder(
                padding: const EdgeInsets.symmetric(horizontal: 8),
                itemCount: controller.sessions.length,
                itemBuilder: (context, index) {
                  final session = controller.sessions[index];
                  return _buildChatSessionItem(session);
                },
              );
            }),
          ),
          
          // Bottom Actions
          Container(
            padding: const EdgeInsets.all(8),
            decoration: const BoxDecoration(
              border: Border(top: BorderSide(color: AppColors.border)),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                IconButton(
                  onPressed: controller.deleteActiveSession,
                  icon: const Icon(Icons.delete_outline, size: 20),
                  color: Colors.grey,
                  tooltip: 'Delete active chat',
                ),
                TextButton.icon(
                  onPressed: () {
                    // TODO: Show archived chats
                  },
                  icon: const Icon(Icons.archive_outlined, size: 18, color: Colors.grey),
                  label: const Text('Archived', style: TextStyle(color: Colors.grey)),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildChatSessionItem(ChatSession session) {
    return Obx(() {
      final isActive = controller.activeSession.value?.id == session.id;
      
      return Container(
        margin: const EdgeInsets.only(bottom: 4),
        decoration: BoxDecoration(
          color: isActive ? AppColors.surface : Colors.transparent,
          borderRadius: BorderRadius.circular(6),
        ),
        child: InkWell(
          onTap: () => controller.switchSession(session.id),
          borderRadius: BorderRadius.circular(6),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Title
                Text(
                  session.title,
                  style: TextStyle(
                    color: isActive ? Colors.white : Colors.grey[400],
                    fontSize: 13,
                    fontWeight: isActive ? FontWeight.w600 : FontWeight.normal,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
                const SizedBox(height: 4),
                // Metadata
                Row(
                  children: [
                    Text(
                      timeago.format(session.lastMessageAt ?? session.createdAt),
                      style: TextStyle(
                        color: Colors.grey[600],
                        fontSize: 11,
                      ),
                    ),
                    const Spacer(),
                    if (session.messageCount > 0)
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                        decoration: BoxDecoration(
                          color: AppColors.primary.withOpacity(0.2),
                          borderRadius: BorderRadius.circular(10),
                        ),
                        child: Text(
                          '${session.messageCount}',
                          style: TextStyle(
                            color: AppColors.primary,
                            fontSize: 10,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ),
                  ],
                ),
              ],
            ),
          ),
        ),
      );
    });
  }
}
