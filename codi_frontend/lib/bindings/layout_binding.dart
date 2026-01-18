import 'package:get/get.dart';
import '../features/layout/controllers/layout_controller.dart';
import '../features/projects/controllers/projects_controller.dart';

class LayoutBinding extends Bindings {
  @override
  void dependencies() {
    Get.lazyPut<LayoutController>(() => LayoutController());
    Get.lazyPut<ProjectsController>(() => ProjectsController());
  }
}
