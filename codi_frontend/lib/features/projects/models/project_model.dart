/// Project model
library;

/// Project data model
class ProjectModel {
  final int id;
  final String name;
  final String? description;
  final String? githubRepoFullName;
  final String? githubRepoUrl;
  final String? githubCurrentBranch;
  final String status;
  final String? deploymentUrl;
  final String? lastBuildStatus;
  final DateTime? lastBuildAt;
  final DateTime createdAt;
  final DateTime updatedAt;

  // Platform configuration
  final String? platformType;
  final String? framework;
  final String? backendType;
  final String? deploymentPlatform;

  // Optional owner info
  final int? ownerId;
  final String? ownerUsername;
  final String? ownerAvatarUrl;

  ProjectModel({
    required this.id,
    required this.name,
    this.description,
    this.githubRepoFullName,
    this.githubRepoUrl,
    this.githubCurrentBranch,
    this.status = 'active',
    this.deploymentUrl,
    this.lastBuildStatus,
    this.lastBuildAt,
    required this.createdAt,
    required this.updatedAt,
    this.platformType,
    this.framework,
    this.backendType,
    this.deploymentPlatform,
    this.ownerId,
    this.ownerUsername,
    this.ownerAvatarUrl,
  });

  factory ProjectModel.fromJson(Map<String, dynamic> json) {
    return ProjectModel(
      id: json['id'] as int,
      name: json['name'] as String,
      description: json['description'] as String?,
      githubRepoFullName: json['github_repo_full_name'] as String?,
      githubRepoUrl: json['github_repo_url'] as String?,
      githubCurrentBranch: json['github_current_branch'] as String?,
      status: json['status'] as String? ?? 'active',
      deploymentUrl: json['deployment_url'] as String?,
      lastBuildStatus: json['last_build_status'] as String?,
      lastBuildAt: json['last_build_at'] != null
          ? DateTime.parse(json['last_build_at'] as String)
          : null,
      createdAt: DateTime.parse(json['created_at'] as String),
      updatedAt: DateTime.parse(json['updated_at'] as String),
      platformType: json['platform_type'] as String?,
      framework: json['framework'] as String?,
      backendType: json['backend_type'] as String?,
      deploymentPlatform: json['deployment_platform'] as String?,
      ownerId: json['owner_id'] as int?,
      ownerUsername: json['owner_username'] as String?,
      ownerAvatarUrl: json['owner_avatar_url'] as String?,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'description': description,
      'github_repo_full_name': githubRepoFullName,
      'github_repo_url': githubRepoUrl,
      'github_current_branch': githubCurrentBranch,
      'status': status,
      'deployment_url': deploymentUrl,
      'last_build_status': lastBuildStatus,
      'last_build_at': lastBuildAt?.toIso8601String(),
      'created_at': createdAt.toIso8601String(),
      'updated_at': updatedAt.toIso8601String(),
      'platform_type': platformType,
      'framework': framework,
      'backend_type': backendType,
      'deployment_platform': deploymentPlatform,
    };
  }

  bool get hasDeployment => deploymentUrl != null && deploymentUrl!.isNotEmpty;
  bool get isBuilding => status == 'building';
  bool get isDeploying => status == 'deploying';
  bool get isActive => status == 'active';
  
  String get frameworkLabel {
    switch (framework) {
      case 'flutter': return 'Flutter';
      case 'react': return 'React';
      case 'nextjs': return 'Next.js';
      case 'react_native': return 'React Native';
      default: return 'Flutter';
    }
  }
}

/// Request model for creating a project
class CreateProjectRequest {
  final String name;
  final String? description;
  final bool isPrivate;
  final String platformType;
  final String framework;
  final String? backendType;
  final String? deploymentPlatform;

  CreateProjectRequest({
    required this.name,
    this.description,
    this.isPrivate = false,
    this.platformType = 'mobile',
    this.framework = 'flutter',
    this.backendType,
    this.deploymentPlatform,
  });

  Map<String, dynamic> toJson() {
    return {
      'name': name,
      'description': description,
      'is_private': isPrivate,
      'platform_type': platformType,
      'framework': framework,
      'backend_type': backendType,
      'deployment_platform': deploymentPlatform,
    };
  }
}

