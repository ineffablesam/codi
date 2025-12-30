/// File tree model
library;

/// File or directory in the project tree
class FileModel {
  final String name;
  final String path;
  final bool isDirectory;
  final int? size;
  final List<FileModel> children;

  FileModel({
    required this.name,
    required this.path,
    this.isDirectory = false,
    this.size,
    this.children = const [],
  });

  factory FileModel.fromJson(Map<String, dynamic> json) {
    return FileModel(
      name: json['name'] as String,
      path: json['path'] as String,
      isDirectory: json['is_directory'] as bool? ?? false,
      size: json['size'] as int?,
      children: (json['children'] as List?)
              ?.map((c) => FileModel.fromJson(c as Map<String, dynamic>))
              .toList() ??
          [],
    );
  }

  /// Get file extension
  String get extension {
    if (isDirectory) return '';
    final parts = name.split('.');
    return parts.length > 1 ? parts.last : '';
  }

  /// Get icon for file type
  String get icon {
    if (isDirectory) return '📁';
    switch (extension) {
      case 'dart':
        return '🎯';
      case 'yaml':
      case 'yml':
        return '⚙️';
      case 'json':
        return '📋';
      case 'md':
        return '📝';
      case 'png':
      case 'jpg':
      case 'jpeg':
      case 'gif':
      case 'svg':
        return '🖼️';
      case 'html':
        return '🌐';
      case 'css':
        return '🎨';
      case 'js':
        return '📜';
      default:
        return '📄';
    }
  }
}
