/// Projects feature binding
library;

import 'package:get/get.dart';

import '../features/projects/controllers/projects_controller.dart';
import '../features/projects/services/project_service.dart';

/// Projects screen binding
class ProjectsBinding extends Bindings {
  @override
  void dependencies() {
    Get.lazyPut(() => ProjectService());
    Get.lazyPut(() => ProjectsController());
  }
}
