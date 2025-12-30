/// Create project screen
library;

import 'package:flutter/material.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:get/get.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../../core/constants/app_colors.dart';
import '../../../core/constants/app_strings.dart';
import '../../../core/utils/validators.dart';
import '../controllers/projects_controller.dart';

/// Screen for creating a new project
class CreateProjectScreen extends StatefulWidget {
  const CreateProjectScreen({super.key});

  @override
  State<CreateProjectScreen> createState() => _CreateProjectScreenState();
}

class _CreateProjectScreenState extends State<CreateProjectScreen> {
  final _formKey = GlobalKey<FormState>();
  final _nameController = TextEditingController();
  final _descriptionController = TextEditingController();
  bool _isPrivate = false;

  @override
  void dispose() {
    _nameController.dispose();
    _descriptionController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final controller = Get.find<ProjectsController>();

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: Text(
          AppStrings.createProject,
          style: GoogleFonts.inter(fontWeight: FontWeight.w600),
        ),
      ),
      body: SafeArea(
        child: Form(
          key: _formKey,
          child: ListView(
            padding: EdgeInsets.all(16.r),
            children: [
              // Project name
              Text(
                AppStrings.projectName,
                style: GoogleFonts.inter(
                  fontSize: 14.sp,
                  fontWeight: FontWeight.w600,
                  color: AppColors.textPrimary,
                ),
              ),
              SizedBox(height: 8.h),
              TextFormField(
                controller: _nameController,
                decoration: InputDecoration(
                  hintText: AppStrings.projectNameHint,
                ),
                validator: Validators.projectName,
                textInputAction: TextInputAction.next,
                autofocus: true,
              ),
              SizedBox(height: 24.h),

              // Description
              Text(
                AppStrings.projectDescription,
                style: GoogleFonts.inter(
                  fontSize: 14.sp,
                  fontWeight: FontWeight.w600,
                  color: AppColors.textPrimary,
                ),
              ),
              SizedBox(height: 8.h),
              TextFormField(
                controller: _descriptionController,
                decoration: InputDecoration(
                  hintText: AppStrings.projectDescriptionHint,
                ),
                maxLines: 3,
                textInputAction: TextInputAction.done,
              ),
              SizedBox(height: 24.h),

              // Private toggle
              Container(
                padding: EdgeInsets.all(16.r),
                decoration: BoxDecoration(
                  color: AppColors.surface,
                  borderRadius: BorderRadius.circular(12.r),
                  border: Border.all(color: AppColors.border),
                ),
                child: Row(
                  children: [
                    Icon(
                      _isPrivate ? Icons.lock : Icons.lock_open,
                      size: 24.r,
                      color: AppColors.textSecondary,
                    ),
                    SizedBox(width: 12.w),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            AppStrings.privateProject,
                            style: GoogleFonts.inter(
                              fontSize: 14.sp,
                              fontWeight: FontWeight.w600,
                              color: AppColors.textPrimary,
                            ),
                          ),
                          SizedBox(height: 2.h),
                          Text(
                            'Only you can see this repository',
                            style: GoogleFonts.inter(
                              fontSize: 12.sp,
                              color: AppColors.textSecondary,
                            ),
                          ),
                        ],
                      ),
                    ),
                    Switch(
                      value: _isPrivate,
                      onChanged: (value) => setState(() => _isPrivate = value),
                      activeColor: AppColors.primary,
                    ),
                  ],
                ),
              ),
              SizedBox(height: 32.h),

              // Info card
              Container(
                padding: EdgeInsets.all(16.r),
                decoration: BoxDecoration(
                  color: AppColors.info.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(12.r),
                  border: Border.all(color: AppColors.info.withOpacity(0.3)),
                ),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Icon(
                      Icons.info_outline,
                      size: 20.r,
                      color: AppColors.info,
                    ),
                    SizedBox(width: 12.w),
                    Expanded(
                      child: Text(
                        'A new GitHub repository will be created with a Flutter starter template. You can start building immediately!',
                        style: GoogleFonts.inter(
                          fontSize: 13.sp,
                          color: AppColors.textPrimary,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              SizedBox(height: 32.h),

              // Create button
              Obx(() => ElevatedButton(
                    onPressed: controller.isCreating.value
                        ? null
                        : _createProject,
                    child: controller.isCreating.value
                        ? SizedBox(
                            width: 24.r,
                            height: 24.r,
                            child: const CircularProgressIndicator(
                              strokeWidth: 2,
                              valueColor:
                                  AlwaysStoppedAnimation<Color>(Colors.white),
                            ),
                          )
                        : Text(AppStrings.createProject),
                  )),
            ],
          ),
        ),
      ),
    );
  }

  void _createProject() async {
    if (_formKey.currentState?.validate() ?? false) {
      final controller = Get.find<ProjectsController>();
      await controller.createProject(
        name: _nameController.text.trim(),
        description: _descriptionController.text.trim().isEmpty
            ? null
            : _descriptionController.text.trim(),
        isPrivate: _isPrivate,
      );
    }
  }
}
