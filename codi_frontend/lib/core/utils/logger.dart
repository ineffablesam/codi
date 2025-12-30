/// Logger utility
library;

import 'dart:developer' as developer;

import '../../config/env.dart';

/// Application logger with different log levels
class AppLogger {
  AppLogger._();

  static const String _tag = 'Codi';

  /// Log debug message
  static void debug(String message, {Object? error}) {
    if (Environment.isDebug) {
      developer.log(
        message,
        name: _tag,
        level: 500,
        error: error,
      );
    }
  }

  /// Log info message
  static void info(String message) {
    developer.log(
      message,
      name: _tag,
      level: 800,
    );
  }

  /// Log warning message
  static void warning(String message, {Object? error}) {
    developer.log(
      '⚠️ $message',
      name: _tag,
      level: 900,
      error: error,
    );
  }

  /// Log error message
  static void error(String message, {Object? error, StackTrace? stackTrace}) {
    developer.log(
      '❌ $message',
      name: _tag,
      level: 1000,
      error: error,
      stackTrace: stackTrace,
    );
  }
}
