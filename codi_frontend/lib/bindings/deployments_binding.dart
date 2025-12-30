/// Deployments feature binding
library;

import 'package:get/get.dart';

import '../features/deployments/controllers/deployments_controller.dart';
import '../features/deployments/services/deployment_service.dart';

/// Deployments screen binding
class DeploymentsBinding extends Bindings {
  @override
  void dependencies() {
    Get.lazyPut(() => DeploymentService());
    Get.lazyPut(() => DeploymentsController());
  }
}
