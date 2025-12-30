/// Deployment model
library;

/// Deployment data model
class DeploymentModel {
  final int id;
  final int projectId;
  final String status;
  final String? deploymentUrl;
  final String? buildTime;
  final String? size;
  final String? branch;
  final String? commitSha;
  final String? commitMessage;
  final DateTime? startedAt;
  final DateTime? completedAt;
  final DateTime createdAt;

  DeploymentModel({
    required this.id,
    required this.projectId,
    required this.status,
    this.deploymentUrl,
    this.buildTime,
    this.size,
    this.branch,
    this.commitSha,
    this.commitMessage,
    this.startedAt,
    this.completedAt,
    required this.createdAt,
  });

  factory DeploymentModel.fromJson(Map<String, dynamic> json) {
    return DeploymentModel(
      id: json['id'] as int,
      projectId: json['project_id'] as int,
      status: json['status'] as String,
      deploymentUrl: json['deployment_url'] as String?,
      buildTime: json['build_time'] as String?,
      size: json['size'] as String?,
      branch: json['branch'] as String?,
      commitSha: json['commit_sha'] as String?,
      commitMessage: json['commit_message'] as String?,
      startedAt: json['started_at'] != null
          ? DateTime.parse(json['started_at'] as String)
          : null,
      completedAt: json['completed_at'] != null
          ? DateTime.parse(json['completed_at'] as String)
          : null,
      createdAt: DateTime.parse(json['created_at'] as String),
    );
  }

  bool get isSuccess => status == 'success';
  bool get isFailed => status == 'failed';
  bool get isInProgress => status == 'in_progress' || status == 'building';

  String get shortCommitSha =>
      commitSha != null && commitSha!.length > 7 ? commitSha!.substring(0, 7) : (commitSha ?? '');
}
