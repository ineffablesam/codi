/// Service for managing backend provider connections (Supabase, Firebase)
library;

import 'package:get/get.dart';

import '../../../core/api/api_client.dart';
import '../../../shared/widgets/codi_in_app_browser.dart';

/// Backend connection status
class BackendConnectionStatus {
  final String provider;
  final bool isConnected;
  final String? organizationId;
  final String? connectedAt;

  BackendConnectionStatus({
    required this.provider,
    required this.isConnected,
    this.organizationId,
    this.connectedAt,
  });

  factory BackendConnectionStatus.fromJson(Map<String, dynamic> json) {
    return BackendConnectionStatus(
      provider: json['provider'] ?? '',
      isConnected: json['is_connected'] ?? false,
      organizationId: json['organization_id'],
      connectedAt: json['connected_at'],
    );
  }
}

/// Organization/project from backend provider
class BackendOrganization {
  final String id;
  final String name;
  final String provider;

  BackendOrganization({
    required this.id,
    required this.name,
    required this.provider,
  });

  factory BackendOrganization.fromJson(Map<String, dynamic> json) {
    return BackendOrganization(
      id: json['id'] ?? '',
      name: json['name'] ?? 'Unnamed',
      provider: json['provider'] ?? '',
    );
  }
}

/// Service for connecting to backend providers via OAuth
class BackendConnectionService extends GetxService {
  /// Check if a provider is connected
  Future<BackendConnectionStatus> checkConnectionStatus(String provider) async {
    try {
      final response = await ApiClient.get<Map<String, dynamic>>(
        '/backend/status/$provider',
      );
      if (response.success && response.data != null) {
        return BackendConnectionStatus.fromJson(response.data!);
      }
      return BackendConnectionStatus(provider: provider, isConnected: false);
    } catch (e) {
      return BackendConnectionStatus(provider: provider, isConnected: false);
    }
  }

  /// Start OAuth flow for a provider using in-app browser
  /// Opens Codi branded browser for user to authorize
  Future<bool> connectProvider(String provider) async {
    try {
      // Get authorization URL from backend
      final response = await ApiClient.get<Map<String, dynamic>>(
        '/backend/connect/$provider',
      );
      
      if (!response.success || response.data == null) return false;
      
      final authUrl = response.data!['authorization_url'] as String?;
      final state = response.data!['state'] as String?;

      if (authUrl == null) return false;

      // Determine callback URL pattern based on provider
      final callbackPattern = '/backend/callback/$provider';

      // Open OAuth in in-app browser
      final code = await CodiInAppBrowser.openOAuth(
        authUrl: authUrl,
        callbackUrlPattern: callbackPattern,
        title: 'Connect ${_getProviderName(provider)}',
      );

      if (code != null) {
        // Exchange code for tokens via backend
        await ApiClient.post<Map<String, dynamic>>(
          '/backend/callback/$provider',
          data: {'code': code, 'state': state},
        );
        return true;
      }
      return false;
    } catch (e) {
      return false;
    }
  }

  String _getProviderName(String provider) {
    switch (provider) {
      case 'supabase':
        return 'Supabase';
      case 'firebase':
        return 'Firebase';
      default:
        return provider;
    }
  }

  /// Disconnect a provider
  Future<bool> disconnectProvider(String provider) async {
    try {
      final response = await ApiClient.delete<Map<String, dynamic>>(
        '/backend/disconnect/$provider',
      );
      return response.success;
    } catch (e) {
      return false;
    }
  }

  /// List organizations/projects for a connected provider
  Future<List<BackendOrganization>> listOrganizations(String provider) async {
    try {
      final response = await ApiClient.get<List<dynamic>>(
        '/backend/organizations',
        queryParameters: {'provider': provider},
      );
      if (response.success && response.data != null) {
        return response.data!
            .map((e) => BackendOrganization.fromJson(e as Map<String, dynamic>))
            .toList();
      }
      return [];
    } catch (e) {
      return [];
    }
  }

  /// Provision backend for a project (Supabase or Firebase)
  Future<Map<String, dynamic>?> provisionBackend({
    required int projectId,
    required String provider,
    String? organizationId, // For Supabase
    String? firebaseProjectId, // For Firebase
  }) async {
    try {
      final response = await ApiClient.post<Map<String, dynamic>>(
        '/backend/provision',
        data: {
          'project_id': projectId,
          'provider': provider,
          if (organizationId != null) 'organization_id': organizationId,
          if (firebaseProjectId != null) 'firebase_project_id': firebaseProjectId,
        },
      );
      return response.data;
    } catch (e) {
      return null;
    }
  }

  /// Configure Serverpod manually
  Future<bool> configureServerpod({
    required int projectId,
    required String serverUrl,
    String? apiKey,
  }) async {
    try {
      final response = await ApiClient.post<Map<String, dynamic>>(
        '/backend/serverpod/configure',
        data: {
          'project_id': projectId,
          'server_url': serverUrl,
          if (apiKey != null) 'api_key': apiKey,
        },
      );
      return response.success;
    } catch (e) {
      return false;
    }
  }

  /// Get backend config for a project
  Future<Map<String, dynamic>?> getProjectBackendConfig(int projectId) async {
    try {
      final response = await ApiClient.get<Map<String, dynamic>>(
        '/backend/project/$projectId/config',
      );
      return response.data;
    } catch (e) {
      return null;
    }
  }
}

