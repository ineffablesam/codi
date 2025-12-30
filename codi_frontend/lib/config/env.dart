/// Environment configuration
library;

/// Application environment settings
class Environment {
  Environment._();

  /// API base URL for REST endpoints
  static const String apiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://10.0.2.2:8000/api/v1',
  );

  /// WebSocket base URL for real-time updates
  static const String wsBaseUrl = String.fromEnvironment(
    'WS_BASE_URL',
    defaultValue: 'ws://10.0.2.2:8000',
  );

  /// GitHub OAuth client ID
  static const String githubClientId = String.fromEnvironment(
    'GITHUB_CLIENT_ID',
    defaultValue: '',
  );

  /// GitHub OAuth redirect URI
  static String get githubRedirectUri => '$apiBaseUrl/auth/github/callback';

  /// Connection timeout in milliseconds
  static const int connectionTimeout = 30000;

  /// Receive timeout in milliseconds
  static const int receiveTimeout = 30000;

  /// WebSocket reconnect attempts
  static const int wsReconnectAttempts = 5;

  /// WebSocket heartbeat interval in seconds
  static const int wsHeartbeatInterval = 30;

  /// Is debug mode
  static const bool isDebug = true;
}
