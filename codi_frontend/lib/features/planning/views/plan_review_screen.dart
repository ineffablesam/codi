/// Plan review screen for approving/rejecting implementation plans
library;

import 'package:flutter/material.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:get/get.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../../core/constants/app_colors.dart';
import '../controllers/planning_controller.dart';

/// Screen for reviewing implementation plans before approval
class PlanReviewScreen extends GetView<PlanningController> {
  const PlanReviewScreen({super.key});

  @override
  Widget build(BuildContext context) {
    // Load plan if passed as argument
    final args = Get.arguments as Map<String, dynamic>?;
    final planId = args?['planId'] as int?;

    if (planId != null && controller.currentPlan.value?.id != planId) {
      controller.loadPlan(planId);
    }

    return Scaffold(
      backgroundColor: const Color(0xFFF9FAFB),
      appBar: _buildAppBar(),
      body: Obx(() {
        if (controller.isLoadingPlan.value) {
          return _buildLoadingState();
        }

        if (controller.currentPlan.value == null) {
          return _buildEmptyState();
        }

        return _buildPlanContent();
      }),
      bottomNavigationBar: _buildActionBar(),
    );
  }

  PreferredSizeWidget _buildAppBar() {
    return AppBar(
      backgroundColor: Colors.white,
      elevation: 0,
      leading: IconButton(
        icon: const Icon(Icons.close, color: Colors.black87),
        onPressed: _handleClose,
      ),
      title: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Implementation Plan',
            style: GoogleFonts.inter(
              fontSize: 18,
              fontWeight: FontWeight.w600,
              color: Colors.black87,
            ),
          ),
          Obx(() {
            if (controller.currentPlan.value != null) {
              return Text(
                controller.currentPlan.value!.title,
                style: GoogleFonts.inter(
                  fontSize: 12,
                  color: Colors.grey[600],
                ),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              );
            }
            return const SizedBox.shrink();
          }),
        ],
      ),
      actions: [
        IconButton(
          icon: const Icon(Icons.share_outlined, color: Colors.black54),
          onPressed: () {
            Get.snackbar('Share', 'Plan sharing coming soon');
          },
        ),
      ],
    );
  }

  Widget _buildPlanContent() {
    return Column(
      children: [
        _buildPlanHeader(),
        Expanded(
          child: _buildMarkdownViewer(),
        ),
      ],
    );
  }

  Widget _buildPlanHeader() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        border: Border(
          bottom: BorderSide(color: Colors.grey[200]!),
        ),
      ),
      child: Obx(() {
        final plan = controller.currentPlan.value!;

        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  decoration: BoxDecoration(
                    color: AppColors.primary.withOpacity(0.1),
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(color: AppColors.primary.withOpacity(0.3)),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(Icons.schedule, size: 14, color: AppColors.primary),
                      const SizedBox(width: 4),
                      Text(
                        plan.estimatedTime ?? 'Unknown',
                        style: GoogleFonts.inter(
                          fontSize: 12,
                          fontWeight: FontWeight.w600,
                          color: AppColors.primary,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 12),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  decoration: BoxDecoration(
                    color: AppColors.success.withOpacity(0.1),
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(color: AppColors.success.withOpacity(0.3)),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(Icons.task_alt, size: 14, color: AppColors.success),
                      const SizedBox(width: 4),
                      Text(
                        '${plan.totalTasks} tasks',
                        style: GoogleFonts.inter(
                          fontSize: 12,
                          fontWeight: FontWeight.w600,
                          color: AppColors.success,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Text(
              'Review this plan carefully before approving.',
              style: GoogleFonts.inter(
                fontSize: 13,
                color: Colors.grey[700],
              ),
            ),
            const SizedBox(height: 4),
            Text(
              'Once approved, agents will begin implementing the tasks automatically.',
              style: GoogleFonts.inter(
                fontSize: 12,
                color: Colors.grey[600],
              ),
            ),
          ],
        );
      }),
    );
  }

  Widget _buildMarkdownViewer() {
    return Container(
      color: Colors.white,
      child: Obx(() {
        final markdown = controller.currentPlan.value?.markdownContent ?? '';

        return Markdown(
          data: markdown,
          selectable: true,
          styleSheet: MarkdownStyleSheet(
            h1: GoogleFonts.inter(
              fontSize: 24,
              fontWeight: FontWeight.w700,
              color: Colors.black87,
            ),
            h2: GoogleFonts.inter(
              fontSize: 20,
              fontWeight: FontWeight.w600,
              color: Colors.black87,
            ),
            h3: GoogleFonts.inter(
              fontSize: 16,
              fontWeight: FontWeight.w600,
              color: Colors.black87,
            ),
            p: GoogleFonts.inter(
              fontSize: 14,
              color: Colors.black87,
              height: 1.6,
            ),
            listBullet: GoogleFonts.inter(
              fontSize: 14,
              color: Colors.black87,
            ),
            code: GoogleFonts.jetBrainsMono(
              fontSize: 13,
              backgroundColor: const Color(0xFFF3F4F6),
            ),
            codeblockDecoration: BoxDecoration(
              color: const Color(0xFFF3F4F6),
              borderRadius: BorderRadius.circular(8),
            ),
            blockquote: GoogleFonts.inter(
              fontSize: 14,
              color: Colors.grey[700],
              fontStyle: FontStyle.italic,
            ),
            blockquoteDecoration: BoxDecoration(
              color: const Color(0xFFFEF3C7).withOpacity(0.3),
              border: const Border(
                left: BorderSide(color: Color(0xFFF59E0B), width: 4),
              ),
            ),
          ),
          padding: const EdgeInsets.all(16),
        );
      }),
    );
  }

  Widget _buildActionBar() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.05),
            blurRadius: 10,
            offset: const Offset(0, -2),
          ),
        ],
      ),
      child: SafeArea(
        child: Obx(() {
          if (controller.isSubmitting.value) {
            return const Center(
              child: CircularProgressIndicator(),
            );
          }

          return Row(
            children: [
              Expanded(
                child: OutlinedButton(
                  onPressed: _handleReject,
                  style: OutlinedButton.styleFrom(
                    foregroundColor: AppColors.error,
                    side: BorderSide(color: AppColors.error),
                    padding: const EdgeInsets.symmetric(vertical: 14),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12),
                    ),
                  ),
                  child: Text(
                    'Decline',
                    style: GoogleFonts.inter(
                      fontSize: 15,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                flex: 2,
                child: ElevatedButton(
                  onPressed: _handleApprove,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppColors.success,
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(vertical: 14),
                    elevation: 0,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12),
                    ),
                  ),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const Icon(Icons.check_circle, size: 20),
                      const SizedBox(width: 8),
                      Text(
                        'Approve & Start',
                        style: GoogleFonts.inter(
                          fontSize: 15,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          );
        }),
      ),
    );
  }

  Widget _buildLoadingState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const CircularProgressIndicator(),
          const SizedBox(height: 16),
          Text(
            'Loading plan...',
            style: GoogleFonts.inter(
              fontSize: 14,
              color: Colors.grey[600],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.description_outlined, size: 64, color: Colors.grey[400]),
          const SizedBox(height: 16),
          Text(
            'No plan to display',
            style: GoogleFonts.inter(
              fontSize: 16,
              fontWeight: FontWeight.w600,
              color: Colors.grey[700],
            ),
          ),
        ],
      ),
    );
  }

  void _handleApprove() {
    Get.dialog(
      AlertDialog(
        title: Text(
          'Approve Plan?',
          style: GoogleFonts.inter(fontWeight: FontWeight.w600),
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'This will start the automated implementation process.',
              style: GoogleFonts.inter(fontSize: 14),
            ),
            const SizedBox(height: 12),
            Text(
              'You can monitor progress in real-time through the agent chat panel.',
              style: GoogleFonts.inter(
                fontSize: 13,
                color: Colors.grey[600],
              ),
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
              Get.back();
              controller.approvePlan();
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: AppColors.success,
            ),
            child: const Text('Approve'),
          ),
        ],
      ),
    );
  }

  void _handleReject() {
    final commentController = TextEditingController();

    Get.dialog(
      AlertDialog(
        title: Text(
          'Decline Plan',
          style: GoogleFonts.inter(fontWeight: FontWeight.w600),
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Why are you declining this plan? (Optional)',
              style: GoogleFonts.inter(fontSize: 14),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: commentController,
              maxLines: 3,
              decoration: InputDecoration(
                hintText: 'e.g., "Please add authentication first"',
                hintStyle: GoogleFonts.inter(fontSize: 13),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(8),
                ),
              ),
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
              Get.back();
              controller.rejectPlan(
                comment: commentController.text.trim().isNotEmpty
                    ? commentController.text.trim()
                    : null,
              );
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: AppColors.error,
            ),
            child: const Text('Decline'),
          ),
        ],
      ),
    );
  }

  void _handleClose() {
    Get.dialog(
      AlertDialog(
        title: Text(
          'Close Plan Review?',
          style: GoogleFonts.inter(fontWeight: FontWeight.w600),
        ),
        content: Text(
          'You can review this plan later from the project dashboard.',
          style: GoogleFonts.inter(fontSize: 14),
        ),
        actions: [
          TextButton(
            onPressed: () => Get.back(),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () {
              Get.back(); // Close dialog
              Get.back(); // Close plan screen
            },
            child: const Text('Close'),
          ),
        ],
      ),
    );
  }
}
