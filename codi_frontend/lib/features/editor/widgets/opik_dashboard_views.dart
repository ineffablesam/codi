  // View routing logic
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

  Widget _buildSessionCard(TraceSessionGroup session, bool isFiltered, int index) {
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
              session.userPrompt ?? 'Session ${session.sessionId.substring(0, 8)}',
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
                    LucideIcons.checkCircle,
                    _success,
                  ),
                  if (session.failureCount > 0) ...[
                    SizedBox(width: 8.w),
                    _buildMiniChip(
                      '${session.failureCount} ✗',
                      LucideIcons.xCircle,
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
            isSuccess ? LucideIcons.checkCircle : LucideIcons.xCircle,
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
              durationMs < 1000 ? '${durationMs}ms' : '${(durationMs / 1000).toStringAsFixed(2)}s',
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
                    isSuccess ? LucideIcons.checkCircle : LucideIcons.alertCircle,
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
                    color: _getConfidenceColor(trace.confidenceLevel).withOpacity(0.15),
                    borderRadius: BorderRadius.circular(4.r),
                    border: Border.all(
                      color: _getConfidenceColor(trace.confidenceLevel).withOpacity(0.3),
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
