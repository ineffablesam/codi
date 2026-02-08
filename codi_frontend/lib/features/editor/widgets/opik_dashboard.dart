/// Premium Opik dashboard widget - Updated with exact Opik brand colors
/// Powered by Comet - Opik
library;

import 'package:flutter/material.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:flutter_svg/svg.dart';
import 'package:get/get.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';
import 'package:url_launcher/url_launcher.dart';

import '../models/opik_models.dart';
import '../services/opik_service.dart';

/// Enhanced Opik dashboard with exact brand colors from comet.com
class OpikDashboard extends StatefulWidget {
  final int? projectId;
  final String? initialFilteredSessionId;

  const OpikDashboard({
    super.key,
    this.projectId,
    this.initialFilteredSessionId,
  });

  @override
  State<OpikDashboard> createState() => _OpikDashboardState();
}

class _OpikDashboardState extends State<OpikDashboard>
    with SingleTickerProviderStateMixin {
  bool _isLoading = true;
  ProjectStatsModel? _stats;
  List<TraceModel> _traces = [];
  String? _selectedTraceType;
  TraceModel? _selectedTrace;
  late AnimationController _animationController;
  late Animation<double> _fadeAnimation;

  // View mode: 'grouped', 'summary', 'advanced'
  String _viewMode = 'grouped';
  GroupedTracesResponse? _groupedTraces;
  String? _filteredSessionId;

  // ============================================================================
  // EXACT OPIK BRAND COLORS FROM WEBSITE
  // ============================================================================

  // Primary Brand Colors
  static const Color _primaryPurple = Color(0xFF6366F1);
  static const Color _accentOrange = Color(0xFFFF8C42);

  // Background Colors
  static const Color _backgroundDark = Color(0xFF0A0F1E);
  static const Color _backgroundCard = Color(0xFF131B2E);
  static const Color _backgroundElevated = Color(0xFF1A2742);
  static const Color _backgroundHover = Color(0xFF1E2D47);

  // Text Colors
  static const Color _textPrimary = Color(0xFFFFFFFF);
  static const Color _textSecondary = Color(0xFFB8C4D8);
  static const Color _textTertiary = Color(0xFF7E8BA3);

  // Status Colors
  static const Color _success = Color(0xFF10B981);
  static const Color _warning = Color(0xFFF59E0B);
  static const Color _error = Color(0xFFEF4444);
  static const Color _info = Color(0xFF3B82F6);

  // Border Colors
  static const Color _borderSubtle = Color(0x1AFFFFFF);
  static const Color _borderDefault = Color(0x33FFFFFF);

  @override
  void initState() {
    super.initState();
    _filteredSessionId = widget.initialFilteredSessionId;
    _animationController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 600),
    );
    _fadeAnimation = CurvedAnimation(
      parent: _animationController,
      curve: Curves.easeInOut,
    );
    _loadData();
  }

  @override
  void dispose() {
    _animationController.dispose();
    super.dispose();
  }

  Future<void> _loadData() async {
    if (widget.projectId == null) {
      setState(() => _isLoading = false);
      return;
    }

    setState(() => _isLoading = true);

    try {
      // Load project stats
      final stats = await OpikService.getProjectStats(widget.projectId!);

      // Load grouped traces (for grouped view)
      final grouped = await OpikService.getGroupedTraces(widget.projectId!);

      // Load regular traces (for summary/advanced views)
      final tracesResponse = await OpikService.getProjectTraces(
        projectId: widget.projectId!,
        traceType: _selectedTraceType,
      );

      setState(() {
        _stats = stats;
        _groupedTraces = grouped;
        _traces = tracesResponse?.traces ?? [];
        _isLoading = false;
      });

      _animationController.forward();
    } catch (e) {
      setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (widget.projectId == null) {
      return _buildEmptyProjectState();
    }

    return Container(
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [_backgroundDark, _backgroundElevated],
        ),
      ),
      child: Column(
        children: [
          _buildPremiumHeader(),
          10.verticalSpace,
          if (_stats != null) _buildStatsCards(_stats!),
          SizedBox(height: 12.h),
          _buildEnhancedFilters(),
          SizedBox(height: 10.h),
          Expanded(
            child: _isLoading ? _buildLoadingState() : _buildViewContent(),
          ),
        ],
      ),
    );
  }

  Widget _buildEmptyProjectState() {
    return Container(
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [_backgroundDark, _backgroundElevated],
        ),
      ),
      child: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              padding: EdgeInsets.all(20.r),
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                gradient: const LinearGradient(
                  colors: [_primaryPurple, Color(0xFF8B5CF6)],
                ),
                boxShadow: [
                  BoxShadow(
                    color: _primaryPurple.withOpacity(0.4),
                    blurRadius: 24,
                    spreadRadius: 4,
                  ),
                ],
              ),
              child: Icon(
                LucideIcons.activity,
                size: 36.sp,
                color: _textPrimary,
              ),
            ),
            SizedBox(height: 20.h),
            Text(
              'AI Operations Dashboard',
              style: Get.textTheme.titleLarge?.copyWith(
                color: _textPrimary,
                fontWeight: FontWeight.bold,
                fontSize: 18.sp,
              ),
            ),
            SizedBox(height: 8.h),
            Text(
              'Select a project to view Opik traces',
              style: Get.textTheme.bodyMedium?.copyWith(
                color: _textSecondary,
                fontSize: 12.sp,
              ),
            ),
            SizedBox(height: 24.h),
            _buildPremiumPoweredByBadge(),
          ],
        ),
      ),
    );
  }

  Widget _buildPremiumHeader() {
    return Container(
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [_primaryPurple, Color(0xFF8B5CF6)],
        ),
        boxShadow: [
          BoxShadow(
            color: _primaryPurple.withOpacity(0.3),
            blurRadius: 16,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Column(
        children: [
          Padding(
            padding: EdgeInsets.fromLTRB(16.w, 14.h, 16.w, 12.h),
            child: Row(
              children: [
                Container(
                  padding: EdgeInsets.all(10.r),
                  decoration: BoxDecoration(
                    color: _textPrimary.withOpacity(0.2),
                    borderRadius: BorderRadius.circular(10.r),
                    border: Border.all(
                      color: _textPrimary.withOpacity(0.3),
                      width: 1.5,
                    ),
                  ),
                  child: Icon(
                    LucideIcons.activity,
                    size: 20.sp,
                    color: _textPrimary,
                  ),
                ),
                SizedBox(width: 12.w),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'AI Operations',
                        style: Get.textTheme.titleMedium?.copyWith(
                          fontWeight: FontWeight.bold,
                          color: _textPrimary,
                          fontSize: 15.sp,
                        ),
                      ),
                      SizedBox(height: 3.h),
                      Text(
                        'Real-time trace analytics',
                        style: Get.textTheme.bodySmall?.copyWith(
                          color: _textPrimary.withOpacity(0.8),
                          fontSize: 11.sp,
                        ),
                      ),
                    ],
                  ),
                ),
                SizedBox(width: 8.w),
                _buildPremiumPoweredByBadge(),
              ],
            ),
          ),
          Container(
            height: 2.h,
            decoration: BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                colors: [
                  _textPrimary.withOpacity(0.15),
                  Colors.transparent,
                ],
              ),
            ),
          ),
          // View mode toggle
          Padding(
            padding: EdgeInsets.symmetric(horizontal: 16.w, vertical: 12.h),
            child: Row(
              children: [
                _buildViewModeButton('Prompts', 'grouped', LucideIcons.layers),
                SizedBox(width: 8.w),
                _buildViewModeButton('Summary', 'summary', LucideIcons.list),
                SizedBox(width: 8.w),
                _buildViewModeButton('Advanced', 'advanced', LucideIcons.code),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildViewModeButton(String label, String mode, IconData icon) {
    final isSelected = _viewMode == mode;
    return Expanded(
      child: Material(
        color: isSelected ? _textPrimary.withOpacity(0.15) : Colors.transparent,
        borderRadius: BorderRadius.circular(8.r),
        child: InkWell(
          onTap: () => setState(() => _viewMode = mode),
          borderRadius: BorderRadius.circular(8.r),
          child: Container(
            padding: EdgeInsets.symmetric(vertical: 8.h, horizontal: 12.w),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(8.r),
              border: Border.all(
                color: isSelected
                    ? _textPrimary.withOpacity(0.3)
                    : _textPrimary.withOpacity(0.1),
                width: 1,
              ),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(
                  icon,
                  size: 14.sp,
                  color: isSelected ? _textPrimary : _textSecondary,
                ),
                SizedBox(width: 6.w),
                Text(
                  label,
                  style: Get.textTheme.bodySmall?.copyWith(
                    color: isSelected ? _textPrimary : _textSecondary,
                    fontSize: 11.sp,
                    fontWeight:
                        isSelected ? FontWeight.w600 : FontWeight.normal,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildPremiumPoweredByBadge() {
    return InkWell(
      onTap: () =>
          launchUrl(Uri.parse('https://www.comet.com/site/products/opik/')),
      borderRadius: BorderRadius.circular(18.r),
      child: Container(
        padding: EdgeInsets.symmetric(horizontal: 8.w, vertical: 4.h),
        decoration: BoxDecoration(
          gradient: LinearGradient(
            colors: [
              _textPrimary.withOpacity(0.2),
              _textPrimary.withOpacity(0.08),
            ],
          ),
          borderRadius: BorderRadius.circular(18.r),
          border: Border.all(
            color: _textPrimary.withOpacity(0.35),
            width: 1.2,
          ),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.15),
              blurRadius: 6,
              offset: const Offset(0, 2),
            ),
          ],
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              'Supercharged by',
              style: Get.textTheme.bodySmall?.copyWith(
                color: _textPrimary.withOpacity(0.85),
                fontSize: 9.5.sp,
                fontWeight: FontWeight.w600,
              ),
            ),
            SizedBox(width: 5.w),
            Container(
              padding: EdgeInsets.symmetric(horizontal: 2.w, vertical: 2.h),
              decoration: BoxDecoration(
                color: _textPrimary.withOpacity(0.15),
                borderRadius: BorderRadius.circular(9.r),
              ),
              child: Row(
                children: [
                  SvgPicture.asset(
                    'assets/images/opik-logo.svg',
                    width: 18.w,
                    height: 18.h,
                  ),
                ],
              ),
            ),
            SizedBox(width: 5.w),
            Icon(
              LucideIcons.externalLink,
              size: 11.sp,
              color: _textPrimary.withOpacity(0.8),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildStatsCards(ProjectStatsModel stats) {
    return Container(
      padding: EdgeInsets.symmetric(horizontal: 12.w, vertical: 4.h),
      child: IntrinsicHeight(
        child: Row(
          children: [
            Expanded(
              child: _buildPremiumStatCard(
                'Traces',
                stats.totalTraces.toString(),
                LucideIcons.activity,
                _primaryPurple,
              ),
            ),
            SizedBox(width: 8.w),
            Expanded(
              child: _buildPremiumStatCard(
                'Success',
                stats.successRateText,
                LucideIcons.circleCheck,
                _success,
              ),
            ),
            SizedBox(width: 8.w),
            Expanded(
              child: _buildPremiumStatCard(
                'Duration',
                stats.averageDurationText,
                LucideIcons.clock,
                _info,
              ),
            ),
            SizedBox(width: 8.w),
            Expanded(
              child: _buildPremiumStatCard(
                'Evals',
                stats.totalEvaluations.toString(),
                LucideIcons.chartBar,
                _accentOrange,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildPremiumStatCard(
    String label,
    String value,
    IconData icon,
    Color accentColor,
  ) {
    return Container(
      padding: EdgeInsets.all(11.r),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [_backgroundCard, _backgroundElevated],
        ),
        borderRadius: BorderRadius.circular(12.r),
        border: Border.all(
          color: accentColor.withOpacity(0.35),
          width: 1.2,
        ),
        boxShadow: [
          BoxShadow(
            color: accentColor.withOpacity(0.15),
            blurRadius: 12,
            offset: const Offset(0, 3),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                padding: EdgeInsets.all(6.r),
                decoration: BoxDecoration(
                  color: accentColor.withOpacity(0.18),
                  borderRadius: BorderRadius.circular(8.r),
                ),
                child: Icon(icon, size: 13.sp, color: accentColor),
              ),
              SizedBox(height: 7.h),
              Row(
                children: [
                  Expanded(
                    child: Text(
                      label,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: Get.textTheme.bodySmall?.copyWith(
                        color: _textSecondary,
                        fontSize: 10.sp,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                ],
              ),
            ],
          ),
          SizedBox(
            height: 24.h,
            child: FittedBox(
              fit: BoxFit.scaleDown,
              alignment: Alignment.centerLeft,
              child: Text(
                value,
                maxLines: 1,
                style: Get.textTheme.titleLarge?.copyWith(
                  fontWeight: FontWeight.bold,
                  color: accentColor,
                  fontSize: 19.sp,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildEnhancedFilters() {
    return Container(
      padding: EdgeInsets.symmetric(horizontal: 12.w),
      child: Row(
        children: [
          Container(
            padding: EdgeInsets.symmetric(horizontal: 9.w, vertical: 6.h),
            child: Row(
              children: [
                Icon(
                  LucideIcons.listFilter,
                  size: 13.sp,
                  color: _primaryPurple,
                ),
                SizedBox(width: 5.w),
                Text(
                  'Filter:',
                  style: Get.textTheme.bodySmall?.copyWith(
                    color: _textSecondary,
                    fontWeight: FontWeight.w600,
                    fontSize: 11.sp,
                  ),
                ),
              ],
            ),
          ),
          SizedBox(width: 8.w),
          Expanded(
            child: SizedBox(
              height: 34.h,
              child: SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: Row(
                  children: [
                    _buildGlassFilterChip('All', null, LucideIcons.grid3x3),
                    SizedBox(width: 7.w),
                    _buildGlassFilterChip(
                        'Summary', 'summarization', LucideIcons.fileText),
                    SizedBox(width: 7.w),
                    _buildGlassFilterChip(
                        'Code', 'code_generation', LucideIcons.code),
                    SizedBox(width: 7.w),
                    _buildGlassFilterChip('Agent', 'agent', LucideIcons.bot),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildGlassFilterChip(String label, String? type, IconData icon) {
    final isSelected = _selectedTraceType == type;
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: () {
          setState(() {
            _selectedTraceType = isSelected ? null : type;
          });
          _loadData();
        },
        borderRadius: BorderRadius.circular(9.r),
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 250),
          padding: EdgeInsets.symmetric(horizontal: 10.w, vertical: 7.h),
          decoration: BoxDecoration(
            gradient: isSelected
                ? const LinearGradient(
                    colors: [_primaryPurple, Color(0xFF8B5CF6)],
                  )
                : null,
            color: isSelected ? null : _backgroundCard,
            borderRadius: BorderRadius.circular(9.r),
            border: Border.all(
              color:
                  isSelected ? _primaryPurple.withOpacity(0.5) : _borderDefault,
              width: 1.2,
            ),
            boxShadow: isSelected
                ? [
                    BoxShadow(
                      color: _primaryPurple.withOpacity(0.35),
                      blurRadius: 10,
                      offset: const Offset(0, 3),
                    ),
                  ]
                : null,
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                icon,
                size: 12.sp,
                color: isSelected ? _textPrimary : _textSecondary,
              ),
              SizedBox(width: 5.w),
              Text(
                label,
                style: Get.textTheme.bodySmall?.copyWith(
                  color: isSelected ? _textPrimary : _textSecondary,
                  fontWeight: isSelected ? FontWeight.w700 : FontWeight.w600,
                  fontSize: 11.sp,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildLoadingState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Container(
            padding: EdgeInsets.all(18.r),
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              gradient: LinearGradient(
                colors: [
                  _primaryPurple.withOpacity(0.25),
                  _primaryPurple.withOpacity(0.08)
                ],
              ),
            ),
            child: CircularProgressIndicator(
              valueColor: const AlwaysStoppedAnimation<Color>(_primaryPurple),
              strokeWidth: 3,
            ),
          ),
          SizedBox(height: 18.h),
          Text(
            'Loading traces...',
            style: Get.textTheme.bodyMedium?.copyWith(
              color: _textSecondary,
              fontSize: 13.sp,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildEmptyTracesState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Container(
            padding: EdgeInsets.all(24.r),
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              gradient: LinearGradient(
                colors: [
                  _primaryPurple.withOpacity(0.12),
                  _primaryPurple.withOpacity(0.05)
                ],
              ),
              border: Border.all(
                color: _primaryPurple.withOpacity(0.3),
                width: 2,
              ),
            ),
            child: Icon(
              LucideIcons.inbox,
              size: 36.sp,
              color: _textTertiary,
            ),
          ),
          SizedBox(height: 18.h),
          Text(
            'No traces yet',
            style: Get.textTheme.titleMedium?.copyWith(
              color: _textSecondary,
              fontWeight: FontWeight.bold,
              fontSize: 15.sp,
            ),
          ),
          SizedBox(height: 8.h),
          Text(
            'Start using AI features to see trace data',
            style: Get.textTheme.bodySmall?.copyWith(
              color: _textTertiary,
              fontSize: 12.sp,
            ),
          ),
        ],
      ),
    );
  }

  // ============================================================================
  // VIEW ROUTING & RENDERING
  // ============================================================================

  Widget _buildViewContent() {
    switch (_viewMode) {
      case 'grouped':
        return _buildGroupedView();
      case 'summary':
        return _buildSummaryView();
      case 'advanced':
      default:
        return _traces.isEmpty
            ? _buildEmptyTracesState()
            : FadeTransition(
                opacity: _fadeAnimation,
                child: _buildTracesList(),
              );
    }
  }

  // GROUPED VIEW - Sessions as expandable cards
  Widget _buildGroupedView() {
    if (_groupedTraces == null || _groupedTraces!.sessions.isEmpty) {
      return _buildEmptyTracesState();
    }

    final sessions = _groupedTraces!.sessions;

    return FadeTransition(
      opacity: _fadeAnimation,
      child: ListView.separated(
        padding: EdgeInsets.symmetric(horizontal: 12.w, vertical: 6.h),
        itemCount: sessions.length,
        separatorBuilder: (context, index) => SizedBox(height: 12.h),
        itemBuilder: (context, index) {
          final session = sessions[index];
          final isFiltered = _filteredSessionId != null &&
              session.sessionId == _filteredSessionId;

          return _buildSessionCard(session, isFiltered, index);
        },
      ),
    );
  }

  Widget _buildSessionCard(
      TraceSessionGroup session, bool isFiltered, int index) {
    return TweenAnimationBuilder<double>(
      tween: Tween(begin: 0.0, end: 1.0),
      duration: Duration(milliseconds: 350 + (index * 45)),
      curve: Curves.easeOutCubic,
      builder: (context, animValue, child) {
        return Transform.translate(
          offset: Offset(0, 12 * (1 - animValue)),
          child: Opacity(
            opacity: animValue,
            child: child,
          ),
        );
      },
      child: Container(
        decoration: BoxDecoration(
          color: _backgroundCard,
          borderRadius: BorderRadius.circular(10.r),
          border: Border.all(
            color: isFiltered ? _primaryPurple : _borderDefault,
            width: isFiltered ? 2 : 1,
          ),
          boxShadow: isFiltered
              ? [
                  BoxShadow(
                    color: _primaryPurple.withOpacity(0.3),
                    blurRadius: 12,
                    offset: const Offset(0, 4),
                  ),
                ]
              : null,
        ),
        child: Theme(
          data: ThemeData(dividerColor: Colors.transparent),
          child: ExpansionTile(
            tilePadding: EdgeInsets.symmetric(horizontal: 14.w, vertical: 4.h),
            childrenPadding: EdgeInsets.only(bottom: 12.h),
            initiallyExpanded: isFiltered,
            leading: Container(
              padding: EdgeInsets.all(8.r),
              decoration: BoxDecoration(
                color: _primaryPurple.withOpacity(0.15),
                borderRadius: BorderRadius.circular(8.r),
              ),
              child: Icon(
                LucideIcons.messageSquare,
                size: 16.sp,
                color: _primaryPurple,
              ),
            ),
            title: Text(
              session.userPrompt ?? 'Session ${session.sessionId}',
              style: Get.textTheme.bodyMedium?.copyWith(
                color: _textPrimary,
                fontWeight: FontWeight.w600,
                fontSize: 13.sp,
              ),
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
            subtitle: Padding(
              padding: EdgeInsets.only(top: 6.h),
              child: Row(
                children: [
                  _buildMiniChip(
                    '${session.totalTools} tools',
                    LucideIcons.layers,
                    _info,
                  ),
                  SizedBox(width: 8.w),
                  _buildMiniChip(
                    '${session.successCount} ✓',
                    LucideIcons.circleCheck,
                    _success,
                  ),
                  if (session.failureCount > 0) ...[
                    SizedBox(width: 8.w),
                    _buildMiniChip(
                      '${session.failureCount} ✗',
                      LucideIcons.circleX,
                      _error,
                    ),
                  ],
                ],
              ),
            ),
            children: [
              ...session.traces.map((traceData) {
                return _buildSessionTraceItem(traceData);
              }).toList(),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildMiniChip(String label, IconData icon, Color color) {
    return Container(
      padding: EdgeInsets.symmetric(horizontal: 6.w, vertical: 3.h),
      decoration: BoxDecoration(
        color: color.withOpacity(0.15),
        borderRadius: BorderRadius.circular(4.r),
        border: Border.all(color: color.withOpacity(0.3), width: 0.5),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 10.sp, color: color),
          SizedBox(width: 4.w),
          Text(
            label,
            style: Get.textTheme.bodySmall?.copyWith(
              color: color,
              fontSize: 10.sp,
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSessionTraceItem(Map<String, dynamic> traceData) {
    final toolName = traceData['tool_name'] as String? ?? 'Unknown';
    final status = traceData['status'] as String? ?? 'unknown';
    final durationMs = traceData['duration_ms'] as int?;
    final isSuccess = status == 'success';

    return Container(
      margin: EdgeInsets.symmetric(horizontal: 14.w, vertical: 4.h),
      padding: EdgeInsets.all(10.w),
      decoration: BoxDecoration(
        color: _backgroundElevated,
        borderRadius: BorderRadius.circular(6.r),
        border: Border.all(color: _borderSubtle),
      ),
      child: Row(
        children: [
          Icon(
            isSuccess ? LucideIcons.circleCheck : LucideIcons.circleX,
            size: 14.sp,
            color: isSuccess ? _success : _error,
          ),
          SizedBox(width: 10.w),
          Expanded(
            child: Text(
              prettifyTraceName(toolName),
              style: Get.textTheme.bodySmall?.copyWith(
                color: _textPrimary,
                fontSize: 12.sp,
              ),
            ),
          ),
          if (durationMs != null)
            Text(
              durationMs < 1000
                  ? '${durationMs}ms'
                  : '${(durationMs / 1000).toStringAsFixed(2)}s',
              style: Get.textTheme.bodySmall?.copyWith(
                color: _textTertiary,
                fontSize: 10.sp,
              ),
            ),
        ],
      ),
    );
  }

  // SUMMARY VIEW - Beginner-friendly
  Widget _buildSummaryView() {
    if (_traces.isEmpty) {
      return _buildEmptyTracesState();
    }

    return FadeTransition(
      opacity: _fadeAnimation,
      child: ListView.separated(
        padding: EdgeInsets.symmetric(horizontal: 12.w, vertical: 6.h),
        itemCount: _traces.length,
        separatorBuilder: (context, index) => SizedBox(height: 10.h),
        itemBuilder: (context, index) {
          final trace = _traces[index];
          return _buildSummaryCard(trace, index);
        },
      ),
    );
  }

  Widget _buildSummaryCard(TraceModel trace, int index) {
    final isSuccess = trace.isSuccess;
    final toolName = trace.toolName;

    return TweenAnimationBuilder<double>(
      tween: Tween(begin: 0.0, end: 1.0),
      duration: Duration(milliseconds: 300 + (index * 40)),
      curve: Curves.easeOut,
      builder: (context, animValue, child) {
        return Transform.translate(
          offset: Offset(0, 10 * (1 - animValue)),
          child: Opacity(opacity: animValue, child: child),
        );
      },
      child: Container(
        padding: EdgeInsets.all(12.w),
        decoration: BoxDecoration(
          color: _backgroundCard,
          borderRadius: BorderRadius.circular(8.r),
          border: Border.all(color: _borderDefault),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                // Status icon
                Container(
                  padding: EdgeInsets.all(6.r),
                  decoration: BoxDecoration(
                    color: (isSuccess ? _success : _error).withOpacity(0.15),
                    borderRadius: BorderRadius.circular(6.r),
                  ),
                  child: Icon(
                    isSuccess
                        ? LucideIcons.circleCheck
                        : LucideIcons.circleAlert,
                    size: 14.sp,
                    color: isSuccess ? _success : _error,
                  ),
                ),
                SizedBox(width: 10.w),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        prettifyTraceName(toolName),
                        style: Get.textTheme.bodyMedium?.copyWith(
                          color: _textPrimary,
                          fontWeight: FontWeight.w600,
                          fontSize: 13.sp,
                        ),
                      ),
                      SizedBox(height: 3.h),
                      Text(
                        trace.durationText,
                        style: Get.textTheme.bodySmall?.copyWith(
                          color: _textTertiary,
                          fontSize: 11.sp,
                        ),
                      ),
                    ],
                  ),
                ),
                // Confidence badge
                Container(
                  padding: EdgeInsets.symmetric(horizontal: 8.w, vertical: 4.h),
                  decoration: BoxDecoration(
                    color: _getConfidenceColor(trace.confidenceLevel)
                        .withOpacity(0.15),
                    borderRadius: BorderRadius.circular(4.r),
                    border: Border.all(
                      color: _getConfidenceColor(trace.confidenceLevel)
                          .withOpacity(0.3),
                      width: 0.5,
                    ),
                  ),
                  child: Text(
                    trace.confidenceLevel,
                    style: Get.textTheme.bodySmall?.copyWith(
                      color: _getConfidenceColor(trace.confidenceLevel),
                      fontSize: 10.sp,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
              ],
            ),
            if (trace.summaryText.isNotEmpty) ...[
              SizedBox(height: 10.h),
              Container(
                padding: EdgeInsets.all(8.w),
                decoration: BoxDecoration(
                  color: _backgroundElevated,
                  borderRadius: BorderRadius.circular(6.r),
                ),
                child: Text(
                  trace.summaryText,
                  style: Get.textTheme.bodySmall?.copyWith(
                    color: _textSecondary,
                    fontSize: 11.sp,
                  ),
                  maxLines: 3,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Color _getConfidenceColor(String level) {
    switch (level.toLowerCase()) {
      case 'high':
        return _success;
      case 'low':
        return _error;
      default:
        return _warning;
    }
  }

  // ============================================================================
  // ADVANCED VIEW (Original Traces List)
  // ============================================================================

  Widget _buildTracesList() {
    return ListView.separated(
      padding: EdgeInsets.symmetric(horizontal: 12.w, vertical: 6.h),
      itemCount: _traces.length,
      separatorBuilder: (context, index) => SizedBox(height: 11.h),
      itemBuilder: (context, index) {
        final trace = _traces[index];
        return TweenAnimationBuilder<double>(
          tween: Tween(begin: 0.0, end: 1.0),
          duration: Duration(milliseconds: 350 + (index * 45)),
          curve: Curves.easeOutCubic,
          builder: (context, animValue, child) {
            return Transform.translate(
              offset: Offset(0, 12 * (1 - animValue)),
              child: Opacity(
                opacity: animValue,
                child: child,
              ),
            );
          },
          child: _buildPremiumTraceCard(trace),
        );
      },
    );
  }

  Widget _buildPremiumTraceCard(TraceModel trace) {
    final isExpanded = _selectedTrace?.id == trace.id;
    final statusColor = trace.isSuccess ? _success : _error;

    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: () {
          setState(() {
            _selectedTrace = isExpanded ? null : trace;
          });
        },
        borderRadius: BorderRadius.circular(14.r),
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 300),
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: isExpanded
                  ? [_backgroundCard, _backgroundElevated]
                  : [_backgroundCard, _backgroundCard],
            ),
            borderRadius: BorderRadius.circular(14.r),
            border: Border.all(
              color:
                  isExpanded ? _primaryPurple.withOpacity(0.5) : _borderDefault,
              width: isExpanded ? 1.5 : 1.2,
            ),
            boxShadow: isExpanded
                ? [
                    BoxShadow(
                      color: _primaryPurple.withOpacity(0.25),
                      blurRadius: 16,
                      offset: const Offset(0, 4),
                    ),
                  ]
                : [
                    BoxShadow(
                      color: Colors.black.withOpacity(0.25),
                      blurRadius: 6,
                      offset: const Offset(0, 2),
                    ),
                  ],
          ),
          child: Column(
            children: [
              Padding(
                padding: EdgeInsets.all(13.r),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Container(
                          width: 9.w,
                          height: 9.w,
                          decoration: BoxDecoration(
                            color: statusColor,
                            shape: BoxShape.circle,
                            boxShadow: [
                              BoxShadow(
                                color: statusColor.withOpacity(0.6),
                                blurRadius: 8,
                                spreadRadius: 1.5,
                              ),
                            ],
                          ),
                        ),
                        SizedBox(width: 9.w),
                        Expanded(
                          child: Text(
                            prettifyTraceName(trace.name),
                            style: Get.textTheme.titleSmall?.copyWith(
                              fontWeight: FontWeight.w700,
                              color: _textPrimary,
                              fontSize: 14.sp,
                            ),
                          ),
                        ),
                        Container(
                          padding: EdgeInsets.symmetric(
                              horizontal: 7.w, vertical: 5.h),
                          decoration: BoxDecoration(
                            color: _textPrimary.withOpacity(0.06),
                            borderRadius: BorderRadius.circular(7.r),
                            border: Border.all(
                              color: _borderSubtle,
                            ),
                          ),
                          child: Row(
                            children: [
                              Icon(
                                LucideIcons.clock,
                                size: 11.sp,
                                color: _textSecondary,
                              ),
                              SizedBox(width: 4.w),
                              Text(
                                trace.durationText,
                                style: Get.textTheme.bodySmall?.copyWith(
                                  color: _textSecondary,
                                  fontFamily: 'monospace',
                                  fontWeight: FontWeight.w600,
                                  fontSize: 10.sp,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                    SizedBox(height: 11.h),
                    Row(
                      children: [
                        _buildPremiumChip(
                            trace.traceType, LucideIcons.tag, _primaryPurple),
                        SizedBox(width: 7.w),
                        _buildPremiumChip(
                            trace.statusText, LucideIcons.info, _info),
                        if (trace.evaluations != null &&
                            trace.evaluations!.isNotEmpty) ...[
                          SizedBox(width: 7.w),
                          _buildPremiumScoreChip(trace.averageScore!),
                        ],
                        const Spacer(),
                        Icon(
                          isExpanded
                              ? LucideIcons.chevronUp
                              : LucideIcons.chevronDown,
                          size: 15.sp,
                          color: _primaryPurple,
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              if (isExpanded) _buildExpandedTraceDetails(trace),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildPremiumChip(String label, IconData icon, Color color) {
    return Container(
      padding: EdgeInsets.symmetric(horizontal: 7.w, vertical: 5.h),
      decoration: BoxDecoration(
        color: color.withOpacity(0.18),
        borderRadius: BorderRadius.circular(7.r),
        border: Border.all(color: color.withOpacity(0.35)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 11.sp, color: color),
          SizedBox(width: 4.w),
          Text(
            label,
            style: Get.textTheme.bodySmall?.copyWith(
              fontSize: 10.sp,
              color: color.withOpacity(0.95),
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildPremiumScoreChip(double score) {
    final color = score >= 0.8
        ? _success
        : score >= 0.6
            ? _warning
            : _error;

    return Container(
      padding: EdgeInsets.symmetric(horizontal: 7.w, vertical: 5.h),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [color.withOpacity(0.25), color.withOpacity(0.12)],
        ),
        borderRadius: BorderRadius.circular(7.r),
        border: Border.all(color: color.withOpacity(0.45), width: 1.2),
        boxShadow: [
          BoxShadow(
            color: color.withOpacity(0.25),
            blurRadius: 6,
          ),
        ],
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(LucideIcons.star, size: 11.sp, color: color),
          SizedBox(width: 4.w),
          Text(
            score.toStringAsFixed(2),
            style: Get.textTheme.bodySmall?.copyWith(
              fontSize: 10.sp,
              color: color,
              fontWeight: FontWeight.w800,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildExpandedTraceDetails(TraceModel trace) {
    return Container(
      padding: EdgeInsets.all(13.r),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [
            Colors.black.withOpacity(0.25),
            Colors.black.withOpacity(0.45),
          ],
        ),
        borderRadius: BorderRadius.only(
          bottomLeft: Radius.circular(14.r),
          bottomRight: Radius.circular(14.r),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            height: 1.2,
            margin: EdgeInsets.only(bottom: 11.h),
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [
                  Colors.transparent,
                  _primaryPurple.withOpacity(0.35),
                  Colors.transparent,
                ],
              ),
            ),
          ),
          if (trace.inputData != null) ...[
            _buildPremiumDetailSection('Input', trace.inputData.toString()),
            SizedBox(height: 11.h),
          ],
          if (trace.outputData != null) ...[
            _buildPremiumDetailSection('Output', trace.outputData.toString()),
            SizedBox(height: 11.h),
          ],
          if (trace.evaluations != null && trace.evaluations!.isNotEmpty) ...[
            Row(
              children: [
                Icon(LucideIcons.chartBar, size: 13.sp, color: _primaryPurple),
                SizedBox(width: 7.w),
                Text(
                  'Evaluations',
                  style: Get.textTheme.titleSmall?.copyWith(
                    fontWeight: FontWeight.w700,
                    color: _textPrimary,
                    fontSize: 13.sp,
                  ),
                ),
              ],
            ),
            SizedBox(height: 9.h),
            ...trace.evaluations!
                .map((eval) => _buildPremiumEvaluationCard(eval)),
          ],
          if (trace.tags != null && trace.tags!.isNotEmpty) ...[
            SizedBox(height: 11.h),
            Wrap(
              spacing: 7.w,
              runSpacing: 7.h,
              children: trace.tags!
                  .map((tag) => Container(
                        padding: EdgeInsets.symmetric(
                            horizontal: 9.w, vertical: 5.h),
                        decoration: BoxDecoration(
                          color: _primaryPurple.withOpacity(0.18),
                          borderRadius: BorderRadius.circular(7.r),
                          border: Border.all(
                              color: _primaryPurple.withOpacity(0.35)),
                        ),
                        child: Text(
                          tag,
                          style: Get.textTheme.bodySmall?.copyWith(
                            fontSize: 10.sp,
                            color: _primaryPurple,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ))
                  .toList(),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildPremiumDetailSection(String title, String content) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Container(
              padding: EdgeInsets.all(5.r),
              decoration: BoxDecoration(
                color: _info.withOpacity(0.18),
                borderRadius: BorderRadius.circular(5.r),
              ),
              child: Icon(
                title == 'Input'
                    ? LucideIcons.arrowDownToLine
                    : LucideIcons.arrowUpFromLine,
                size: 11.sp,
                color: _info,
              ),
            ),
            SizedBox(width: 7.w),
            Text(
              title,
              style: Get.textTheme.titleSmall?.copyWith(
                fontWeight: FontWeight.w700,
                color: _textPrimary,
                fontSize: 12.sp,
              ),
            ),
          ],
        ),
        SizedBox(height: 7.h),
        Container(
          width: double.infinity,
          padding: EdgeInsets.all(11.r),
          decoration: BoxDecoration(
            color: Colors.black.withOpacity(0.35),
            borderRadius: BorderRadius.circular(9.r),
            border: Border.all(color: _borderSubtle),
          ),
          child: Text(
            content.length > 150 ? '${content.substring(0, 150)}...' : content,
            style: Get.textTheme.bodySmall?.copyWith(
              fontFamily: 'monospace',
              fontSize: 10.sp,
              color: _textSecondary,
              height: 1.5,
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildPremiumEvaluationCard(EvaluationModel eval) {
    final color = eval.score >= 0.8
        ? _success
        : eval.score >= 0.6
            ? _warning
            : _error;

    return Container(
      margin: EdgeInsets.only(bottom: 9.h),
      padding: EdgeInsets.all(11.r),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            color.withOpacity(0.12),
            color.withOpacity(0.06),
          ],
        ),
        borderRadius: BorderRadius.circular(9.r),
        border: Border.all(color: color.withOpacity(0.45), width: 1.2),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: EdgeInsets.all(5.r),
                decoration: BoxDecoration(
                  color: color.withOpacity(0.25),
                  borderRadius: BorderRadius.circular(5.r),
                ),
                child: Icon(LucideIcons.circleCheck, size: 12.sp, color: color),
              ),
              SizedBox(width: 9.w),
              Expanded(
                child: Text(
                  eval.metricName,
                  style: Get.textTheme.bodyMedium?.copyWith(
                    fontWeight: FontWeight.w700,
                    color: _textPrimary,
                    fontSize: 12.sp,
                  ),
                ),
              ),
              Container(
                padding: EdgeInsets.symmetric(horizontal: 9.w, vertical: 4.h),
                decoration: BoxDecoration(
                  color: color,
                  borderRadius: BorderRadius.circular(7.r),
                  boxShadow: [
                    BoxShadow(
                      color: color.withOpacity(0.45),
                      blurRadius: 8,
                    ),
                  ],
                ),
                child: Text(
                  eval.score.toStringAsFixed(2),
                  style: Get.textTheme.titleSmall?.copyWith(
                    color: _textPrimary,
                    fontWeight: FontWeight.w900,
                    fontSize: 12.sp,
                  ),
                ),
              ),
            ],
          ),
          if (eval.reason != null) ...[
            SizedBox(height: 7.h),
            Text(
              eval.reason!,
              style: Get.textTheme.bodySmall?.copyWith(
                color: _textSecondary,
                fontSize: 10.sp,
                height: 1.4,
              ),
            ),
          ],
        ],
      ),
    );
  }
}

String prettifyTraceName(String raw) {
  return raw
      // replace underscores with spaces
      .replaceAll('_', ' ')
      // handle camelCase → camel Case
      .replaceAllMapped(
        RegExp(r'([a-z])([A-Z])'),
        (m) => '${m[1]} ${m[2]}',
      )
      // normalize spacing
      .replaceAll(RegExp(r'\s+'), ' ')
      .trim()
      // Title Case
      .split(' ')
      .map((word) {
    if (word.isEmpty) return word;
    return word[0].toUpperCase() + word.substring(1).toLowerCase();
  }).join(' ');
}
