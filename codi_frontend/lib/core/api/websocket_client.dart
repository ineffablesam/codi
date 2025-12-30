/// WebSocket client for real-time agent updates
library;

import 'dart:async';
import 'dart:convert';
import 'dart:math';

import 'package:flutter/material.dart';
import 'package:get/get.dart';
import 'package:web_socket_channel/io.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

import '../../config/env.dart';
import '../../core/constants/app_colors.dart';
import '../storage/shared_prefs.dart';
import '../utils/logger.dart';

/// WebSocket client service for real-time communication
class WebSocketClient extends GetxService {
  WebSocketChannel? _channel;
  final _messageController = StreamController<Map<String, dynamic>>.broadcast();
  
  /// Stream of incoming WebSocket messages
  Stream<Map<String, dynamic>> get messageStream => _messageController.stream;
  
  /// Connection status
  final isConnected = false.obs;
  
  /// Current project ID
  String? _currentProjectId;
  
  Timer? _reconnectTimer;
  Timer? _heartbeatTimer;
  int _reconnectAttempts = 0;

  /// Connect to WebSocket for a specific project
  Future<void> connect(String projectId) async {
    if (_currentProjectId == projectId && isConnected.value) {
      AppLogger.debug('Already connected to project $projectId');
      return;
    }

    // Disconnect from previous project if any
    await disconnect();
    _currentProjectId = projectId;
    _reconnectAttempts = 0;

    await _connect();
  }

  Future<void> _connect() async {
    if (_currentProjectId == null) return;

    try {
      final token = SharedPrefs.getToken();
      if (token == null) {
        AppLogger.warning('No auth token available for WebSocket');
        return;
      }

      final wsUrl = '${Environment.wsBaseUrl}/api/v1/agents/$_currentProjectId/ws?token=$token';
      AppLogger.debug('Connecting to WebSocket: $wsUrl');

      _channel = IOWebSocketChannel.connect(
        Uri.parse(wsUrl),
        pingInterval: const Duration(seconds: 30),
      );

      isConnected.value = true;
      _reconnectAttempts = 0;
      _startHeartbeat();

      // Listen to messages
      _channel!.stream.listen(
        _onMessage,
        onError: _onError,
        onDone: _onDone,
      );

      AppLogger.info('WebSocket connected to project $_currentProjectId');
      
      _showSnackbar(
        'Connected',
        'Real-time updates enabled',
        backgroundColor: AppColors.success,
      );
    } catch (e) {
      AppLogger.error('WebSocket connection failed', error: e);
      _attemptReconnect();
    }
  }

  void _onMessage(dynamic message) {
    try {
      final data = jsonDecode(message as String) as Map<String, dynamic>;
      AppLogger.debug('WebSocket message: ${data['type']}');
      
      // Handle pong messages internally
      if (data['type'] == 'pong') {
        return;
      }
      
      // Broadcast message to listeners
      _messageController.add(data);
    } catch (e) {
      AppLogger.error('Failed to parse WebSocket message', error: e);
    }
  }

  void _onError(dynamic error) {
    AppLogger.error('WebSocket error', error: error);
    _attemptReconnect();
  }

  void _onDone() {
    AppLogger.info('WebSocket connection closed');
    isConnected.value = false;
    _heartbeatTimer?.cancel();
    
    if (_currentProjectId != null) {
      _attemptReconnect();
    }
  }

  void _startHeartbeat() {
    _heartbeatTimer?.cancel();
    _heartbeatTimer = Timer.periodic(
      const Duration(seconds: Environment.wsHeartbeatInterval),
      (_) {
        if (isConnected.value) {
          sendMessage({'type': 'ping'});
        }
      },
    );
  }

  void _attemptReconnect() {
    if (_reconnectAttempts >= Environment.wsReconnectAttempts) {
      AppLogger.warning('Max reconnection attempts reached');
      _showSnackbar(
        'Connection Failed',
        'Unable to connect to server. Please refresh.',
        backgroundColor: AppColors.error,
      );
      return;
    }

    _reconnectAttempts++;
    final delay = Duration(
      seconds: min(30, pow(2, _reconnectAttempts).toInt()),
    );

    AppLogger.info('Reconnecting in ${delay.inSeconds}s (attempt $_reconnectAttempts)');

    _reconnectTimer?.cancel();
    _reconnectTimer = Timer(delay, () {
      if (_currentProjectId != null) {
        _connect();
      }
    });
  }

  /// Send a message through the WebSocket
  void sendMessage(Map<String, dynamic> message) {
    if (_channel != null && isConnected.value) {
      try {
        _channel!.sink.add(jsonEncode(message));
        AppLogger.debug('WebSocket sent: ${message['type']}');
      } catch (e) {
        AppLogger.error('Failed to send WebSocket message', error: e);
      }
    } else {
      AppLogger.warning('WebSocket not connected, cannot send message');
    }
  }

  /// Send a user message to trigger agent workflow
  void sendUserMessage(String message) {
    sendMessage({
      'type': 'user_message',
      'message': message,
      'project_id': _currentProjectId,
    });
  }

  /// Send a response to user input request
  void sendUserInputResponse(dynamic response) {
    sendMessage({
      'type': 'user_input_response',
      'response': response,
    });
  }

  /// Disconnect from WebSocket
  Future<void> disconnect() async {
    _currentProjectId = null;
    _reconnectTimer?.cancel();
    _heartbeatTimer?.cancel();
    
    if (_channel != null) {
      await _channel!.sink.close();
      _channel = null;
    }
    
    isConnected.value = false;
    AppLogger.info('WebSocket disconnected');
  }

  void _showSnackbar(String title, String message, {Color? backgroundColor}) {
    if (Get.context != null) {
      Get.snackbar(
        title,
        message,
        duration: const Duration(seconds: 3),
        snackPosition: SnackPosition.BOTTOM,
        backgroundColor: backgroundColor ?? AppColors.primary,
        colorText: Colors.white,
        margin: const EdgeInsets.all(16),
      );
    }
  }

  @override
  void onClose() {
    _messageController.close();
    disconnect();
    super.onClose();
  }
}
