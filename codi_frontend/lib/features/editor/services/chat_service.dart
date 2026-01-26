import 'package:get/get.dart';
import '../../../core/api/api_client.dart';
import '../models/chat_session_model.dart';
import '../../../core/constants/api_endpoints.dart';

class ChatService extends GetxService {
  Future<List<ChatSession>> getSessions(int projectId, {bool includeArchived = false}) async {
    final response = await ApiClient.get(
      '/chats/projects/$projectId/sessions',
      queryParameters: {'include_archived': includeArchived},
    );

    if (response.success && response.data != null) {
      final list = response.data!['sessions'] as List;
      return list.map((e) => ChatSession.fromJson(e)).toList();
    }
    return [];
  }

  Future<ChatSession?> createSession(int projectId, {String title = 'New Chat'}) async {
    final response = await ApiClient.post(
      '/chats/projects/$projectId/sessions',
      data: {'title': title},
    );

    if (response.success && response.data != null) {
      return ChatSession.fromJson(response.data!);
    }
    return null;
  }

  Future<List<ChatMessage>> getMessages(String sessionId, {int limit = 50}) async {
    final response = await ApiClient.get(
      '/chats/$sessionId/messages',
      queryParameters: {'limit': limit},
    );

    if (response.success && response.data != null) {
      final list = response.data!['messages'] as List;
      return list.map((e) => ChatMessage.fromJson(e)).toList();
    }
    return [];
  }

  Future<bool> deleteSession(String sessionId) async {
    final response = await ApiClient.delete('/chats/$sessionId');
    return response.success;
  }

  Future<bool> archiveSession(String sessionId) async {
    final response = await ApiClient.patch('/chats/$sessionId/archive');
    return response.success;
  }
}
