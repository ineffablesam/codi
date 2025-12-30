/// Create project dialog widget
library;

import 'package:flutter/material.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:get/get.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../../core/constants/app_colors.dart';
import '../../../core/constants/app_strings.dart';
import '../../../core/utils/validators.dart';
import '../controllers/projects_controller.dart';

/// Dialog for creating a new project
class CreateProjectDialog extends StatefulWidget {
  const CreateProjectDialog({super.key});

  @override
  State<CreateProjectDialog> createState() => _CreateProjectDialogState();
}

class _CreateProjectDialogState extends State<CreateProjectDialog> {
  final _formKey = GlobalKey<FormState>();
  final _nameController = TextEditingController();

  @override
  void dispose() {
    _nameController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final controller = Get.find<ProjectsController>();

    return AlertDialog(
      title: Text(
        AppStrings.newProject,
        style: GoogleFonts.inter(fontWeight: FontWeight.w600),
      ),
      content: Form(
        key: _formKey,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextFormField(
              controller: _nameController,
              decoration: InputDecoration(
                labelText: AppStrings.projectName,
                hintText: AppStrings.projectNameHint,
              ),
              validator: Validators.projectName,
              autofocus: true,
            ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Get.back(),
          child: Text(AppStrings.cancel),
        ),
        Obx(() => ElevatedButton(
              onPressed: controller.isCreating.value ? null : _create,
              child: controller.isCreating.value
                  ? SizedBox(
                      width: 16.r,
                      height: 16.r,
                      child: const CircularProgressIndicator(strokeWidth: 2),
                    )
                  : Text(AppStrings.createProject),
            )),
      ],
    );
  }

  void _create() async {
    if (_formKey.currentState?.validate() ?? false) {
      final controller = Get.find<ProjectsController>();
      final success = await controller.createProject(
        name: _nameController.text.trim(),
      );
      if (success) {
        Get.back();
      }
    }
  }
}
