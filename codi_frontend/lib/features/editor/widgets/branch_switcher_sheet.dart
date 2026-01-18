import 'package:flutter/material.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:get/get.dart';
import 'package:iconsax_flutter/iconsax_flutter.dart';

import '../../../core/constants/app_colors.dart';
import '../controllers/branch_controller.dart';

/// Bottom sheet for switching Git branches
class BranchSwitcherSheet extends StatefulWidget {
  final Function(String branch, {bool createPreview})? onBranchSelected;

  const BranchSwitcherSheet({
    super.key,
    this.onBranchSelected,
  });

  static Future<void> show(BuildContext context,
      {Function(String branch, {bool createPreview})? onBranchSelected}) {
    return showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => BranchSwitcherSheet(onBranchSelected: onBranchSelected),
    );
  }

  @override
  State<BranchSwitcherSheet> createState() => _BranchSwitcherSheetState();
}

class _BranchSwitcherSheetState extends State<BranchSwitcherSheet> {
  late final BranchController _controller;
  final TextEditingController _newBranchController = TextEditingController();
  bool _showCreateBranch = false;

  @override
  void initState() {
    super.initState();
    if (!Get.isRegistered<BranchController>()) {
      Get.put(BranchController());
    }
    _controller = Get.find<BranchController>();
    _controller.loadBranches();
  }

  @override
  void dispose() {
    _newBranchController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      height: MediaQuery.of(context).size.height * 0.8,
      constraints: BoxConstraints(maxHeight: 500.h),
      decoration: BoxDecoration(
        color: Get.theme.cardTheme.color,
        borderRadius: BorderRadius.vertical(top: Radius.circular(20.r)),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // Handle bar
          Container(
            margin: EdgeInsets.only(top: 12.h),
            width: 40.w,
            height: 4.h,
            decoration: BoxDecoration(
              color: Get.textTheme.bodyMedium!.color!.withOpacity(0.3),
              borderRadius: BorderRadius.circular(2.r),
            ),
          ),

          // Header
          Padding(
            padding: EdgeInsets.all(16.w),
            child: Row(
              children: [
                Icon(Iconsax.code_circle,
                    color: AppColors.primary, size: 24.sp),
                SizedBox(width: 12.w),
                Text(
                  'Git Branches',
                  style: TextStyle(
                    fontSize: 18.sp,
                    fontWeight: FontWeight.w600,
                    color: Get.textTheme.titleLarge?.color,
                  ),
                ),
                const Spacer(),
                // Create branch button
                IconButton(
                  onPressed: () {
                    setState(() => _showCreateBranch = !_showCreateBranch);
                  },
                  icon: Icon(
                    _showCreateBranch ? Icons.close : Iconsax.add,
                    color: AppColors.primary,
                  ),
                ),
              ],
            ),
          ),

          // Create branch form
          if (_showCreateBranch) _buildCreateBranchForm(),

          // Branch list
          Expanded(
            child: Obx(() {
              if (_controller.isLoading.value) {
                return const Center(child: CircularProgressIndicator());
              }

              if (_controller.branches.isEmpty) {
                return Center(
                  child: Text(
                    'No branches found',
                    style: TextStyle(
                      color: Get.textTheme.bodyMedium?.color,
                      fontSize: 14.sp,
                    ),
                  ),
                );
              }

              return ListView.builder(
                padding: EdgeInsets.symmetric(horizontal: 8.w),
                itemCount: _controller.branches.length,
                itemBuilder: (context, index) {
                  final branch = _controller.branches[index];
                  final isCurrent = branch == _controller.currentBranch.value;

                  return _buildBranchTile(branch, isCurrent);
                },
              );
            }),
          ),

          SizedBox(height: MediaQuery.of(context).padding.bottom + 16.h),
        ],
      ),
    );
  }

  Widget _buildCreateBranchForm() {
    return Padding(
      padding: EdgeInsets.symmetric(horizontal: 16.w, vertical: 8.h),
      child: Row(
        children: [
          Expanded(
            child: TextField(
              controller: _newBranchController,
              decoration: InputDecoration(
                hintText: 'New branch name...',
                hintStyle: TextStyle(color: Get.textTheme.bodyMedium?.color),
                filled: true,
                fillColor: Get.theme.inputDecorationTheme.fillColor ?? Get.theme.scaffoldBackgroundColor,
                contentPadding: EdgeInsets.symmetric(
                  horizontal: 16.w,
                  vertical: 12.h,
                ),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12.r),
                  borderSide: BorderSide.none,
                ),
              ),
              style: TextStyle(color: Get.textTheme.bodyLarge?.color),
            ),
          ),
          SizedBox(width: 12.w),
          Obx(() => ElevatedButton(
                onPressed: _controller.isLoading.value
                    ? null
                    : () async {
                        final name = _newBranchController.text.trim();
                        if (name.isNotEmpty) {
                          final success = await _controller.createBranch(name);
                          if (success) {
                            _newBranchController.clear();
                            setState(() => _showCreateBranch = false);
                          }
                        }
                      },
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppColors.primary,
                  padding:
                      EdgeInsets.symmetric(horizontal: 20.w, vertical: 14.h),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12.r),
                  ),
                ),
                child: Text(
                  'Create',
                  style: TextStyle(color: Colors.white, fontSize: 14.sp),
                ),
              )),
        ],
      ),
    );
  }

  Widget _buildBranchTile(String branch, bool isCurrent) {
    return Container(
      margin: EdgeInsets.symmetric(vertical: 4.h),
      decoration: BoxDecoration(
        color: isCurrent
            ? AppColors.primary.withOpacity(0.1)
            : Get.theme.canvasColor,
        borderRadius: BorderRadius.circular(12.r),
        border: isCurrent
            ? Border.all(color: AppColors.primary.withOpacity(0.3))
            : null,
      ),
      child: ListTile(
        leading: Icon(
          isCurrent ? Iconsax.tick_circle : Iconsax.code_circle,
          color: isCurrent ? AppColors.primary : Get.textTheme.bodyMedium?.color,
        ),
        title: Text(
          branch,
          style: TextStyle(
            color: Get.textTheme.bodyLarge?.color,
            fontWeight: isCurrent ? FontWeight.w600 : FontWeight.normal,
          ),
        ),
        trailing: PopupMenuButton<String>(
          icon: Icon(Iconsax.more, color: Get.textTheme.bodyMedium?.color),
          color: Get.theme.cardTheme.color,
          itemBuilder: (context) => [
            if (!isCurrent)
              PopupMenuItem(
                value: 'switch',
                child: Row(
                  children: [
                    Icon(Iconsax.arrow_swap_horizontal,
                        size: 18.sp, color: Get.textTheme.bodyLarge?.color),
                    SizedBox(width: 8.w),
                    Text('Switch to branch',
                        style: TextStyle(color: Get.textTheme.bodyLarge?.color)),
                  ],
                ),
              ),
            PopupMenuItem(
              value: 'preview',
              child: Row(
                children: [
                  Icon(Iconsax.eye, size: 18.sp, color: AppColors.primary),
                  SizedBox(width: 8.w),
                  Text('Create Preview',
                      style: TextStyle(color: Get.textTheme.bodyLarge?.color)),
                ],
              ),
            ),
          ],
          onSelected: (value) async {
            if (value == 'switch') {
              final success = await _controller.switchBranch(branch);
              if (success && mounted) {
                widget.onBranchSelected?.call(branch, createPreview: false);
                Navigator.pop(context);
              }
            } else if (value == 'preview') {
              widget.onBranchSelected?.call(branch, createPreview: true);
              Navigator.pop(context);
            }
          },
        ),
        onTap: isCurrent
            ? null
            : () async {
                final success = await _controller.switchBranch(branch);
                if (success && mounted) {
                  widget.onBranchSelected?.call(branch, createPreview: false);
                  Navigator.pop(context);
                }
              },
      ),
    );
  }
}
