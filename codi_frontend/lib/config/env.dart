import 'dart:io';

import 'package:flutter/foundation.dart';

class Environment {
  Environment._();

  /// Check if running in development mode
  static bool get isDevelopment => kDebugMode;

  /// Check if running in production mode
  static bool get isProduction => kReleaseMode;

  /// Check if running in profile mode
  static bool get isProfile => kProfileMode;

  static const String _apiBaseUrlFromEnv =
      String.fromEnvironment('API_BASE_URL', defaultValue: '');

  static String get apiBaseUrl {
    // Highest priority: build-time override
    if (_apiBaseUrlFromEnv.isNotEmpty) {
      return _apiBaseUrlFromEnv;
    }

    // Local development defaults
    if (isDebug) {
      if (Platform.isAndroid) {
        return 'http://10.0.2.2:8000/api/v1';
      }
      if (Platform.isIOS) {
        return 'http://localhost:8000/api/v1';
      }
    }

    // Fallback (should never happen in prod)
    return 'https://api.yourapp.com/api/v1';
  }

  static String get wsBaseUrl {
    final base = apiBaseUrl.replaceFirst('http', 'ws');
    return base.replaceAll('/api/v1', '');
  }

  static const String githubClientId =
      String.fromEnvironment('GITHUB_CLIENT_ID', defaultValue: '');

  static String get githubRedirectUri => '$apiBaseUrl/auth/github/callback';

  static const int connectionTimeout = 30000;
  static const int receiveTimeout = 30000;

  static const int wsReconnectAttempts = 5;
  static const int wsHeartbeatInterval = 30;

  static const bool isDebug = bool.fromEnvironment(
    'DEBUG',
    defaultValue: true,
  );
}
