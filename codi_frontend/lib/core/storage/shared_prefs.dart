/// Shared preferences storage wrapper
library;

import 'package:shared_preferences/shared_preferences.dart';

/// Wrapper for shared_preferences providing typed access
class SharedPrefs {
  SharedPrefs._();

  static SharedPreferences? _prefs;

  // Storage keys
  static const String _keyToken = 'auth_token';
  static const String _keyUserId = 'user_id';
  static const String _keyUsername = 'username';
  static const String _keyAvatarUrl = 'avatar_url';
  static const String _keyDarkMode = 'dark_mode';
  static const String _keyNotifications = 'notifications';
  static const String _keyLastProjectId = 'last_project_id';
  static const String _keyOnboardingComplete = 'onboarding_complete';

  /// Initialize shared preferences
  static Future<void> init() async {
    _prefs = await SharedPreferences.getInstance();
  }

  /// Get SharedPreferences instance
  static SharedPreferences get prefs {
    if (_prefs == null) {
      throw Exception('SharedPrefs not initialized. Call init() first.');
    }
    return _prefs!;
  }

  // Token management
  
  /// Get authentication token
  static String? getToken() => prefs.getString(_keyToken);

  /// Set authentication token
  static Future<bool> setToken(String token) =>
      prefs.setString(_keyToken, token);

  /// Remove authentication token
  static Future<bool> removeToken() => prefs.remove(_keyToken);

  /// Check if user is logged in
  static bool get isLoggedIn => getToken() != null;

  // User info
  
  /// Get user ID
  static int? getUserId() => prefs.getInt(_keyUserId);

  /// Set user ID
  static Future<bool> setUserId(int id) => prefs.setInt(_keyUserId, id);

  /// Get username
  static String? getUsername() => prefs.getString(_keyUsername);

  /// Set username
  static Future<bool> setUsername(String username) =>
      prefs.setString(_keyUsername, username);

  /// Get avatar URL
  static String? getAvatarUrl() => prefs.getString(_keyAvatarUrl);

  /// Set avatar URL
  static Future<bool> setAvatarUrl(String url) =>
      prefs.setString(_keyAvatarUrl, url);

  // Settings
  
  /// Get dark mode preference
  static bool getDarkMode() => prefs.getBool(_keyDarkMode) ?? false;

  /// Set dark mode preference
  static Future<bool> setDarkMode(bool enabled) =>
      prefs.setBool(_keyDarkMode, enabled);

  /// Get notifications preference
  static bool getNotifications() => prefs.getBool(_keyNotifications) ?? true;

  /// Set notifications preference
  static Future<bool> setNotifications(bool enabled) =>
      prefs.setBool(_keyNotifications, enabled);

  // Project state
  
  /// Get last opened project ID
  static int? getLastProjectId() => prefs.getInt(_keyLastProjectId);

  /// Set last opened project ID
  static Future<bool> setLastProjectId(int id) =>
      prefs.setInt(_keyLastProjectId, id);

  /// Check if onboarding is complete
  static bool getOnboardingComplete() =>
      prefs.getBool(_keyOnboardingComplete) ?? false;

  /// Set onboarding complete
  static Future<bool> setOnboardingComplete(bool complete) =>
      prefs.setBool(_keyOnboardingComplete, complete);

  // Utility methods
  
  /// Save user session data
  static Future<void> saveUserSession({
    required String token,
    required int userId,
    required String username,
    String? avatarUrl,
  }) async {
    await setToken(token);
    await setUserId(userId);
    await setUsername(username);
    if (avatarUrl != null) {
      await setAvatarUrl(avatarUrl);
    }
  }

  /// Clear all user data (logout)
  static Future<void> clearUserSession() async {
    await removeToken();
    await prefs.remove(_keyUserId);
    await prefs.remove(_keyUsername);
    await prefs.remove(_keyAvatarUrl);
    await prefs.remove(_keyLastProjectId);
  }

  /// Clear all data
  static Future<bool> clearAll() => prefs.clear();
}
