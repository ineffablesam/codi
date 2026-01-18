/// Onboarding form widget for new users
library;

import 'dart:ui';

import 'package:animate_do/animate_do.dart';
import 'package:animated_custom_dropdown/custom_dropdown.dart';
import 'package:flutter/material.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:get/get.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';

import '../../../core/utils/sf_font.dart';
import '../controllers/onboarding_controller.dart';
import 'selectable_option_button.dart';

/// Onboarding form widget with pre-populated fields and sticky Get Started button
class OnboardingFormWidget extends StatelessWidget {
  const OnboardingFormWidget({super.key});

  @override
  Widget build(BuildContext context) {
    // Initialize the onboarding controller
    final onboardingController = Get.put(OnboardingController());

    return Stack(
      children: [
        // Scrollable form content
        SingleChildScrollView(
          padding: EdgeInsets.only(bottom: 100.h), // Space for sticky button
          child: SafeArea(
            top: true,
            child: Padding(
              padding: EdgeInsets.symmetric(horizontal: 16.w, vertical: 24.h),
              child: SlideInUp(
                duration: const Duration(milliseconds: 600),
                curve: Curves.fastLinearToSlowEaseIn,
                from: 110,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    /// Title
                    Text(
                      "Let's get you started",
                      style: SFPro.font(
                        fontSize: 22.sp,
                        fontWeight: FontWeight.w700,
                        color: Colors.white,
                      ),
                    ),
                    8.verticalSpace,
                    Text(
                      'Tell us a bit about yourself so we can personalize your experience',
                      style: SFPro.font(
                        fontSize: 15,
                        fontWeight: FontWeight.w400,
                        color: Colors.white,
                      ),
                    ),
                    24.verticalSpace,

                    /// Name Field
                    _buildLabel('Your Name'),
                    8.verticalSpace,
                    _buildNameField(onboardingController),
                    20.verticalSpace,

                    /// What brings you to Codi
                    _buildLabel('What brings you to Codi?'),
                    8.verticalSpace,
                    _buildWhatBringsYouDropdown(onboardingController),
                    20.verticalSpace,

                    /// Have you coded before?
                    _buildLabel('Have you coded before?'),
                    4.verticalSpace,
                    Text(
                      'This helps us adjust how our AI assists you',
                      style: SFPro.font(
                        fontSize: 12.sp,
                        fontWeight: FontWeight.w400,
                        color: Colors.grey.shade300,
                      ),
                    ),
                    12.verticalSpace,
                    _buildCodingExperienceOptions(onboardingController),
                    40.verticalSpace,
                  ],
                ),
              ),
            ),
          ),
        ),

        // Sticky bottom Get Started button
        Positioned(
          left: 0,
          right: 0,
          bottom: 0,
          child: Obx(() {
            final isValid = onboardingController.isFormValid.value;
            final isSubmitting = onboardingController.isSubmitting.value;

            return AnimatedOpacity(
              duration: const Duration(milliseconds: 300),
              opacity: isValid ? 1.0 : 0.0,
              child: IgnorePointer(
                ignoring: !isValid,
                child: Container(
                  padding: EdgeInsets.all(16.w),
                  child: SafeArea(
                    top: false,
                    child: ElevatedButton(
                      onPressed: isSubmitting
                          ? null
                          : () => onboardingController.submitOnboarding(),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.white,
                        foregroundColor: Colors.black,
                        minimumSize: Size(double.infinity, 56.h),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(16.r),
                        ),
                        elevation: 0,
                      ),
                      child: isSubmitting
                          ? SizedBox(
                              width: 24.w,
                              height: 24.w,
                              child: const CircularProgressIndicator(
                                color: Colors.black,
                                strokeWidth: 2.5,
                              ),
                            )
                          : Row(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                Text(
                                  'Get Started',
                                  style: SFPro.font(
                                    fontSize: 16.sp,
                                    fontWeight: FontWeight.w600,
                                    color: Colors.black,
                                  ),
                                ),
                                SizedBox(width: 8.w),
                                Icon(
                                  LucideIcons.arrowRight,
                                  color: Colors.black,
                                  size: 20.r,
                                ),
                              ],
                            ),
                    ),
                  ),
                ),
              ),
            );
          }),
        ),
      ],
    );
  }

  Widget _buildLabel(String text) {
    return Text(
      text,
      style: SFPro.font(
        fontSize: 14.sp,
        fontWeight: FontWeight.w700,
        color: Colors.white,
      ),
    );
  }

  Widget _buildNameField(OnboardingController controller) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(12.r),
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 8, sigmaY: 8),
        child: Container(
          height: 50.h,
          decoration: BoxDecoration(
            color: Colors.grey.shade800.withOpacity(0.15),
            borderRadius: BorderRadius.circular(12.r),
          ),
          child: TextField(
            controller: controller.nameController,
            style: const TextStyle(color: Colors.white),
            decoration: InputDecoration(
              enabledBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(12.r),
                borderSide: BorderSide(color: Colors.grey.shade600),
              ),
              focusedBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(12.r),
                borderSide: BorderSide(width: 2, color: Colors.blue.shade200),
              ),
              filled: false,
              hintText: 'Enter your name',
              prefixIcon: Icon(
                LucideIcons.user,
                color: Colors.white70,
                size: 20.r,
              ),
              hintStyle: SFPro.font(
                fontWeight: FontWeight.w400,
                color: Colors.white70,
              ),
              border: InputBorder.none,
            ),
            onChanged: (_) {
              // Trigger rebuild to check form validity
              controller.update();
            },
          ),
        ),
      ),
    );
  }

  Widget _buildWhatBringsYouDropdown(OnboardingController controller) {
    final options = OnboardingController.whatBringsYouOptions
        .map((e) => e['label']!)
        .toList();

    return ClipRRect(
      borderRadius: BorderRadius.circular(12.r),
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 8, sigmaY: 8),
        child: Container(
          height: 50.h,
          decoration: BoxDecoration(
            border: Border.all(color: Colors.grey.shade600),
            color: Colors.grey.shade800.withOpacity(0.15),
            borderRadius: BorderRadius.circular(12.r),
          ),
          child: Theme(
            data: Theme.of(Get.context!).copyWith(
              inputDecorationTheme: const InputDecorationTheme(
                errorBorder: InputBorder.none,
                focusedBorder: InputBorder.none,
                focusedErrorBorder: InputBorder.none,
                disabledBorder: InputBorder.none,
                enabledBorder: InputBorder.none,
                isDense: false,
              ),
            ),
            child: CustomDropdown<String>(
              hideSelectedFieldWhenExpanded: true,
              decoration: CustomDropdownDecoration(
                listItemStyle: SFPro.font(),
                hintStyle: SFPro.font(color: Colors.grey.shade300),
                headerStyle: SFPro.font(color: Colors.grey.shade300),
                closedFillColor: Colors.transparent,
                closedSuffixIcon: Icon(
                  Icons.arrow_drop_down_rounded,
                  color: Colors.grey.shade300,
                  size: 28.r,
                ),
              ),
              hintText: 'Select an option',
              items: options,
              onChanged: (value) {
                if (value != null) {
                  final option = OnboardingController.whatBringsYouOptions
                      .firstWhere((e) => e['label'] == value);
                  controller.setWhatBringsYou(option['value']!);
                }
              },
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildCodingExperienceOptions(OnboardingController controller) {
    return Obx(() {
      final selected = controller.codingExperience.value;

      return Column(
        children: OnboardingController.codingExperienceOptions.map((option) {
          return Padding(
            padding: EdgeInsets.only(bottom: 8.h),
            child: SelectableOptionButton(
              title: option['label']!,
              subtitle: option['description'],
              isSelected: selected == option['value'],
              onTap: () => controller.setCodingExperience(option['value']!),
            ),
          );
        }).toList(),
      );
    });
  }
}
