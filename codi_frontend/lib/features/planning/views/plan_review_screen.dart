/// Plan review screen for approving/rejecting implementation plans
library;

import 'package:flutter/material.dart';
import 'package:flutter_highlight/flutter_highlight.dart';
import 'package:flutter_highlight/themes/atom-one-dark.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:get/get.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:markdown/markdown.dart' as md;

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

    // Only load from API if we don't have this plan already, or if it has no markdown
    if (planId != null) {
      final currentPlan = controller.currentPlan.value;
      final needsLoad = currentPlan == null ||
          currentPlan.id != planId ||
          currentPlan.markdownContent.isEmpty;
      if (needsLoad) {
        controller.loadPlan(planId);
      }
    }

    return Scaffold(
      backgroundColor: Get.theme.scaffoldBackgroundColor,
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
      backgroundColor: AppColors.backgroundDark,
      elevation: 0,
      leading: IconButton(
        icon: const Icon(Icons.close, color: Colors.white),
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
              color: Colors.white,
            ),
          ),
          Obx(() {
            if (controller.currentPlan.value != null) {
              return Text(
                controller.currentPlan.value!.title,
                style: GoogleFonts.inter(
                  fontSize: 12,
                  color: Colors.white70,
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
          icon: const Icon(Icons.share_outlined, color: Colors.white70),
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
        color: AppColors.backgroundDark,
        border: Border(
          bottom: BorderSide(color: Colors.grey[800]!),
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
                  padding:
                      const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  decoration: BoxDecoration(
                    color: AppColors.primary.withOpacity(0.2),
                    borderRadius: BorderRadius.circular(20),
                    border:
                        Border.all(color: AppColors.primary.withOpacity(0.5)),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(Icons.schedule,
                          size: 14, color: AppColors.primaryLight),
                      const SizedBox(width: 4),
                      Text(
                        plan.estimatedTime ?? 'Not estimated',
                        style: GoogleFonts.inter(
                          fontSize: 12,
                          fontWeight: FontWeight.w600,
                          color: AppColors.primaryLight,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 12),
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  decoration: BoxDecoration(
                    color: AppColors.success.withOpacity(0.2),
                    borderRadius: BorderRadius.circular(20),
                    border:
                        Border.all(color: AppColors.success.withOpacity(0.5)),
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
                color: Colors.grey[400],
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
      color: AppColors.backgroundDark,
      child: Obx(() {
        final plan = controller.currentPlan.value;
        final markdown = plan?.markdownContent ?? '';

        return Markdown(
          data: markdown,
          selectable: true,
          builders: {
            'code': CodeElementBuilder(),
          },
          styleSheet: MarkdownStyleSheet(
            h1: GoogleFonts.inter(
              fontSize: 24,
              fontWeight: FontWeight.w700,
              color: Colors.white,
            ),
            h2: GoogleFonts.inter(
              fontSize: 20,
              fontWeight: FontWeight.w600,
              color: Colors.white,
            ),
            h3: GoogleFonts.inter(
              fontSize: 16,
              fontWeight: FontWeight.w600,
              color: Colors.white,
            ),
            p: GoogleFonts.inter(
              fontSize: 14,
              color: Colors.white,
              height: 1.6,
            ),
            listBullet: GoogleFonts.inter(
              fontSize: 14,
              color: Colors.white,
            ),
            code: GoogleFonts.jetBrainsMono(
              fontSize: 13,
              backgroundColor: AppColors.surfaceDarkVariant,
              color: Colors.white70,
            ),
            codeblockDecoration: BoxDecoration(
              color: Colors.transparent,
              borderRadius: BorderRadius.circular(8),
            ),
            blockquote: GoogleFonts.inter(
              fontSize: 14,
              color: Colors.grey[400],
              fontStyle: FontStyle.italic,
            ),
            blockquoteDecoration: BoxDecoration(
              color: const Color(0xFFFEF3C7).withOpacity(0.1),
              border: const Border(
                left: BorderSide(color: Color(0xFFF59E0B), width: 4),
              ),
            ),
          ),
          padding: const EdgeInsets.all(16),
          onTapLink: (text, href, title) {
            if (href != null) {
              // TODO: Handle link taps
            }
          },
        );
      }),
    );
  }

  Widget _buildActionBar() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.surfaceDark,
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.2),
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

class CodeElementBuilder extends MarkdownElementBuilder {
  @override
  Widget? visitElementAfter(md.Element element, TextStyle? preferredStyle) {
    var language = '';

    if (element.attributes['class'] != null) {
      String lg = element.attributes['class'] as String;
      // "language-dart" -> "dart"
      language = lg.substring(9);
    }

    if (language.isEmpty) {
      return null;
    }

    return Container(
      width: double.infinity,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(8),
        color: AppColors.surfaceDarkVariant,
        border: Border.all(color: Colors.white.withOpacity(0.1)),
      ),
      child: HighlightView(
        element.textContent,
        language: language,
        theme: atomOneDarkTheme,
        textStyle: GoogleFonts.jetBrainsMono(fontSize: 13),
        padding: const EdgeInsets.all(12),
      ),
    );
  }
}
