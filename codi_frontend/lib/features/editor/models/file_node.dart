/// File node model for code editor file tree
library;

import 'package:get/get.dart';

/// Represents a file or directory in the repository tree
class FileNode {
  final String path;
  final String name;
  final String type; // 'file' or 'directory'
  final int? size;
  final String? sha;
  final bool modified;
  final List<FileNode> children;
  final RxBool isExpanded;

  FileNode({
    required this.path,
    required this.name,
    required this.type,
    this.size,
    this.sha,
    this.modified = false,
    List<FileNode>? children,
    bool expanded = false,
  })  : children = children ?? [],
        isExpanded = expanded.obs;

  /// Create FileNode from JSON
  factory FileNode.fromJson(Map<String, dynamic> json) {
    final path = json['path'] as String;
    final name = path.split('/').last;
    final type = json['type'] == 'directory' ? 'directory' : 'file';

    return FileNode(
      path: path,
      name: name,
      type: type,
      size: json['size'] as int?,
      sha: json['sha'] as String?,
      modified: json['modified'] as bool? ?? false,
      children: (json['children'] as List?)
              ?.map((child) => FileNode.fromJson(child as Map<String, dynamic>))
              .toList() ??
          [],
    );
  }

  /// Check if this is a file
  bool get isFile => type == 'file';

  /// Check if this is a directory
  bool get isDirectory => type == 'directory';

  /// Get file extension
  String get extension {
    if (isDirectory) return '';
    final parts = name.split('.');
    return parts.length > 1 ? parts.last.toLowerCase() : '';
  }

  /// Get icon for file based on extension
  String get icon {
    if (isDirectory) {
      return isExpanded.value ? '📂' : '📁';
    }

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
      case 'webp':
        return '🖼️';
      case 'svg':
        return '🎨';
      case 'lock':
        return '🔒';
      case 'gradle':
        return '🐘';
      case 'kt':
        return '🟣';
      case 'swift':
        return '🔶';
      case 'xml':
        return '📰';
      case 'html':
        return '🌐';
      case 'css':
        return '🎨';
      case 'js':
      case 'ts':
        return '📜';
      default:
        return '📄';
    }
  }

  /// Create a copy with modifications
  FileNode copyWith({
    String? path,
    String? name,
    String? type,
    int? size,
    String? sha,
    bool? modified,
    List<FileNode>? children,
    bool? expanded,
  }) {
    return FileNode(
      path: path ?? this.path,
      name: name ?? this.name,
      type: type ?? this.type,
      size: size ?? this.size,
      sha: sha ?? this.sha,
      modified: modified ?? this.modified,
      children: children ?? this.children,
      expanded: expanded ?? isExpanded.value,
    );
  }
}
