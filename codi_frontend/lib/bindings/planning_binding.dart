/// Planning binding for dependency injection
library;

import 'package:get/get.dart';

import '../features/planning/controllers/planning_controller.dart';
import '../features/planning/services/planning_service.dart';

/// Binding for planning feature dependencies
class PlanningBinding extends Bindings {
  @override
  void dependencies() {
    Get.lazyPut(() => PlanningService());
    Get.lazyPut(() => PlanningController());
  }
}
