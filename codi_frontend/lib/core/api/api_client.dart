/// High-level API client
library;

import 'package:dio/dio.dart';

import 'dio_client.dart';

/// API response wrapper
class ApiResponse<T> {
  final T? data;
  final String? error;
  final bool success;

  ApiResponse({
    this.data,
    this.error,
    this.success = true,
  });

  factory ApiResponse.success(T data) => ApiResponse(data: data, success: true);
  
  factory ApiResponse.failure(String error) => ApiResponse(error: error, success: false);
}

/// High-level API client wrapping Dio
class ApiClient {
  ApiClient._();

  static Dio get _dio => DioClient.dio;

  /// GET request
  static Future<ApiResponse<T>> get<T>(
    String path, {
    Map<String, dynamic>? queryParameters,
    T Function(dynamic)? fromJson,
  }) async {
    try {
      final response = await _dio.get(
        path,
        queryParameters: queryParameters,
      );
      
      if (fromJson != null) {
        return ApiResponse.success(fromJson(response.data));
      }
      return ApiResponse.success(response.data as T);
    } on DioException catch (e) {
      return ApiResponse.failure(e.message ?? 'Request failed');
    }
  }

  /// POST request
  static Future<ApiResponse<T>> post<T>(
    String path, {
    dynamic data,
    Map<String, dynamic>? queryParameters,
    T Function(dynamic)? fromJson,
  }) async {
    try {
      final response = await _dio.post(
        path,
        data: data,
        queryParameters: queryParameters,
      );
      
      if (fromJson != null) {
        return ApiResponse.success(fromJson(response.data));
      }
      return ApiResponse.success(response.data as T);
    } on DioException catch (e) {
      return ApiResponse.failure(e.message ?? 'Request failed');
    }
  }

  /// PUT request
  static Future<ApiResponse<T>> put<T>(
    String path, {
    dynamic data,
    Map<String, dynamic>? queryParameters,
    T Function(dynamic)? fromJson,
  }) async {
    try {
      final response = await _dio.put(
        path,
        data: data,
        queryParameters: queryParameters,
      );
      
      if (fromJson != null) {
        return ApiResponse.success(fromJson(response.data));
      }
      return ApiResponse.success(response.data as T);
    } on DioException catch (e) {
      return ApiResponse.failure(e.message ?? 'Request failed');
    }
  }

  /// PATCH request
  static Future<ApiResponse<T>> patch<T>(
    String path, {
    dynamic data,
    Map<String, dynamic>? queryParameters,
    T Function(dynamic)? fromJson,
  }) async {
    try {
      final response = await _dio.patch(
        path,
        data: data,
        queryParameters: queryParameters,
      );
      
      if (fromJson != null) {
        return ApiResponse.success(fromJson(response.data));
      }
      return ApiResponse.success(response.data as T);
    } on DioException catch (e) {
      return ApiResponse.failure(e.message ?? 'Request failed');
    }
  }

  /// DELETE request
  static Future<ApiResponse<T>> delete<T>(
    String path, {
    dynamic data,
    Map<String, dynamic>? queryParameters,
    T Function(dynamic)? fromJson,
  }) async {
    try {
      final response = await _dio.delete(
        path,
        data: data,
        queryParameters: queryParameters,
      );
      
      if (fromJson != null) {
        return ApiResponse.success(fromJson(response.data));
      }
      return ApiResponse.success(response.data as T);
    } on DioException catch (e) {
      return ApiResponse.failure(e.message ?? 'Request failed');
    }
  }
}
