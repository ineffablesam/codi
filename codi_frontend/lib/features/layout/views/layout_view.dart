import 'package:animations/animations.dart';
import 'package:codi_frontend/features/auth/controllers/auth_controller.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:get/get.dart';
import 'package:iconsax_flutter/iconsax_flutter.dart';
import 'package:lucky_navigation_bar/lucky_navigation_bar.dart';

import '../../../config/routes.dart';
import '../../../core/constants/image_placeholders.dart';
import '../../projects/views/projects_list_screen.dart';
import '../../settings/views/settings_screen.dart';
import '../controllers/layout_controller.dart';

class LayoutView extends GetView<LayoutController> {
  const LayoutView({super.key});

  @override
  Widget build(BuildContext context) {
    if (!Get.isRegistered<LayoutController>()) {
      Get.put(LayoutController());
    }

    return Obx(() {
      if (controller.isLoading.value) {
        return Scaffold(
          backgroundColor: Get.theme.scaffoldBackgroundColor,
          body: const Center(
            child: CircularProgressIndicator(
              strokeWidth: 2,
            ),
          ),
        );
      }

      final pages = <Widget>[
        const ProjectsListScreen(key: ValueKey('projects')),
        const _PlaceholderPage(
            title: 'Store', icon: Iconsax.shop, key: ValueKey('store')),
        const _PlaceholderPage(
            title: 'Activity',
            icon: Iconsax.notification,
            key: ValueKey('activity')),
        const SettingsScreen(key: ValueKey('account')),
      ];

      return Scaffold(
        backgroundColor: Get.theme.scaffoldBackgroundColor,
        body: PageTransitionSwitcher(
          duration: const Duration(milliseconds: 350),
          reverse: controller.currentIndex < controller.previousPageIndex,
          transitionBuilder: (child, animation, secondaryAnimation) {
            return SharedAxisTransition(
              fillColor: Colors.transparent,
              animation: animation,
              secondaryAnimation: secondaryAnimation,
              transitionType: SharedAxisTransitionType.horizontal,
              child: child,
            );
          },
          child: pages[controller.currentIndex],
        ),
        bottomNavigationBar: Theme(
          data: Get.theme.copyWith(
            colorScheme: Get.theme.colorScheme.copyWith(
              surfaceContainer: Get.theme.cardTheme.color,
              surface: Get.theme.scaffoldBackgroundColor,
              outlineVariant: Get.theme.dividerColor,
            ),
            splashColor: Colors.transparent,
            highlightColor: Colors.transparent,
          ),
          child: LuckyNavigationBar(
            selectedIndex: controller.currentIndex,
            onDestinationSelected: (index) {
              if (index >= 0 && index < pages.length) {
                HapticFeedback.lightImpact();
                controller.updatePageIndex(index);
              }
            },
            destinations: [
              NavigationDestination(
                icon: Icon(
                    controller.currentIndex == 0
                        ? Iconsax.folder_2
                        : Iconsax.folder_2_copy,
                    size: 24.r),
                selectedIcon: Icon(Iconsax.folder_2,
                    size: 24.r, color: Get.theme.primaryColor),
                label: 'Projects',
              ),
              NavigationDestination(
                icon: Icon(
                    controller.currentIndex == 1
                        ? Iconsax.shop
                        : Iconsax.shop_copy,
                    size: 24.r),
                selectedIcon: Icon(Iconsax.shop,
                    size: 24.r, color: Get.theme.primaryColor),
                label: 'Store',
              ),
              NavigationDestination(
                icon: Icon(
                    controller.currentIndex == 2
                        ? Iconsax.notification
                        : Iconsax.notification_copy,
                    size: 24.r),
                selectedIcon: Icon(Iconsax.notification,
                    size: 24.r, color: Get.theme.primaryColor),
                label: 'Activity',
              ),
              NavigationDestination(
                icon: Obx(() {
                  final authController = Get.find<AuthController>();
                  final user = authController.currentUser.value;
                  return CircleAvatar(
                    radius: 14.r,
                    child: CircleAvatar(
                      radius: 12.r,
                      backgroundImage: NetworkImage(
                        ImagePlaceholders.userAvatarWithFallback(
                          user?.githubAvatarUrl,
                          user?.githubUsername,
                        ),
                      ),
                    ),
                  );
                }),
                selectedIcon: Icon(Iconsax.user,
                    size: 24.r, color: Get.theme.primaryColor),
                label: 'Account',
              ),
            ],
            trailing: FloatingActionButton(
              onPressed: () {
                HapticFeedback.mediumImpact();
                Get.toNamed(AppRoutes.createProject);
              },
              elevation: 1,
              highlightElevation: 1,
              backgroundColor: Get.theme.primaryColor,
              shape: const CircleBorder(),
              child: Icon(Iconsax.add, size: 28.r, color: Colors.white),
            ),
          ),
        ),
      );
    });
  }
}

class _PlaceholderPage extends StatelessWidget {
  final String title;
  final IconData icon;

  const _PlaceholderPage({required this.title, required this.icon, super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Get.theme.scaffoldBackgroundColor,
      appBar: AppBar(
        title: Text(
          title,
          style: const TextStyle(fontWeight: FontWeight.w600),
        ),
        backgroundColor: Colors.transparent,
        elevation: 0,
      ),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon,
                size: 64.r, color: Get.theme.primaryColor.withOpacity(0.5)),
            SizedBox(height: 16.h),
            Text(
              '$title coming soon',
              style: TextStyle(
                fontSize: 18.sp,
                fontWeight: FontWeight.w500,
                color: Get.textTheme.bodyLarge?.color,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
