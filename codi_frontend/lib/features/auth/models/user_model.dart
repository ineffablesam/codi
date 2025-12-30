/// User model
library;

/// User data model
class UserModel {
  final int id;
  final int githubId;
  final String githubUsername;
  final String? email;
  final String? name;
  final String? githubAvatarUrl;
  final bool isActive;
  final DateTime createdAt;
  final DateTime? lastLoginAt;

  UserModel({
    required this.id,
    required this.githubId,
    required this.githubUsername,
    this.email,
    this.name,
    this.githubAvatarUrl,
    this.isActive = true,
    required this.createdAt,
    this.lastLoginAt,
  });

  factory UserModel.fromJson(Map<String, dynamic> json) {
    return UserModel(
      id: json['id'] as int,
      githubId: json['github_id'] as int,
      githubUsername: json['github_username'] as String,
      email: json['email'] as String?,
      name: json['name'] as String?,
      githubAvatarUrl: json['github_avatar_url'] as String?,
      isActive: json['is_active'] as bool? ?? true,
      createdAt: DateTime.parse(json['created_at'] as String),
      lastLoginAt: json['last_login_at'] != null
          ? DateTime.parse(json['last_login_at'] as String)
          : null,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'github_id': githubId,
      'github_username': githubUsername,
      'email': email,
      'name': name,
      'github_avatar_url': githubAvatarUrl,
      'is_active': isActive,
      'created_at': createdAt.toIso8601String(),
      'last_login_at': lastLoginAt?.toIso8601String(),
    };
  }

  String get displayName => name ?? githubUsername;

  String get avatarUrl =>
      githubAvatarUrl ?? 'https://picsum.photos/seed/$githubUsername/200/200';
}

/// Token response from auth
class TokenResponse {
  final String accessToken;
  final String tokenType;
  final int expiresIn;
  final UserModel user;

  TokenResponse({
    required this.accessToken,
    required this.tokenType,
    required this.expiresIn,
    required this.user,
  });

  factory TokenResponse.fromJson(Map<String, dynamic> json) {
    return TokenResponse(
      accessToken: json['access_token'] as String,
      tokenType: json['token_type'] as String,
      expiresIn: json['expires_in'] as int,
      user: UserModel.fromJson(json['user'] as Map<String, dynamic>),
    );
  }
}
