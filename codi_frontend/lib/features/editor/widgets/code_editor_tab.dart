/// Code editor tab widget with file tree, editor, and commit panel
library;

import 'package:flutter/material.dart';
import 'package:flutter_code_editor/flutter_code_editor.dart';
import 'package:flutter_highlight/themes/vs2015.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:get/get.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';
import 'package:resizable_splitter/resizable_splitter.dart';

import '../../../core/constants/app_colors.dart';
import '../../../core/utils/sf_font.dart';
import '../controllers/code_editor_controller.dart';
import '../controllers/commit_panel_controller.dart';
import '../controllers/file_tree_controller.dart';
import '../models/file_node.dart';

/// Main code editor tab with file tree, editor, and commit panel
class CodeEditorTab extends StatelessWidget {
  const CodeEditorTab({super.key});

  @override
  Widget build(BuildContext context) {
    return ResizableSplitter(
      axis: Axis.vertical,
      // minStartPanelSize: 120,
      // minEndPanelSize: 160,
      minRatio: 0.2,
      maxRatio: 0.8,
      dividerThickness: 8,
      startPanel: const _FileTreePanel(isCollapsible: false),
      endPanel: const _CodeEditorPanel(),
      // onRatioChanged: (ratio) => debugPrint('ratio: $ratio'),
    );
  }
}

class BuildFileTree extends StatelessWidget {
  const BuildFileTree({super.key});

  @override
  Widget build(BuildContext context) {
    final controller = Get.find<FileTreeController>();

    return Container(
      padding: EdgeInsets.symmetric(horizontal: 16.w, vertical: 12.h),
      decoration: BoxDecoration(
        color: Get.theme.cardTheme.color,
        border: Border(bottom: BorderSide(color: Get.theme.dividerColor)),
      ),
      child: Row(
        children: [
          Icon(LucideIcons.folder,
              size: 20.r, color: Get.textTheme.bodyMedium?.color),
          SizedBox(width: 8.w),
          Text(
            'Files',
            style: SFPro.font(
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
                  icon: Icon(LucideIcons.refreshCw, size: 20.r),
                  onPressed: controller.refreshFileTree,
                  padding: EdgeInsets.zero,
                  constraints: const BoxConstraints(),
                  color: Get.textTheme.bodyMedium?.color,
                )),
          SizedBox(width: 8.w),
          PopupMenuButton<String>(
            icon: Icon(LucideIcons.ellipsisVertical,
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

    return Column(
      children: [
        // Fixed header
        const BuildFileTree(),

        // Scrollable area that RESIZES correctly
        Expanded(
          child: Obx(() {
            if (controller.isLoading.value) {
              return const Center(child: CircularProgressIndicator());
            }

            if (controller.fileTree.isEmpty) {
              return Center(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(LucideIcons.folderOpen, size: 40),
                    const SizedBox(height: 8),
                    const Text('No files found'),
                  ],
                ),
              );
            }

            final tree = controller.filteredTree;

            return ListView(
              padding: EdgeInsets.symmetric(vertical: 8.h),
              children: tree
                  .map((node) => _FileTreeNode(node: node, depth: 0))
                  .toList(),
            );
          }),
        ),
      ],
    );
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
                  // expand / collapse arrow
                  SizedBox(
                    width: 20.w,
                    child: node.isDirectory
                        ? Icon(
                            node.isExpanded.value
                                ? LucideIcons.chevronDown
                                : LucideIcons.chevronRight,
                            size: 18.r,
                            color: Get.textTheme.bodyMedium?.color
                                ?.withOpacity(0.7),
                          )
                        : null,
                  ),

                  // file/folder icon with proper Material icons
                  SizedBox(
                    width: 24.w,
                    child: Icon(
                      _getFileIcon(node),
                      size: 16.r,
                      color: _getFileIconColor(node),
                    ),
                  ),

                  SizedBox(width: 8.w),

                  // ✅ THIS IS THE MOST IMPORTANT CHANGE
                  Expanded(
                    child: Text(
                      node.name,
                      style: SFPro.font(
                        fontSize: 12.sp,
                        fontWeight:
                            isSelected ? FontWeight.w600 : FontWeight.w400,
                        color: node.modified
                            ? AppColors.warning
                            : Get.textTheme.bodyMedium?.color,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      softWrap: false,
                    ),
                  ),

                  // modified dot
                  if (node.modified)
                    Container(
                      width: 6.r,
                      height: 6.r,
                      margin: EdgeInsets.only(left: 6.w),
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

  /// Get appropriate icon based on file type
  IconData _getFileIcon(FileNode node) {
    if (node.isDirectory) {
      return node.isExpanded.value
          ? LucideIcons.folderOpen
          : LucideIcons.folder;
    }

    final extension = node.name.split('.').last.toLowerCase();
    switch (extension) {
      case 'dart':
        return LucideIcons.code;
      case 'py':
        return LucideIcons.code;
      case 'js':
      case 'ts':
      case 'jsx':
      case 'tsx':
        return LucideIcons.fileCode;
      case 'html':
        return LucideIcons.fileCode;
      case 'css':
      case 'scss':
      case 'sass':
        return LucideIcons.palette;
      case 'json':
        return LucideIcons.braces;
      case 'yaml':
      case 'yml':
        return LucideIcons.settings;
      case 'md':
        return LucideIcons.fileText;
      case 'png':
      case 'jpg':
      case 'jpeg':
      case 'gif':
      case 'svg':
        return LucideIcons.image;
      case 'pdf':
        return LucideIcons.file;
      case 'zip':
      case 'tar':
      case 'gz':
        return LucideIcons.archive;
      case 'sh':
        return LucideIcons.terminal;
      case 'lock':
        return LucideIcons.lock;
      default:
        return LucideIcons.file;
    }
  }

  /// Get color for file icon based on type
  Color _getFileIconColor(FileNode node) {
    if (node.isDirectory) {
      return AppColors.primary;
    }

    final extension = node.name.split('.').last.toLowerCase();
    switch (extension) {
      case 'dart':
        return const Color(0xFF0175C2); // Dart blue
      case 'py':
        return const Color(0xFF3776AB); // Python blue
      case 'js':
      case 'ts':
      case 'jsx':
      case 'tsx':
        return const Color(0xFFF7DF1E); // JavaScript yellow
      case 'html':
        return const Color(0xFFE34C26); // HTML orange
      case 'css':
      case 'scss':
      case 'sass':
        return const Color(0xFF264DE4); // CSS blue
      case 'json':
        return const Color(0xFF00D084); // JSON green
      case 'yaml':
      case 'yml':
        return const Color(0xFFCB171E); // YAML red
      case 'md':
        return Get.textTheme.bodyMedium?.color ?? Colors.grey;
      case 'png':
      case 'jpg':
      case 'jpeg':
      case 'gif':
      case 'svg':
        return const Color(0xFF9C27B0); // Purple for images
      case 'sh':
        return const Color(0xFF4EAA25); // Green for shell
      default:
        return Get.textTheme.bodyMedium?.color?.withOpacity(0.6) ?? Colors.grey;
    }
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
              Icon(LucideIcons.code,
                  size: 64.r, color: AppColors.textSecondary),
              SizedBox(height: 16.h),
              Text(
                'Select a file to edit',
                style: SFPro.font(
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
          Icon(LucideIcons.file,
              size: 16.r, color: Get.textTheme.bodyMedium?.color),
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
                    style: SFPro.font(
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
                    : Icon(LucideIcons.save, size: 16.r),
                label: Text(
                  controller.isSaving.value ? 'Saving...' : 'Save',
                  style: SFPro.font(fontSize: 12.sp),
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
                    Icon(LucideIcons.gitCommitHorizontal,
                        size: 20.r, color: AppColors.primary),
                    SizedBox(width: 8.w),
                    Text(
                      'Commit Changes',
                      style: SFPro.font(
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
                              style: SFPro.font(
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
                          ? LucideIcons.chevronDown
                          : LucideIcons.chevronUp,
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
                style: SFPro.font(
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
            style: SFPro.font(
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
              hintStyle: SFPro.font(
                  fontSize: 12.sp, color: Get.textTheme.bodyMedium?.color),
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(8.r),
              ),
              contentPadding:
                  EdgeInsets.symmetric(horizontal: 12.w, vertical: 10.h),
            ),
            style: SFPro.font(fontSize: 13.sp),
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
                    style: SFPro.font(fontSize: 13.sp),
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
                          : Icon(LucideIcons.check, size: 18.r),
                      label: Text(
                        controller.isCommitting.value
                            ? 'Committing...'
                            : 'Commit & Push',
                        style: SFPro.font(fontSize: 13.sp),
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
