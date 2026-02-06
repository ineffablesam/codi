/// Deployments screen
library;

import 'package:flutter/material.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:get/get.dart';

import '../../../core/constants/app_colors.dart';
import '../../../core/constants/app_strings.dart';
import '../../../core/constants/image_placeholders.dart';
import '../../../core/utils/sf_font.dart';
import '../controllers/deployments_controller.dart';
import '../widgets/deployment_card.dart';

/// Deployments history screen
class DeploymentsScreen extends StatelessWidget {
  const DeploymentsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final controller = Get.find<DeploymentsController>();
    final projectId = int.tryParse(Get.parameters['projectId'] ?? '');

    if (projectId != null) {
      controller.loadDeployments(projectId);
    }

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: Text(
          AppStrings.deployments,
          style: SFPro.font(fontWeight: FontWeight.w600),
        ),
      ),
      body: RefreshIndicator(
        onRefresh: controller.refresh,
        child: Obx(() {
          if (controller.isLoading.value && controller.deployments.isEmpty) {
            return const Center(child: CircularProgressIndicator());
          }

          if (controller.deployments.isEmpty) {
            return _buildEmptyState();
          }

          return ListView.builder(
            padding: EdgeInsets.all(16.r),
            itemCount: controller.deployments.length,
            itemBuilder: (context, index) {
              return Padding(
                padding: EdgeInsets.only(bottom: 12.h),
                child:
                    DeploymentCard(deployment: controller.deployments[index]),
              );
            },
          );
        }),
      ),
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Padding(
        padding: EdgeInsets.all(32.r),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Image.network(
              ImagePlaceholders.emptyState,
              width: 160.w,
              height: 120.h,
              errorBuilder: (_, __, ___) => Icon(
                Icons.rocket_launch,
                size: 64.r,
                color: AppColors.textTertiary,
              ),
            ),
            SizedBox(height: 24.h),
            Text(
              AppStrings.noDeployments,
              style: SFPro.font(
                fontSize: 18.sp,
                fontWeight: FontWeight.w600,
                color: AppColors.textPrimary,
              ),
            ),
            SizedBox(height: 8.h),
            Text(
              AppStrings.noDeploymentsSubtitle,
              style: SFPro.font(
                fontSize: 14.sp,
                color: AppColors.textSecondary,
              ),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }
}
