import 'package:get/get.dart';

import '../features/environment/controllers/environment_controller.dart';
import '../features/environment/services/environment_service.dart';

class EnvironmentBinding extends Bindings {
  @override
  void dependencies() {
    Get.lazyPut<EnvironmentService>(() => EnvironmentService());
    Get.lazyPut<EnvironmentController>(() => EnvironmentController());
  }
}
