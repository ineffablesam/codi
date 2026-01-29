class EnvironmentVariable {
  final int id;
  final int projectId;
  final String key;
  final String value;
  final String context;
  final bool isSecret;
  final String? description;
  final DateTime createdAt;
  final DateTime updatedAt;

  EnvironmentVariable({
    required this.id,
    required this.projectId,
    required this.key,
    required this.value,
    required this.context,
    required this.isSecret,
    this.description,
    required this.createdAt,
    required this.updatedAt,
  });

  factory EnvironmentVariable.fromJson(Map<String, dynamic> json) {
    return EnvironmentVariable(
      id: json['id'],
      projectId: json['project_id'],
      key: json['key'],
      value: json['value'],
      context: json['context'],
      isSecret: json['is_secret'],
      description: json['description'],
      createdAt: DateTime.parse(json['created_at']),
      updatedAt: DateTime.parse(json['updated_at']),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'project_id': projectId,
      'key': key,
      'value': value,
      'context': context,
      'is_secret': isSecret,
      'description': description,
      'created_at': createdAt.toIso8601String(),
      'updated_at': updatedAt.toIso8601String(),
    };
  }
}

class EnvironmentVariableCreate {
  final String key;
  final String value;
  final String context;
  final bool isSecret;
  final String? description;

  EnvironmentVariableCreate({
    required this.key,
    required this.value,
    this.context = 'general',
    this.isSecret = false,
    this.description,
  });

  Map<String, dynamic> toJson() {
    return {
      'key': key,
      'value': value,
      'context': context,
      'is_secret': isSecret,
      'description': description,
    };
  }
}

class EnvironmentVariableUpdate {
  final String? value;
  final String? context;
  final bool? isSecret;
  final String? description;

  EnvironmentVariableUpdate({
    this.value,
    this.context,
    this.isSecret,
    this.description,
  });

  Map<String, dynamic> toJson() {
    return {
      if (value != null) 'value': value,
      if (context != null) 'context': context,
      if (isSecret != null) 'is_secret': isSecret,
      if (description != null) 'description': description,
    };
  }
}
