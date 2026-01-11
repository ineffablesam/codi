/// Dio HTTP client with interceptors
library;

import 'package:dio/dio.dart';
import 'package:get/get.dart' hide Response;

import '../../config/env.dart';
import '../../config/routes.dart';
import '../storage/shared_prefs.dart';
import '../utils/logger.dart';

/// Dio HTTP client singleton
class DioClient {
  DioClient._();

  static Dio? _dio;

  /// Get Dio instance
  static Dio get dio {
    _dio ??= _createDio();
    return _dio!;
  }

  /// Create and configure Dio instance
  static Dio _createDio() {
    final dio = Dio(
      BaseOptions(
        baseUrl: Environment.apiBaseUrl,
        connectTimeout:
            const Duration(milliseconds: Environment.connectionTimeout),
        // receiveTimeout: const Duration(milliseconds: Environment.receiveTimeout),
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
      ),
    );

    // Add interceptors
    dio.interceptors.add(_AuthInterceptor());
    dio.interceptors.add(_LoggingInterceptor());
    dio.interceptors.add(_ErrorInterceptor());

    return dio;
  }

  /// Get base URL for WebSocket connections
  static String get baseUrl => Environment.apiBaseUrl;

  /// Reset Dio instance (useful for testing)
  static void reset() {
    _dio = null;
  }
}

/// Authentication interceptor that adds token to requests
class _AuthInterceptor extends Interceptor {
  @override
  void onRequest(RequestOptions options, RequestInterceptorHandler handler) {
    final token = SharedPrefs.getToken();
    if (token != null && token.isNotEmpty) {
      options.headers['Authorization'] = 'Bearer $token';
    }
    handler.next(options);
  }

  @override
  void onError(DioException err, ErrorInterceptorHandler handler) {
    // Handle 401 Unauthorized - redirect to login
    if (err.response?.statusCode == 401) {
      _handleUnauthorized();
    }
    handler.next(err);
  }

  void _handleUnauthorized() async {
    // Clear user session
    await SharedPrefs.clearUserSession();
    // Redirect to login
    Get.offAllNamed(AppRoutes.login);
  }
}

/// Logging interceptor for debugging
class _LoggingInterceptor extends Interceptor {
  @override
  void onRequest(RequestOptions options, RequestInterceptorHandler handler) {
    if (Environment.isDebug) {
      AppLogger.debug(
        'REQUEST[${options.method}] => PATH: ${options.path}',
      );
    }
    handler.next(options);
  }

  @override
  void onResponse(Response response, ResponseInterceptorHandler handler) {
    if (Environment.isDebug) {
      AppLogger.debug(
        'RESPONSE[${response.statusCode}] => PATH: ${response.requestOptions.path}',
      );
    }
    handler.next(response);
  }

  @override
  void onError(DioException err, ErrorInterceptorHandler handler) {
    if (Environment.isDebug) {
      AppLogger.error(
        'ERROR[${err.response?.statusCode}] => PATH: ${err.requestOptions.path}',
        error: err,
      );
    }
    handler.next(err);
  }
}

/// Error interceptor for standardized error handling
class _ErrorInterceptor extends Interceptor {
  @override
  void onError(DioException err, ErrorInterceptorHandler handler) {
    // Transform errors into user-friendly format
    String message = 'Something went wrong';

    switch (err.type) {
      case DioExceptionType.connectionTimeout:
      case DioExceptionType.receiveTimeout:
      case DioExceptionType.sendTimeout:
        message = 'Connection timeout. Please try again.';
        break;
      case DioExceptionType.connectionError:
        message = 'No internet connection.';
        break;
      case DioExceptionType.badResponse:
        message = _getErrorMessage(err.response);
        break;
      case DioExceptionType.cancel:
        message = 'Request cancelled.';
        break;
      default:
        message = 'An unexpected error occurred.';
    }

    // Create a new DioException with the formatted message
    final newError = DioException(
      requestOptions: err.requestOptions,
      response: err.response,
      type: err.type,
      error: message,
      message: message,
    );

    handler.next(newError);
  }

  String _getErrorMessage(Response? response) {
    if (response == null) {
      return 'Server error. Please try again.';
    }

    try {
      final data = response.data;
      if (data is Map<String, dynamic>) {
        return data['detail'] as String? ??
            data['message'] as String? ??
            'Server error';
      }
    } catch (_) {}

    switch (response.statusCode) {
      case 400:
        return 'Bad request.';
      case 401:
        return 'Session expired. Please log in again.';
      case 403:
        return 'Access denied.';
      case 404:
        return 'Resource not found.';
      case 422:
        return 'Invalid data provided.';
      case 500:
        return 'Server error. Please try again later.';
      default:
        return 'Something went wrong.';
    }
  }
}
