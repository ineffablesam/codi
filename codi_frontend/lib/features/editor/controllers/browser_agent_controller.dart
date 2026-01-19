/// Browser agent controller
library;

import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:get/get.dart';

import '../../../core/api/websocket_client.dart';
import '../../../core/utils/logger.dart';

/// Controller for browser agent panel and streaming
class BrowserAgentController extends GetxController {
  late final WebSocketClient _webSocketClient;

  // Current browser frame (decoded bytes)
  final currentFrame = Rxn<Uint8List>();

  // Browser session state
  final isSessionActive = false.obs;
  final currentUrl = 'https://google.com'.obs;
  final isLoading = false.obs;

  // Stats for debugging
  final frameCount = 0.obs;
  final lastFrameTime = DateTime.now().obs;
  final lastFrameSize = 0.obs;
  final fps = 0.0.obs;
  final errorCount = 0.obs;
  final lastError = RxnString();

  StreamSubscription? _frameSubscription;

  // Frame throttling
  Timer? _frameUpdateTimer;
  Uint8List? _pendingFrame;
  static const _frameUpdateInterval = Duration(milliseconds: 33); // ~30 FPS cap

  @override
  void onInit() {
    super.onInit();
    _webSocketClient = Get.find<WebSocketClient>();
    _subscribeToFrames();
    _startFrameUpdateTimer();
  }

  /// Start timer to update frames at consistent interval
  void _startFrameUpdateTimer() {
    _frameUpdateTimer = Timer.periodic(_frameUpdateInterval, (_) {
      if (_pendingFrame != null) {
        currentFrame.value = _pendingFrame;
        _pendingFrame = null;
      }
    });
  }

  /// Subscribe to browser frame updates from WebSocket
  void _subscribeToFrames() {
    _frameSubscription = _webSocketClient.messageStream.listen((data) {
      final messageType = data['type'] as String?;

      if (messageType == 'browser_frame') {
        _handleBrowserFrame(data);
      } else if (messageType == 'agent_status' && data['agent'] == 'browser') {
        _handleBrowserStatus(data);
      }
    });
  }

  /// Handle incoming browser frame
  void _handleBrowserFrame(Map<String, dynamic> data) {
    try {
      final imageB64 = data['image'] as String?;
      if (imageB64 != null) {
        lastFrameSize.value = imageB64.length;
        print('BrowserFrame: received ${imageB64.length} chars');

        final bytes = base64Decode(imageB64);

        // Store frame for next update cycle (throttled)
        _pendingFrame = bytes;

        isSessionActive.value = true;
        isLoading.value = false;

        // Calculate FPS
        final now = DateTime.now();
        final diff = now.difference(lastFrameTime.value).inMilliseconds;
        if (diff > 0) {
          fps.value = 1000 / diff;
        }

        frameCount.value++;
        lastFrameTime.value = now;
      } else {
        errorCount.value++;
        lastError.value = 'Empty image data received';
        print('BrowserFrame Error: Empty image data');
        AppLogger.warning('Empty image data in browser_frame');
      }
    } catch (e) {
      errorCount.value++;
      lastError.value = e.toString();
      print('BrowserFrame Decode Error: $e');
      final imageB64 = data['image'] as String?;
      AppLogger.error(
          'Failed to decode browser frame (len: ${imageB64?.length})',
          error: e);
    }
  }

  /// Send mouse event to browser
  void sendMouseEvent({
    required String eventType,
    required double x,
    required double y,
    String button = 'left',
    int clickCount = 1,
  }) {
    if (!isSessionActive.value) return;

    _webSocketClient.sendMessage({
      'type': 'user_interaction',
      'agent': 'browser',
      'payload': {
        'type': 'input_mouse',
        'eventType': eventType,
        'x': x.toInt(),
        'y': y.toInt(),
        'button': button,
        'clickCount': clickCount,
      }
    });
  }

  /// Send keyboard event to browser
  void sendKeyboardEvent({
    required String eventType,
    required String key,
    String? code,
  }) {
    if (!isSessionActive.value) return;

    _webSocketClient.sendMessage({
      'type': 'user_interaction',
      'agent': 'browser',
      'payload': {
        'type': 'input_keyboard',
        'eventType': eventType,
        'key': key,
        'code': code,
      }
    });
  }

  /// Handle browser agent status updates
  void _handleBrowserStatus(Map<String, dynamic> data) {
    final status = data['status'] as String?;

    if (status == 'started') {
      isLoading.value = true;
      isSessionActive.value = true;
    } else if (status == 'completed' || status == 'error') {
      isLoading.value = false;
    }

    // Update URL if provided
    final url = data['url'] as String?;
    if (url != null) {
      currentUrl.value = url;
    }
  }

  // Viewport settings
  final isMobile = false.obs;
  static const _desktopViewport = {
    'width': 1280,
    'height': 800,
    'userAgent': null
  };
  static const _mobileViewport = {
    'width': 390,
    'height': 844,
    'userAgent':
        'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1'
  };

  /// Toggle between mobile and desktop viewport
  void toggleViewport() {
    isMobile.value = !isMobile.value;
    final settings = isMobile.value ? _mobileViewport : _desktopViewport;

    _webSocketClient.sendMessage({
      'type': 'user_interaction',
      'agent': 'browser',
      'payload': {
        'type': 'set_viewport',
        'width': settings['width'],
        'height': settings['height'],
        'isMobile': isMobile.value,
        'userAgent': settings['userAgent'],
      }
    });

    AppLogger.debug(
        'Toggled viewport: ${isMobile.value ? "Mobile" : "Desktop"}');
  }

  /// Clear the current browser session
  void clearSession() {
    currentFrame.value = null;
    _pendingFrame = null;
    isSessionActive.value = false;
    currentUrl.value = 'https://google.com';
    isMobile.value = false; // Reset to desktop on clear
  }

  @override
  void onClose() {
    _frameSubscription?.cancel();
    _frameUpdateTimer?.cancel();
    _pendingFrame = null;
    super.onClose();
  }
}
