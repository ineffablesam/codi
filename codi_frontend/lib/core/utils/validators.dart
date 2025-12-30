/// Form validation utilities
library;

/// Form field validators
class Validators {
  Validators._();

  /// Validate required field
  static String? required(String? value, [String fieldName = 'This field']) {
    if (value == null || value.trim().isEmpty) {
      return '$fieldName is required';
    }
    return null;
  }

  /// Validate email format
  static String? email(String? value) {
    if (value == null || value.isEmpty) {
      return 'Email is required';
    }
    final emailRegex = RegExp(r'^[\w-\.]+@([\w-]+\.)+[\w-]{2,4}$');
    if (!emailRegex.hasMatch(value)) {
      return 'Please enter a valid email';
    }
    return null;
  }

  /// Validate minimum length
  static String? minLength(String? value, int length, [String fieldName = 'This field']) {
    if (value == null || value.length < length) {
      return '$fieldName must be at least $length characters';
    }
    return null;
  }

  /// Validate maximum length
  static String? maxLength(String? value, int length, [String fieldName = 'This field']) {
    if (value != null && value.length > length) {
      return '$fieldName cannot exceed $length characters';
    }
    return null;
  }

  /// Validate project name (alphanumeric with dashes)
  static String? projectName(String? value) {
    if (value == null || value.trim().isEmpty) {
      return 'Project name is required';
    }
    if (value.length < 3) {
      return 'Project name must be at least 3 characters';
    }
    if (value.length > 50) {
      return 'Project name cannot exceed 50 characters';
    }
    final nameRegex = RegExp(r'^[a-zA-Z][a-zA-Z0-9-_]*$');
    if (!nameRegex.hasMatch(value)) {
      return 'Project name must start with a letter and contain only letters, numbers, dashes, or underscores';
    }
    return null;
  }

  /// Combine multiple validators
  static String? combine(String? value, List<String? Function(String?)> validators) {
    for (final validator in validators) {
      final error = validator(value);
      if (error != null) {
        return error;
      }
    }
    return null;
  }
}
