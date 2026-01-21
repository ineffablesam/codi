import 'package:fluentui_system_icons/fluentui_system_icons.dart';
import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_highlight/flutter_highlight.dart';
import 'package:flutter_highlight/themes/atom-one-dark.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:google_fonts/google_fonts.dart';

/// Collapsible tool execution card for mobile-optimized chat
/// - Collapsed by default
/// - Shows tool icon + name in header
/// - Expandable to show details/code
class ToolExecutionCard extends StatefulWidget {
  final String toolName;
  final String? details;
  final String? filePath;
  final bool initiallyExpanded;
  final VoidCallback? onExpand;

  const ToolExecutionCard({
    super.key,
    required this.toolName,
    this.details,
    this.filePath,
    this.initiallyExpanded = false,
    this.onExpand,
  });

  @override
  State<ToolExecutionCard> createState() => _ToolExecutionCardState();
}

class _ToolExecutionCardState extends State<ToolExecutionCard>
    with SingleTickerProviderStateMixin {
  late bool _isExpanded;
  late AnimationController _controller;
  late Animation<double> _iconRotation;

  @override
  void initState() {
    super.initState();
    _isExpanded = widget.initiallyExpanded;
    _controller = AnimationController(
      duration: const Duration(milliseconds: 200),
      vsync: this,
    );
    _iconRotation = Tween<double>(begin: 0, end: 0.5).animate(
      CurvedAnimation(parent: _controller, curve: Curves.easeInOut),
    );
    if (_isExpanded) _controller.forward();
  }

  @override
  void didUpdateWidget(ToolExecutionCard oldWidget) {
    super.didUpdateWidget(oldWidget);
    // Allow external collapse
    if (!widget.initiallyExpanded && _isExpanded) {
      setState(() => _isExpanded = false);
      _controller.reverse();
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _toggle() {
    setState(() => _isExpanded = !_isExpanded);
    if (_isExpanded) {
      _controller.forward();
      widget.onExpand?.call();
    } else {
      _controller.reverse();
    }
  }

  IconData _getToolIcon() {
    switch (widget.toolName) {
      case 'read_file':
        return FluentIcons.document_text_24_regular;
      case 'write_file':
        return FluentIcons.document_add_24_regular;
      case 'edit_file':
        return FluentIcons.document_edit_24_regular;
      case 'list_files':
        return FluentIcons.folder_open_24_regular;
      case 'search_files':
        return FluentIcons.search_24_regular;
      case 'run_bash':
        return Icons.terminal_outlined;
      case 'run_python':
        return FluentIcons.code_24_regular;
      case 'git_commit':
        return Icons.commit_outlined;
      case 'docker_preview':
        return FluentIcons.cloud_arrow_up_24_regular;
      case 'initial_deploy':
        return FluentIcons.rocket_24_regular;
      default:
        return FluentIcons.wrench_24_regular;
    }
  }

  String _getDisplayName() {
    // Convert snake_case to Title Case
    return widget.toolName
        .split('_')
        .map(
            (w) => w.isNotEmpty ? '${w[0].toUpperCase()}${w.substring(1)}' : '')
        .join(' ');
  }

  String? _detectLanguage() {
    final path = widget.filePath?.toLowerCase() ?? '';
    if (path.endsWith('.dart')) return 'dart';
    if (path.endsWith('.py')) return 'python';
    if (path.endsWith('.js') || path.endsWith('.jsx')) return 'javascript';
    if (path.endsWith('.ts') || path.endsWith('.tsx')) return 'typescript';
    if (path.endsWith('.json')) return 'json';
    if (path.endsWith('.yaml') || path.endsWith('.yml')) return 'yaml';
    if (path.endsWith('.md')) return 'markdown';
    if (path.endsWith('.html')) return 'html';
    if (path.endsWith('.css')) return 'css';
    if (path.endsWith('.sh')) return 'bash';
    return null;
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(bottom: 4.h, left: 40.w),
      child: Container(
        decoration: BoxDecoration(
          color: Colors.grey[900],
          borderRadius: BorderRadius.circular(6.r),
          border: Border.all(color: Colors.grey[800]!, width: 0.5),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            // Header - always visible
            InkWell(
              onTap: widget.details != null ? _toggle : null,
              borderRadius: BorderRadius.circular(6.r),
              child: Padding(
                padding: EdgeInsets.symmetric(horizontal: 8.w, vertical: 6.h),
                child: Row(
                  children: [
                    Icon(
                      _getToolIcon(),
                      size: 14.r,
                      color: Colors.blue[400],
                    ),
                    SizedBox(width: 6.w),
                    Expanded(
                      child: Text(
                        widget.filePath ?? _getDisplayName(),
                        style: GoogleFonts.jetBrainsMono(
                          fontSize: 10.sp,
                          color: Colors.grey[400],
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                    if (widget.details != null)
                      RotationTransition(
                        turns: _iconRotation,
                        child: Icon(
                          FluentIcons.chevron_down_24_regular,
                          size: 12.r,
                          color: Colors.grey[600],
                        ),
                      ),
                  ],
                ),
              ),
            ),
            // Expandable content
            AnimatedSize(
              duration: const Duration(milliseconds: 200),
              curve: Curves.easeInOut,
              child: _isExpanded && widget.details != null
                  ? Container(
                      width: double.infinity,
                      padding: EdgeInsets.all(8.r),
                      decoration: BoxDecoration(
                        color: Colors.grey[850],
                        borderRadius: BorderRadius.only(
                          bottomLeft: Radius.circular(5.r),
                          bottomRight: Radius.circular(5.r),
                        ),
                      ),
                      child: _buildContent(),
                    )
                  : const SizedBox.shrink(),
            ),
          ],
        ),
      ),
    ).animate().fadeIn(duration: 150.ms);
  }

  Widget _buildContent() {
    final language = _detectLanguage();
    final hasCode = language != null &&
        widget.details != null &&
        widget.details!.contains('\n');

    if (hasCode) {
      // Syntax highlighted code
      return ClipRRect(
        borderRadius: BorderRadius.circular(6.r),
        child: HighlightView(
          widget.details!,
          language: language,
          theme: atomOneDarkTheme,
          padding: EdgeInsets.all(10.r),
          textStyle: GoogleFonts.jetBrainsMono(
            fontSize: 11.sp,
          ),
        ),
      );
    } else {
      // Plain text
      return Text(
        widget.details ?? '',
        style: GoogleFonts.jetBrainsMono(
          fontSize: 11.sp,
          color: Colors.grey[400],
        ),
      );
    }
  }
}
