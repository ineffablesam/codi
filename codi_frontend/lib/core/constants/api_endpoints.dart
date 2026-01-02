/// API endpoints constants
library;

/// API endpoint definitions
class ApiEndpoints {
  ApiEndpoints._();

  // Auth endpoints
  static const String authGitHub = '/auth/github';
  static const String authGitHubCallback = '/auth/github/callback';
  static const String authMe = '/auth/me';
  static const String authLogout = '/auth/logout';

  // Projects endpoints
  static const String projects = '/projects';
  static String projectById(int id) => '/projects/$id';
  static String projectFiles(int id) => '/projects/$id/files';
  static String projectFile(int id, String path) => '/projects/$id/files/$path';

  // File operations endpoints (Code Editor)
  static String projectFilesTree(int id) => '/projects/$id/files/tree';
  static String projectFilesRead(int id) => '/projects/$id/files/read';
  static String projectFilesUpdate(int id) => '/projects/$id/files/update';
  static String projectCommits(int id) => '/projects/$id/commits';
  static String projectCommitsMulti(int id) => '/projects/$id/commits/multi';
  static String projectBranches(int id) => '/projects/$id/branches';

  // Agents endpoints
  static String agentTask(int projectId) => '/agents/$projectId/task';
  static String agentTaskStatus(int projectId, String taskId) =>
      '/agents/$projectId/task/$taskId';
  static String agentHistory(int projectId) => '/agents/$projectId/history';
  static String agentWebSocket(int projectId) => '/agents/$projectId/ws';

  // Health endpoints
  static const String health = '/health';
  static const String healthReady = '/health/ready';
}

