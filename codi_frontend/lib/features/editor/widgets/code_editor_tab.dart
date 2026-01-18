/// Code editor tab widget with file tree, editor, and commit panel
library;

import 'package:flutter/material.dart';
import 'package:flutter_code_editor/flutter_code_editor.dart';
import 'package:flutter_highlight/themes/vs2015.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:get/get.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../../core/constants/app_colors.dart';
import '../controllers/code_editor_controller.dart';
import '../controllers/commit_panel_controller.dart';
import '../controllers/file_tree_controller.dart';
import '../models/file_node.dart';

/// Main code editor tab with file tree, editor, and commit panel
class CodeEditorTab extends StatelessWidget {
  const CodeEditorTab({super.key});

  @override
  Widget build(BuildContext context) {
    final isLandscape =
        MediaQuery.of(context).orientation == Orientation.landscape;

    if (isLandscape) {
      return _buildLandscapeLayout();
    }
    return _buildPortraitLayout();
  }

  Widget _buildPortraitLayout() {
    return Column(
      children: [
        // File tree header
        _buildFileTreeHeader(),
        // Content area
        Expanded(
          child: Column(
            children: [
              // Collapsible file tree
              const _FileTreePanel(),
              const Divider(height: 1),
              // Code editor
              const Expanded(child: _CodeEditorPanel()),
            ],
          ),
        ),
        // Commit panel (always at bottom)
        const _CommitPanel(),
      ],
    );
  }

  Widget _buildLandscapeLayout() {
    return Row(
      children: [
        // File tree sidebar (persistent in landscape)
        SizedBox(
          width: 250.w,
          child: Container(
            decoration: BoxDecoration(
              border: Border(right: BorderSide(color: AppColors.border)),
            ),
            child: Column(
              children: [
                _buildFileTreeHeader(),
                const Expanded(child: _FileTreePanel(isCollapsible: false)),
              ],
            ),
          ),
        ),
        // Code editor and commit panel
        Expanded(
          child: Column(
            children: [
              const Expanded(child: _CodeEditorPanel()),
              const _CommitPanel(),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildFileTreeHeader() {
    final controller = Get.find<FileTreeController>();

    return Container(
      padding: EdgeInsets.symmetric(horizontal: 16.w, vertical: 12.h),
      decoration: BoxDecoration(
        color: Get.theme.cardTheme.color,
        border: Border(bottom: BorderSide(color: Get.theme.dividerColor)),
      ),
      child: Row(
        children: [
          Icon(Icons.folder_outlined,
              size: 20.r, color: Get.textTheme.bodyMedium?.color),
          SizedBox(width: 8.w),
          Text(
            'Files',
            style: GoogleFonts.inter(
              fontSize: 14.sp,
              fontWeight: FontWeight.w600,
              color: Get.textTheme.bodyLarge?.color,
            ),
          ),
          const Spacer(),
          Obx(() => controller.isLoading.value
              ? SizedBox(
                  width: 16.r,
                  height: 16.r,
                  child: const CircularProgressIndicator(strokeWidth: 2),
                )
              : IconButton(
                  icon: Icon(Icons.refresh, size: 20.r),
                  onPressed: controller.refreshFileTree,
                  padding: EdgeInsets.zero,
                  constraints: const BoxConstraints(),
                  color: Get.textTheme.bodyMedium?.color,
                )),
          SizedBox(width: 8.w),
          PopupMenuButton<String>(
            icon: Icon(Icons.more_vert,
                size: 20.r, color: Get.textTheme.bodyMedium?.color),
            itemBuilder: (context) => [
              const PopupMenuItem(value: 'expand', child: Text('Expand All')),
              const PopupMenuItem(
                  value: 'collapse', child: Text('Collapse All')),
            ],
            onSelected: (value) {
              switch (value) {
                case 'expand':
                  controller.expandAll();
                  break;
                case 'collapse':
                  controller.collapseAll();
                  break;
              }
            },
          ),
        ],
      ),
    );
  }
}

/// Collapsible file tree panel
class _FileTreePanel extends StatelessWidget {
  final bool isCollapsible;

  const _FileTreePanel({this.isCollapsible = true});

  @override
  Widget build(BuildContext context) {
    final controller = Get.find<FileTreeController>();

    return Obx(() {
      if (controller.isLoading.value) {
        return SizedBox(
          height: isCollapsible ? 150.h : null,
          child: const Center(child: CircularProgressIndicator()),
        );
      }

      if (controller.fileTree.isEmpty) {
        return SizedBox(
          height: isCollapsible ? 100.h : null,
          child: Center(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(Icons.folder_open,
                    size: 40.r, color: Get.textTheme.bodyMedium?.color),
                SizedBox(height: 8.h),
                Text(
                  'No files found',
                  style: GoogleFonts.inter(
                    fontSize: 13.sp,
                    color: AppColors.textSecondary,
                  ),
                ),
              ],
            ),
          ),
        );
      }

      final tree = controller.filteredTree;

      if (isCollapsible) {
        return SizedBox(
          height: 200.h,
          child: ListView(
            padding: EdgeInsets.symmetric(vertical: 8.h),
            children: tree
                .map((node) => _FileTreeNode(node: node, depth: 0))
                .toList(),
          ),
        );
      }

      return ListView(
        padding: EdgeInsets.symmetric(vertical: 8.h),
        children:
            tree.map((node) => _FileTreeNode(node: node, depth: 0)).toList(),
      );
    });
  }
}

/// Individual file tree node
class _FileTreeNode extends StatelessWidget {
  final FileNode node;
  final int depth;

  const _FileTreeNode({required this.node, required this.depth});

  @override
  Widget build(BuildContext context) {
    final controller = Get.find<FileTreeController>();

    return Obx(() {
      final isSelected = controller.selectedFile.value?.path == node.path;

      return Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          InkWell(
            onTap: () => controller.selectFile(node),
            child: Container(
              padding: EdgeInsets.symmetric(
                horizontal: (16 + depth * 16).w,
                vertical: 8.h,
              ),
              color: isSelected
                  ? AppColors.primary.withOpacity(0.1)
                  : Colors.transparent,
              child: Row(
                children: [
                  if (node.isDirectory)
                    Icon(
                      node.isExpanded.value
                          ? Icons.keyboard_arrow_down
                          : Icons.keyboard_arrow_right,
                      size: 16.r,
                      color: Get.textTheme.bodyMedium?.color,
                    ),
                  if (node.isFile) SizedBox(width: 16.w),
                  Text(
                    node.icon,
                    style: TextStyle(fontSize: 14.sp),
                  ),
                  SizedBox(width: 8.w),
                  Expanded(
                    child: Text(
                      node.name,
                      style: GoogleFonts.inter(
                        fontSize: 12.sp,
                        fontWeight:
                            isSelected ? FontWeight.w600 : FontWeight.w400,
                        color: node.modified
                            ? AppColors.warning
                            : Get.textTheme.bodyMedium?.color,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  if (node.modified)
                    Container(
                      width: 6.r,
                      height: 6.r,
                      decoration: BoxDecoration(
                        color: AppColors.warning,
                        shape: BoxShape.circle,
                      ),
                    ),
                ],
              ),
            ),
          ),
          if (node.isDirectory && node.isExpanded.value)
            ...node.children
                .map((child) => _FileTreeNode(node: child, depth: depth + 1)),
        ],
      );
    });
  }
}

/// Code editor panel with toolbar
class _CodeEditorPanel extends StatelessWidget {
  const _CodeEditorPanel();

  @override
  Widget build(BuildContext context) {
    final controller = Get.find<CodeEditorController>();

    return Obx(() {
      if (controller.currentFile.value == null) {
        return Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.code, size: 64.r, color: AppColors.textSecondary),
              SizedBox(height: 16.h),
              Text(
                'Select a file to edit',
                style: GoogleFonts.inter(
                  fontSize: 16.sp,
                  color: AppColors.textSecondary,
                ),
              ),
            ],
          ),
        );
      }

      if (controller.isLoading.value) {
        return const Center(child: CircularProgressIndicator());
      }

      return Container(
        decoration: BoxDecoration(
          border: Border.all(color: Get.theme.dividerColor),
        ),
        child: Column(
          children: [
            _buildEditorToolbar(controller),
            Expanded(
              child: CodeTheme(
                data: CodeThemeData(styles: vs2015Theme),
                child: SingleChildScrollView(
                  child: CodeField(
                    controller: controller.codeController,
                    // background: Colors.grey.shade900,
                    // wrap: true,
                    // gutterStyle: GutterStyle(
                    //   background: Colors.red,
                    // ),
                    // decoration: BoxDecoration(
                    //   color: Colors.grey.shade900,
                    //   borderRadius: BorderRadius.only(
                    //     bottomLeft: Radius.circular(0.r),
                    //     bottomRight: Radius.circular(0.r),
                    //   ),
                    // ),
                    textStyle: GoogleFonts.jetBrainsMono(
                      fontSize: 12.sp,
                    ),
                  ),
                ),
              ),
            ),
          ],
        ),
      );
    });
  }

  Widget _buildEditorToolbar(CodeEditorController controller) {
    return Container(
      padding: EdgeInsets.symmetric(horizontal: 12.w, vertical: 8.h),
      decoration: BoxDecoration(
        color: Get.theme.cardTheme.color,
        border: Border(bottom: BorderSide(color: Get.theme.dividerColor)),
      ),
      child: Row(
        children: [
          Icon(Icons.description, size: 16.r, color: Get.textTheme.bodyMedium?.color),
          SizedBox(width: 8.w),
          Expanded(
            child: Obx(() => Text(
                  controller.currentFile.value?.path ?? '',
                  style: GoogleFonts.jetBrainsMono(
                    fontSize: 11.sp,
                    color: AppColors.textSecondary,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                )),
          ),
          Obx(() => controller.hasUnsavedChanges.value
              ? Container(
                  padding: EdgeInsets.symmetric(horizontal: 8.w, vertical: 4.h),
                  decoration: BoxDecoration(
                    color: AppColors.warning,
                    borderRadius: BorderRadius.circular(4.r),
                  ),
                  child: Text(
                    'Modified',
                    style: GoogleFonts.inter(
                      fontSize: 10.sp,
                      color: Colors.white,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                )
              : const SizedBox.shrink()),
          SizedBox(width: 8.w),
          Obx(() => ElevatedButton.icon(
                onPressed: controller.hasUnsavedChanges.value &&
                        !controller.isSaving.value
                    ? controller.saveFile
                    : null,
                icon: controller.isSaving.value
                    ? SizedBox(
                        width: 14.r,
                        height: 14.r,
                        child: const CircularProgressIndicator(
                          strokeWidth: 2,
                          valueColor: AlwaysStoppedAnimation(Colors.white),
                        ),
                      )
                    : Icon(Icons.save, size: 16.r),
                label: Text(
                  controller.isSaving.value ? 'Saving...' : 'Save',
                  style: GoogleFonts.inter(fontSize: 12.sp),
                ),
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppColors.primary,
                  foregroundColor: Colors.white,
                  padding:
                      EdgeInsets.symmetric(horizontal: 12.w, vertical: 8.h),
                  minimumSize: Size.zero,
                ),
              )),
        ],
      ),
    );
  }
}

/// Commit panel at the bottom
class _CommitPanel extends StatelessWidget {
  const _CommitPanel();

  @override
  Widget build(BuildContext context) {
    final controller = Get.find<CommitPanelController>();

    return Obx(() {
      final isExpanded = controller.isExpanded.value;

      return Container(
        decoration: BoxDecoration(
          color: Get.theme.cardTheme.color,
          border: Border(top: BorderSide(color: Get.theme.dividerColor)),
        ),
        child: Column(
          children: [
            // Header
            InkWell(
              onTap: () => controller.isExpanded.toggle(),
              child: Container(
                padding: EdgeInsets.symmetric(horizontal: 16.w, vertical: 12.h),
                child: Row(
                  children: [
                    Icon(Icons.commit, size: 20.r, color: AppColors.primary),
                    SizedBox(width: 8.w),
                    Text(
                      'Commit Changes',
                      style: GoogleFonts.inter(
                        fontSize: 14.sp,
                        fontWeight: FontWeight.w600,
                        color: Get.textTheme.titleSmall?.color,
                      ),
                    ),
                    Obx(() => controller.modifiedFiles.isNotEmpty
                        ? Container(
                            margin: EdgeInsets.only(left: 8.w),
                            padding: EdgeInsets.symmetric(
                                horizontal: 8.w, vertical: 2.h),
                            decoration: BoxDecoration(
                              color: AppColors.warning,
                              borderRadius: BorderRadius.circular(12.r),
                            ),
                            child: Text(
                              '${controller.modifiedFiles.length}',
                              style: GoogleFonts.inter(
                                fontSize: 10.sp,
                                fontWeight: FontWeight.w600,
                                color: Colors.white,
                              ),
                            ),
                          )
                        : const SizedBox.shrink()),
                    const Spacer(),
                    Icon(
                      isExpanded
                          ? Icons.keyboard_arrow_down
                          : Icons.keyboard_arrow_up,
                      size: 20.r,
                      color: Get.textTheme.bodyMedium?.color,
                    ),
                  ],
                ),
              ),
            ),
            // Expanded content
            if (isExpanded) _buildCommitContent(controller),
          ],
        ),
      );
    });
  }

  Widget _buildCommitContent(CommitPanelController controller) {
    return Container(
      padding: EdgeInsets.all(16.r),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Branch info
          Row(
            children: [
              Text(
                'Branch:',
                style: GoogleFonts.inter(
                  fontSize: 13.sp,
                  fontWeight: FontWeight.w600,
                  color: Get.textTheme.titleSmall?.color,
                ),
              ),
              SizedBox(width: 8.w),
              Obx(() => Text(
                    controller.currentBranch.value,
                    style: GoogleFonts.jetBrainsMono(
                      fontSize: 12.sp,
                      color: AppColors.primary,
                    ),
                  )),
            ],
          ),
          SizedBox(height: 16.h),

          // Commit message
          Text(
            'Commit Message',
            style: GoogleFonts.inter(
              fontSize: 13.sp,
              fontWeight: FontWeight.w600,
              color: AppColors.textPrimary,
            ),
          ),
          SizedBox(height: 8.h),
          TextField(
            controller: controller.messageController,
            decoration: InputDecoration(
              hintText: 'e.g., feat: add login validation',
              hintStyle: GoogleFonts.inter(
                  fontSize: 12.sp, color: Get.textTheme.bodyMedium?.color),
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(8.r),
              ),
              contentPadding:
                  EdgeInsets.symmetric(horizontal: 12.w, vertical: 10.h),
            ),
            style: GoogleFonts.inter(fontSize: 13.sp),
            maxLines: 2,
            onChanged: (value) => controller.commitMessage.value = value,
          ),
          SizedBox(height: 16.h),

          // Actions
          Row(
            children: [
              Expanded(
                child: OutlinedButton(
                  onPressed: () => controller.isExpanded.value = false,
                  style: OutlinedButton.styleFrom(
                    padding: EdgeInsets.symmetric(vertical: 12.h),
                  ),
                  child: Text(
                    'Cancel',
                    style: GoogleFonts.inter(fontSize: 13.sp),
                  ),
                ),
              ),
              SizedBox(width: 12.w),
              Expanded(
                flex: 2,
                child: Obx(() => ElevatedButton.icon(
                      onPressed: controller.isCommitting.value
                          ? null
                          : controller.commit,
                      icon: controller.isCommitting.value
                          ? SizedBox(
                              width: 16.r,
                              height: 16.r,
                              child: const CircularProgressIndicator(
                                strokeWidth: 2,
                                valueColor:
                                    AlwaysStoppedAnimation(Colors.white),
                              ),
                            )
                          : Icon(Icons.check, size: 18.r),
                      label: Text(
                        controller.isCommitting.value
                            ? 'Committing...'
                            : 'Commit & Push',
                        style: GoogleFonts.inter(fontSize: 13.sp),
                      ),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: AppColors.success,
                        foregroundColor: Colors.white,
                        padding: EdgeInsets.symmetric(vertical: 12.h),
                      ),
                    )),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
