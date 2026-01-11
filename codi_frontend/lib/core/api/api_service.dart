/// API Service for GetX dependency injection
library;

import 'package:dio/dio.dart';
import 'package:get/get.dart' hide Response;

import 'dio_client.dart';

/// API Service wrapper for dependency injection
/// This class provides instance methods that wrap the static ApiClient,
/// allowing it to be injected via GetX.
class ApiService extends GetxService {
  /// Get the base URL for WebSocket connections
  String get baseUrl => DioClient.baseUrl;

  Dio get _dio => DioClient.dio;

  /// GET request
  Future<Response> get(
    String path, {
    Map<String, dynamic>? queryParameters,
  }) async {
    return await _dio.get(path, queryParameters: queryParameters);
  }

  /// POST request
  Future<Response> post(
    String path, {
    dynamic data,
    Map<String, dynamic>? queryParameters,
  }) async {
    return await _dio.post(path, data: data, queryParameters: queryParameters);
  }

  /// PUT request
  Future<Response> put(
    String path, {
    dynamic data,
    Map<String, dynamic>? queryParameters,
  }) async {
    return await _dio.put(path, data: data, queryParameters: queryParameters);
  }

  /// PATCH request
  Future<Response> patch(
    String path, {
    dynamic data,
    Map<String, dynamic>? queryParameters,
  }) async {
    return await _dio.patch(path, data: data, queryParameters: queryParameters);
  }

  /// DELETE request
  Future<Response> delete(
    String path, {
    dynamic data,
    Map<String, dynamic>? queryParameters,
  }) async {
    return await _dio.delete(path,
        data: data, queryParameters: queryParameters);
  }
}
