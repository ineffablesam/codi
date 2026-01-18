import 'dart:async';

import 'package:get/get.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

import '../../../core/api/api_service.dart';
import '../../../core/utils/logger.dart';

/// Log line model with unique identifier for deduplication
class LogLine {
  final String id; // Unique ID based on timestamp + content hash
  final String text;
  final DateTime timestamp;
  final LogLevel level;
  final bool isSystemMessage; // For Codi system messages

  LogLine({
    required this.id,
    required this.text,
    DateTime? timestamp,
    this.level = LogLevel.info,
    this.isSystemMessage = false,
  }) : timestamp = timestamp ?? DateTime.now();

  /// Create a system message (from Codi, not from container)
  factory LogLine.system(String message, {LogLevel level = LogLevel.system}) {
    final now = DateTime.now();
    return LogLine(
      id: 'system_${now.microsecondsSinceEpoch}_${message.hashCode}',
      text: message,
      timestamp: now,
      level: level,
      isSystemMessage: true,
    );
  }

  factory LogLine.fromText(String text) {
    // Parse timestamp if present (Docker log format: 2024-01-01T12:00:00.000000000Z message)
    DateTime? parsedTimestamp;
    String cleanText = text;
    
    // Try to extract ISO timestamp from Docker log format
    if (text.length > 30 && text.contains('T') && text.contains('Z')) {
      final match = RegExp(r'^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z)\s').firstMatch(text);
      if (match != null) {
        try {
          parsedTimestamp = DateTime.parse(match.group(1)!);
          cleanText = text.substring(match.end);
        } catch (_) {}
      }
    }
    
    // Determine log level
    LogLevel level = LogLevel.info;
    final lowerText = cleanText.toLowerCase();
    if (lowerText.contains('error') || lowerText.contains('err')) {
      level = LogLevel.error;
    } else if (lowerText.contains('warn')) {
      level = LogLevel.warning;
    } else if (lowerText.contains('debug')) {
      level = LogLevel.debug;
    } else if (lowerText.contains('✓') || lowerText.contains('ready') || lowerText.contains('success')) {
      level = LogLevel.success;
    }

    // Generate unique ID from timestamp and content
    final ts = parsedTimestamp ?? DateTime.now();
    final id = '${ts.microsecondsSinceEpoch}_${cleanText.hashCode}';

    return LogLine(
      id: id,
      text: cleanText.trim(),
      timestamp: parsedTimestamp,
      level: level,
    );
  }
  
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is LogLine && runtimeType == other.runtimeType && id == other.id;

  @override
  int get hashCode => id.hashCode;
}

enum LogLevel { debug, info, success, warning, error, system }

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
  
  // Deduplication: track seen log IDs
  final Set<String> _seenLogIds = {};
  
  // Track if initial logs have been fetched
  bool _initialFetchDone = false;

  @override
  void onClose() {
    stopLogStream();
    super.onClose();
  }

  /// Add a system message to the logs
  void _addSystemMessage(String message, {LogLevel level = LogLevel.system}) {
    final log = LogLine.system(message, level: level);
    logs.add(log);
    _seenLogIds.add(log.id);
  }

  /// Initialize logs for a container - fetches historical and starts streaming
  Future<void> initializeLogs(String containerId) async {
    // Clear previous logs
    clearLogs();
    _initialFetchDone = false;
    
    // System message: loading
    _addSystemMessage('📋 Loading container logs...');
    
    // Fetch historical logs first
    await fetchLogs(containerId);
    _initialFetchDone = true;
    
    // Start streaming only NEW logs
    await startLogStream(containerId, onlyNew: true);
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
        
        for (final line in logLines) {
          _addLogIfNew(LogLine.fromText(line.toString()));
        }
      }
    } catch (e) {
      AppLogger.error('Failed to fetch logs', error: e);
      error.value = 'Failed to fetch logs';
      _addSystemMessage('❌ Failed to fetch logs', level: LogLevel.error);
    } finally {
      isLoading.value = false;
    }
  }

  /// Start streaming logs via WebSocket
  Future<void> startLogStream(String containerId, {bool onlyNew = false}) async {
    // Stop any existing stream
    await stopLogStream(silent: true);

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
      
      // System message: connected
      _addSystemMessage('🟢 Live stream connected — watching for new logs');

      _subscription = _channel!.stream.listen(
        (data) {
          final line = LogLine.fromText(data.toString());
          // Only add if not already seen (deduplication)
          _addLogIfNew(line);
        },
        onError: (e) {
          AppLogger.error('Log stream error', error: e);
          error.value = 'Log stream error';
          isStreaming.value = false;
          _addSystemMessage('⚠️ Stream disconnected due to error', level: LogLevel.warning);
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
      _addSystemMessage('❌ Failed to connect to live stream', level: LogLevel.error);
    }
  }
  
  /// Add log line only if it's new (deduplication)
  void _addLogIfNew(LogLine line) {
    if (_seenLogIds.contains(line.id)) {
      return; // Skip duplicate
    }
    
    _seenLogIds.add(line.id);
    logs.add(line);
    
    // Keep max 1000 lines and corresponding IDs
    if (logs.length > 1000) {
      final removed = logs.removeAt(0);
      _seenLogIds.remove(removed.id);
    }
  }

  /// Stop streaming logs (pause)
  Future<void> stopLogStream({bool silent = false}) async {
    final wasStreaming = isStreaming.value;
    
    await _subscription?.cancel();
    _subscription = null;

    await _channel?.sink.close();
    _channel = null;

    isStreaming.value = false;
    
    // Only show message if we were actually streaming and not silent
    if (wasStreaming && !silent) {
      _addSystemMessage('⏸️ Live stream paused');
    }
  }
  
  /// Resume streaming without duplicating logs
  Future<void> resumeLogStream() async {
    if (containerId.value != null) {
      await startLogStream(containerId.value!, onlyNew: true);
    }
  }

  /// Clear logs
  void clearLogs() {
    logs.clear();
    _seenLogIds.clear();
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
      _addSystemMessage('🔄 Restarting container...');
      
      final response = await _apiService.post('/containers/$containerId/restart');
      
      if (response.statusCode == 200) {
        _addSystemMessage('✅ Container restart initiated — new logs will appear shortly', level: LogLevel.success);
        return true;
      } else {
        _addSystemMessage('❌ Failed to restart container', level: LogLevel.error);
        return false;
      }
    } catch (e) {
      AppLogger.error('Failed to restart container', error: e);
      error.value = 'Failed to restart container';
      _addSystemMessage('❌ Failed to restart container: ${e.toString()}', level: LogLevel.error);
      return false;
    } finally {
      isLoading.value = false;
    }
  }

  /// Stop container
  Future<bool> stopContainer(String containerId) async {
    try {
      isLoading.value = true;
      _addSystemMessage('🛑 Stopping container...');
      
      final response = await _apiService.post('/containers/$containerId/stop');
      
      if (response.statusCode == 200) {
        _addSystemMessage('✅ Container stopped successfully', level: LogLevel.success);
        return true;
      } else {
        _addSystemMessage('❌ Failed to stop container', level: LogLevel.error);
        return false;
      }
    } catch (e) {
      AppLogger.error('Failed to stop container', error: e);
      error.value = 'Failed to stop container';
      _addSystemMessage('❌ Failed to stop container: ${e.toString()}', level: LogLevel.error);
      return false;
    } finally {
      isLoading.value = false;
    }
  }
}
