/// Browser agent controller
library;

import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:get/get.dart';

import '../../../core/api/websocket_client.dart';
import '../../../core/utils/logger.dart';

/// Controller for browser agent panel and streaming
class BrowserAgentController extends GetxController {
  late final WebSocketClient _webSocketClient;
  final lastSentText = ''.obs;

  // Current browser frame (decoded bytes)
  final currentFrame = Rxn<Uint8List>();

  // Browser session state
  final isSessionActive = false.obs;
  final currentUrl = 'Start Interactive or AI Agent session'.obs;

  final isLoading = false.obs;

  // Interactive mode - user controls browser directly (no AI)
  final isInteractiveMode = false.obs;

  // Text controller for interactive keyboard input
  final textInputController = TextEditingController();

  // Actual device/viewport dimensions from screencast metadata
  // These are updated with each frame and used for coordinate scaling
  final actualDeviceWidth = 1440.obs;
  final actualDeviceHeight = 900.obs;

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
      } else if (messageType == 'browser_url_changed') {
        _handleUrlChanged(data);
      } else if (messageType == 'agent_status' && data['agent'] == 'browser') {
        _handleBrowserStatus(data);
      }
    });
  }

  /// Handle URL change from browser-agent
  void _handleUrlChanged(Map<String, dynamic> data) {
    final url = data['url'] as String?;
    if (url != null && url.isNotEmpty) {
      currentUrl.value = url;
      AppLogger.debug('Browser URL changed: $url');
    }
  }

  /// Handle incoming browser frame
  void _handleBrowserFrame(Map<String, dynamic> data) {
    // strict check: don't process frames if session is not active
    // this prevents lingering frames from re-showing the view after "Stop" is clicked
    if (!isSessionActive.value) return;

    try {
      final imageB64 = data['image'] as String?;
      if (imageB64 != null) {
        lastFrameSize.value = imageB64.length;
        print('BrowserFrame: received ${imageB64.length} chars');

        final bytes = base64Decode(imageB64);

        // Store frame for next update cycle (throttled)
        _pendingFrame = bytes;

        // Update actual device dimensions from metadata
        final deviceWidth = data['deviceWidth'] as int?;
        final deviceHeight = data['deviceHeight'] as int?;
        if (deviceWidth != null && deviceWidth > 0) {
          actualDeviceWidth.value = deviceWidth;
        }
        if (deviceHeight != null && deviceHeight > 0) {
          actualDeviceHeight.value = deviceHeight;
        }

        // REMOVED: isSessionActive.value = true; 
        // We rely on explicit 'started' events to manage lifecycle now.
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
  /// Coordinates are scaled from widget size to browser viewport size
  void sendMouseEvent({
    required String eventType,
    required double x,
    required double y,
    String button = 'left',
    int clickCount = 1,
    Size? widgetSize, // Size of the Flutter widget displaying the image
  }) {
    if (!isSessionActive.value) return;

    // Use actual device dimensions from screencast metadata (updated with each frame)
    final browserWidth = actualDeviceWidth.value;
    final browserHeight = actualDeviceHeight.value;

    // Scale coordinates if widget size is provided
    double scaledX = x;
    double scaledY = y;

    if (widgetSize != null && widgetSize.width > 0 && widgetSize.height > 0) {
      // Calculate the aspect ratios
      final browserAspect = browserWidth / browserHeight;
      final widgetAspect = widgetSize.width / widgetSize.height;

      double imageWidth, imageHeight, offsetX, offsetY;

      if (widgetAspect > browserAspect) {
        // Widget is wider - image height fills widget, width is letterboxed
        imageHeight = widgetSize.height;
        imageWidth = imageHeight * browserAspect;
        offsetX = (widgetSize.width - imageWidth) / 2;
        offsetY = 0;
      } else {
        // Widget is taller - image width fills widget, height is letterboxed
        imageWidth = widgetSize.width;
        imageHeight = imageWidth / browserAspect;
        offsetX = 0;
        offsetY = (widgetSize.height - imageHeight) / 2;
      }

      // Adjust for offset and scale
      scaledX = ((x - offsetX) / imageWidth) * browserWidth;
      scaledY = ((y - offsetY) / imageHeight) * browserHeight;

      // Clamp to browser viewport bounds
      scaledX = scaledX.clamp(0, browserWidth.toDouble());
      scaledY = scaledY.clamp(0, browserHeight.toDouble());
    }

    _webSocketClient.sendMessage({
      'type': 'user_interaction',
      'agent': 'browser',
      'payload': {
        'type': 'input_mouse',
        'eventType': eventType,
        'x': scaledX.toInt(),
        'y': scaledY.toInt(),
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

  /// Navigate back in browser history
  void goBack() {
    if (!isSessionActive.value) return;
    _webSocketClient.sendMessage({
      'type': 'browser_navigation',
      'action': 'back',
    });
  }

  /// Navigate forward in browser history
  void goForward() {
    if (!isSessionActive.value) return;
    _webSocketClient.sendMessage({
      'type': 'browser_navigation',
      'action': 'forward',
    });
  }

  /// Refresh the current page
  void refresh() {
    if (!isSessionActive.value) return;
    _webSocketClient.sendMessage({
      'type': 'browser_navigation',
      'action': 'reload',
    });
  }

  /// Navigate to a specific URL
  void navigateTo(String url) {
    if (!isSessionActive.value) return;
    // Ensure URL has a protocol
    String targetUrl = url;
    if (!url.startsWith('http://') && !url.startsWith('https://')) {
      targetUrl = 'https://$url';
    }
    currentUrl.value = targetUrl;
    _webSocketClient.sendMessage({
      'type': 'browser_navigation',
      'action': 'navigate',
      'url': targetUrl,
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

  /// Toggle between mobile and desktop viewport (with confirmation)
  Future<void> requestViewportChange() async {
    if (!isSessionActive.value) {
      // No active session, just toggle
      _doToggleViewport();
      return;
    }

    // Show confirmation dialog
    final confirmed = await Get.dialog<bool>(
      AlertDialog(
        title: const Text('Change Viewport?'),
        content: Text(
          'Changing viewport may interrupt ongoing tasks. Switch to ${isMobile.value ? "Desktop" : "Mobile"} view?',
        ),
        actions: [
          TextButton(
            onPressed: () => Get.back(result: false),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Get.back(result: true),
            child: const Text('Change'),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      _doToggleViewport();
    }
  }

  /// Actually toggle the viewport
  void _doToggleViewport() {
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

  /// Legacy method for backwards compatibility
  void toggleViewport() {
    requestViewportChange();
  }

  /// Clear the current browser session
  void clearSession() {
    // Notify backend to close the session
    if (isSessionActive.value) {
      _webSocketClient.sendMessage({
        'type': 'end_browser_session',
      });
    }

    currentFrame.value = null;
    _pendingFrame = null;
    isSessionActive.value = false;
    isInteractiveMode.value = false;
    isLoading.value = false;
    currentUrl.value = 'https://google.com';
    isMobile.value = false; // Reset to desktop on clear
  }

  /// Stop an ongoing browser agent task without ending the session
  void stopBrowserAgent() {
    if (!isSessionActive.value) return;

    _webSocketClient.sendMessage({
      'type': 'stop_browser_agent',
    });

    isLoading.value = false;
    AppLogger.debug('Sent stop signal to browser agent');
  }

  /// Start an interactive-only browser session (no AI control)
  /// User can directly interact with the browser via mouse/keyboard
  void startInteractiveSession({String initialUrl = 'https://google.com'}) {
    if (isLoading.value || isSessionActive.value) return;

    isLoading.value = true;
    isInteractiveMode.value = true;

    // Send request to start interactive browser session
    _webSocketClient.sendMessage({
      'type': 'start_interactive_browser',
      'initial_url': initialUrl,
    });

    AppLogger.debug('Starting interactive browser session: $initialUrl');
  }

  /// Send text as keyboard input
  void sendTextInput(String text) {
    if (!isSessionActive.value || text.isEmpty) return;

    _webSocketClient.sendMessage({
      'type': 'user_interaction',
      'agent': 'browser',
      'payload': {
        'type': 'input_keyboard',
        'eventType': 'type',
        'text': text,
      }
    });
  }

  /// Send special key press (Enter, Tab, Backspace, etc.)
  void sendSpecialKey(String key) {
    if (!isSessionActive.value) return;

    AppLogger.debug('Sending special key: $key');

    _webSocketClient.sendMessage({
      'type': 'user_interaction',
      'agent': 'browser',
      'payload': {
        'type': 'input_keyboard',
        'eventType': 'press',
        'key': key,
      }
    });
  }

  @override
  void onClose() {
    _frameSubscription?.cancel();
    _frameUpdateTimer?.cancel();
    _pendingFrame = null;
    super.onClose();
  }
}
