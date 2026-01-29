/// Application routes configuration
library;

import 'package:get/get.dart';

import '../bindings/deployments_binding.dart';
import '../bindings/editor_binding.dart';
import '../bindings/environment_binding.dart';
import '../bindings/planning_binding.dart';
import '../bindings/projects_binding.dart';
import '../bindings/layout_binding.dart';
import '../features/auth/views/login_screen.dart';
import '../features/auth/views/splash_screen.dart';
import '../features/deployments/views/deployments_screen.dart';
import '../features/editor/views/editor_screen.dart';
import '../features/environment/screens/environment_manager_screen.dart';
import '../features/planning/views/plan_review_screen.dart';
import '../features/planning/views/walkthrough_screen.dart';
import '../features/projects/views/project_wizard_screen.dart';
import '../features/projects/views/project_detail_screen.dart';
import '../features/projects/views/projects_list_screen.dart';
import '../features/layout/views/layout_view.dart';
import '../features/layout/controllers/layout_controller.dart';
import '../features/settings/views/settings_screen.dart';

/// Application route definitions
class AppRoutes {
  AppRoutes._();

  // Route names
  static const String splash = '/';
  static const String login = '/login';
  static const String projects = '/projects';
  static const String layout = '/layout';
  static const String createProject = '/projects/create';
  static const String projectDetail = '/projects/:id';
  static const String editor = '/editor/:id';
  static const String environment = '/environment/:id';
  static const String deployments = '/deployments';
  static const String settings = '/settings';
  static const String planReview = '/plan-review';
  static const String walkthrough = '/walkthrough';

  /// All application routes with bindings
  static List<GetPage> get routes => [
        // Splash screen
        GetPage(
          name: splash,
          page: () => const SplashScreen(),
          transition: Transition.fade,
        ),

        // Login screen
        GetPage(
          name: login,
          page: () => const LoginScreen(),
          transition: Transition.fadeIn,
        ),

        // Projects list
        GetPage(
          name: projects,
          page: () => const ProjectsListScreen(),
          binding: ProjectsBinding(),
          transition: Transition.fadeIn,
        ),

        // Layout (Master View)
        GetPage(
          name: layout,
          page: () => const LayoutView(),
          binding: LayoutBinding(),
          transition: Transition.fadeIn,
        ),

        // Create project wizard
        GetPage(
          name: createProject,
          page: () => const ProjectWizardScreen(),
          binding: ProjectsBinding(),
          transition: Transition.rightToLeft,
        ),

        // Project detail
        GetPage(
          name: projectDetail,
          page: () => const ProjectDetailScreen(),
          binding: ProjectsBinding(),
          transition: Transition.rightToLeft,
        ),

        // Editor screen
        GetPage(
          name: editor,
          page: () => const EditorScreen(),
          binding: EditorBinding(),
          transition: Transition.fadeIn,
        ),

        // Deployments
        GetPage(
          name: deployments,
          page: () => const DeploymentsScreen(),
          binding: DeploymentsBinding(),
          transition: Transition.rightToLeft,
        ),

        // Settings
        GetPage(
          name: settings,
          page: () => const SettingsScreen(),
          transition: Transition.rightToLeft,
        ),

        // Plan review
        GetPage(
          name: planReview,
          page: () => const PlanReviewScreen(),
          binding: PlanningBinding(),
          transition: Transition.rightToLeft,
        ),

        // Environment Manager
        GetPage(
          name: environment,
          page: () => const EnvironmentManagerScreen(),
          binding: EnvironmentBinding(),
          transition: Transition.rightToLeft,
        ),

        // Walkthrough
        GetPage(
          name: walkthrough,
          page: () => const WalkthroughScreen(),
          transition: Transition.fadeIn,
        ),
      ];
}

