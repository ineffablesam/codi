import 'dart:async';
import 'dart:convert';

import 'package:get/get.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

import '../../../core/api/api_service.dart';
import '../../../core/utils/logger.dart';

/// Log line model
class LogLine {
  final String text;
  final DateTime timestamp;
  final LogLevel level;

  LogLine({
    required this.text,
    DateTime? timestamp,
    this.level = LogLevel.info,
  }) : timestamp = timestamp ?? DateTime.now();

  factory LogLine.fromText(String text) {
    // Parse timestamp if present
    LogLevel level = LogLevel.info;
    if (text.contains('ERROR') || text.contains('error')) {
      level = LogLevel.error;
    } else if (text.contains('WARN') || text.contains('warn')) {
      level = LogLevel.warning;
    } else if (text.contains('DEBUG') || text.contains('debug')) {
      level = LogLevel.debug;
    }

    return LogLine(text: text, level: level);
  }
}

enum LogLevel { debug, info, warning, error }

/// Controller for container logs streaming
class ContainerLogsController extends GetxController {
  final ApiService _apiService = Get.find<ApiService>();
  
  // State
  final logs = <LogLine>[].obs;
  final isStreaming = false.obs;
  final isLoading = false.obs;
  final error = RxnString();
  final autoScroll = true.obs;

  // Current container
  final containerId = RxnString();
  final containerName = RxnString();
  final containerStatus = RxnString();

  // WebSocket for streaming
  WebSocketChannel? _channel;
  StreamSubscription? _subscription;

  @override
  void onClose() {
    stopLogStream();
    super.onClose();
  }

  /// Fetch recent logs (non-streaming)
  Future<void> fetchLogs(String containerId, {int tail = 100}) async {
    try {
      isLoading.value = true;
      error.value = null;
      this.containerId.value = containerId;

      final response = await _apiService.get(
        '/containers/$containerId/logs',
        queryParameters: {'tail': tail},
      );

      if (response.data != null) {
        final data = response.data as Map<String, dynamic>;
        final logLines = (data['logs'] as List<dynamic>?) ?? [];
        
        logs.value = logLines
            .map((line) => LogLine.fromText(line.toString()))
            .toList();
      }
    } catch (e) {
      AppLogger.error('Failed to fetch logs', error: e);
      error.value = 'Failed to fetch logs';
    } finally {
      isLoading.value = false;
    }
  }

  /// Start streaming logs via WebSocket
  Future<void> startLogStream(String containerId) async {
    // Stop any existing stream
    await stopLogStream();

    try {
      this.containerId.value = containerId;
      isStreaming.value = true;
      error.value = null;

      // Build WebSocket URL
      final baseUrl = _apiService.baseUrl
          .replaceFirst('http://', 'ws://')
          .replaceFirst('https://', 'wss://');
      final wsUrl = '$baseUrl/containers/$containerId/logs/stream';

      AppLogger.info('Connecting to log stream: $wsUrl');

      _channel = WebSocketChannel.connect(Uri.parse(wsUrl));

      _subscription = _channel!.stream.listen(
        (data) {
          final line = LogLine.fromText(data.toString());
          logs.add(line);
          
          // Keep max 1000 lines
          if (logs.length > 1000) {
            logs.removeAt(0);
          }
        },
        onError: (e) {
          AppLogger.error('Log stream error', error: e);
          error.value = 'Log stream error';
          isStreaming.value = false;
        },
        onDone: () {
          AppLogger.info('Log stream closed');
          isStreaming.value = false;
        },
      );
    } catch (e) {
      AppLogger.error('Failed to start log stream', error: e);
      error.value = 'Failed to connect to log stream';
      isStreaming.value = false;
    }
  }

  /// Stop streaming logs
  Future<void> stopLogStream() async {
    await _subscription?.cancel();
    _subscription = null;

    await _channel?.sink.close();
    _channel = null;

    isStreaming.value = false;
  }

  /// Clear logs
  void clearLogs() {
    logs.clear();
  }

  /// Toggle auto-scroll
  void toggleAutoScroll() {
    autoScroll.value = !autoScroll.value;
  }

  /// Get container stats
  Future<Map<String, dynamic>?> getContainerStats(String containerId) async {
    try {
      final response = await _apiService.get('/containers/$containerId/stats');
      return response.data as Map<String, dynamic>?;
    } catch (e) {
      AppLogger.error('Failed to get container stats', error: e);
      return null;
    }
  }

  /// Restart container
  Future<bool> restartContainer(String containerId) async {
    try {
      isLoading.value = true;
      final response = await _apiService.post('/containers/$containerId/restart');
      return response.statusCode == 200;
    } catch (e) {
      AppLogger.error('Failed to restart container', error: e);
      error.value = 'Failed to restart container';
      return false;
    } finally {
      isLoading.value = false;
    }
  }

  /// Stop container
  Future<bool> stopContainer(String containerId) async {
    try {
      isLoading.value = true;
      final response = await _apiService.post('/containers/$containerId/stop');
      return response.statusCode == 200;
    } catch (e) {
      AppLogger.error('Failed to stop container', error: e);
      error.value = 'Failed to stop container';
      return false;
    } finally {
      isLoading.value = false;
    }
  }
}
