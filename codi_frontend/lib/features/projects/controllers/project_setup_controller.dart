import 'package:get/get.dart';
import '../../../core/api/websocket_client.dart';
import '../../../core/utils/logger.dart';
import '../../editor/controllers/editor_controller.dart';

class ProjectSetupController extends GetxController {
  final _editorController = Get.find<EditorController>();
  late final WebSocketClient _webSocketClient;

  // Setup state
  final setupStage = 'completed'.obs;
  final isInitialSetup = false.obs;
  final setupProgress = 0.0.obs;
  final setupMessage = ''.obs;

  @override
  void onInit() {
    super.onInit();
    _webSocketClient = Get.find<WebSocketClient>();
    
    // Initialize with current project state if available
    final project = _editorController.currentProject.value;
    if (project != null) {
      // Note: project model needs update to include setup_stage
      // For now default to completed until we update the frontend model
      setupStage.value = project.setupStage ?? 'completed';
      _updateStatus();
    }

    // Listen for WebSocket updates
    _webSocketClient.messageStream.listen(_handleWebSocketMessage);
    
    // Listen for project changes
    ever(_editorController.currentProject, (project) {
      if (project != null) {
        setupStage.value = project.setupStage ?? 'completed';
        _updateStatus();
      }
    });
  }

  void _handleWebSocketMessage(Map<String, dynamic> data) {
    if (data['type'] == 'project_update') {
      final stage = data['setup_stage'];
      if (stage != null) {
        setupStage.value = stage;
        _updateStatus();
      }
    }
  }

  void _updateStatus() {
    isInitialSetup.value = setupStage.value != 'completed';
    
    switch (setupStage.value) {
      case 'pending':
        setupMessage.value = 'Preparing environment...';
        setupProgress.value = 0.1;
        break;
      case 'deploying_starter':
        setupMessage.value = 'Deploying starter template...';
        setupProgress.value = 0.3;
        break;
      case 'building_idea':
        setupMessage.value = 'Building your idea...';
        setupProgress.value = 0.6;
        break;
      case 'deploying_final':
        setupMessage.value = 'Final deployment...';
        setupProgress.value = 0.9;
        break;
      case 'completed':
        setupMessage.value = 'Ready!';
        setupProgress.value = 1.0;
        break;
    }
  }
}
