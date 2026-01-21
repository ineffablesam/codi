/// Codi branded in-app browser for OAuth and external links
library;

import 'package:flutter/material.dart';
import 'package:flutter_inappwebview/flutter_inappwebview.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:get/get.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../core/constants/app_colors.dart';

/// In-app browser screen with Codi branding
class CodiInAppBrowser extends StatefulWidget {
  final String url;
  final String title;
  final bool showProgress;
  final String?
      successUrlPattern; // URL pattern that indicates success (for OAuth)
  final void Function(String url)? onSuccess;
  final void Function(String? errorCode)? onError;

  const CodiInAppBrowser({
    super.key,
    required this.url,
    this.title = 'Codi',
    this.showProgress = true,
    this.successUrlPattern,
    this.onSuccess,
    this.onError,
  });

  /// Open a URL in the in-app browser
  static Future<T?> open<T>({
    required String url,
    String title = 'Codi',
    bool showProgress = true,
    String? successUrlPattern,
    void Function(String url)? onSuccess,
    void Function(String? errorCode)? onError,
  }) async {
    return await Get.to<T>(
      () => CodiInAppBrowser(
        url: url,
        title: title,
        showProgress: showProgress,
        successUrlPattern: successUrlPattern,
        onSuccess: onSuccess,
        onError: onError,
      ),
      transition: Transition.rightToLeft,
    );
  }

  /// Open OAuth flow and return when callback is reached
  static Future<String?> openOAuth({
    required String authUrl,
    required String callbackUrlPattern,
    String title = 'Connect Account',
  }) async {
    String? resultCode;

    await Get.to(
      () => CodiInAppBrowser(
        url: authUrl,
        title: title,
        successUrlPattern: callbackUrlPattern,
        onSuccess: (url) {
          // Extract code from callback URL
          final uri = Uri.parse(url);
          resultCode = uri.queryParameters['code'];
          Get.back();
        },
        onError: (error) {
          Get.back();
        },
      ),
      transition: Transition.rightToLeft,
    );

    return resultCode;
  }

  @override
  State<CodiInAppBrowser> createState() => _CodiInAppBrowserState();
}

class _CodiInAppBrowserState extends State<CodiInAppBrowser> {
  InAppWebViewController? _controller;
  double _progress = 0;
  String _currentUrl = '';
  String _pageTitle = '';
  bool _canGoBack = false;
  bool _canGoForward = false;
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _currentUrl = widget.url;
  }

  bool _isSuccessUrl(String url) {
    if (widget.successUrlPattern == null) return false;
    try {
      final uri = Uri.parse(url);
      // Check path only to avoid matching query parameters (like redirect_uri in the auth URL)
      return uri.path.contains(widget.successUrlPattern!);
    } catch (e) {
      return false;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: _buildAppBar(),
      body: Column(
        children: [
          // Progress indicator
          if (widget.showProgress && _isLoading)
            LinearProgressIndicator(
              value: _progress,
              backgroundColor: AppColors.border.withOpacity(0.2),
              valueColor:
                  const AlwaysStoppedAnimation<Color>(AppColors.primary),
              minHeight: 3.h,
            ),
          // WebView
          Expanded(
            child: InAppWebView(
              initialUrlRequest: URLRequest(url: WebUri(widget.url)),
              initialSettings: InAppWebViewSettings(
                useShouldOverrideUrlLoading: true,
                javaScriptEnabled: true,
                supportZoom: false,
                transparentBackground: true,
                userAgent: 'Codi/1.0 (Flutter)',
              ),
              onWebViewCreated: (controller) {
                _controller = controller;
              },
              onLoadStart: (controller, url) {
                print('DEBUG: Browser onLoadStart: $url');
                final urlString = url?.toString() ?? '';

                if (!mounted) return;
                setState(() {
                  _isLoading = true;
                  _currentUrl = urlString;
                });

                // Check for OAuth success pattern
                if (_isSuccessUrl(urlString)) {
                  print('DEBUG: OAuth success pattern match in onLoadStart');
                  widget.onSuccess?.call(urlString);
                }
              },
              onLoadStop: (controller, url) async {
                final urlString = url?.toString() ?? '';
                print('DEBUG: Browser onLoadStop: $urlString');

                // Check for OAuth success pattern (fallback)
                if (_isSuccessUrl(urlString)) {
                  print('DEBUG: OAuth success pattern match in onLoadStop');
                  widget.onSuccess?.call(urlString);
                  return;
                }

                if (!mounted) return;
                setState(() {
                  _isLoading = false;
                });

                final title = await controller.getTitle();
                final canGoBack = await controller.canGoBack();
                final canGoForward = await controller.canGoForward();

                if (!mounted) return;
                setState(() {
                  _pageTitle = title ?? '';
                  _canGoBack = canGoBack;
                  _canGoForward = canGoForward;
                });
              },
              onProgressChanged: (controller, progress) {
                if (!mounted) return;
                setState(() {
                  _progress = progress / 100;
                });
              },
              onLoadError: (controller, url, code, message) {
                print('DEBUG: Browser onLoadError: $code, $message');
              },
              shouldOverrideUrlLoading: (controller, navigationAction) async {
                final url = navigationAction.request.url?.toString() ?? '';
                print('DEBUG: Browser shouldOverrideUrlLoading: $url');

                // Check for OAuth success pattern
                if (_isSuccessUrl(url)) {
                  print(
                      'DEBUG: OAuth success pattern match in shouldOverrideUrlLoading');
                  widget.onSuccess?.call(url);
                  return NavigationActionPolicy.CANCEL;
                }

                // Check for error patterns in OAuth
                if (url.contains('error=')) {
                  print('DEBUG: OAuth error pattern match: $url');
                  final uri = Uri.parse(url);
                  widget.onError?.call(uri.queryParameters['error']);
                  return NavigationActionPolicy.CANCEL;
                }

                return NavigationActionPolicy.ALLOW;
              },
            ),
          ),
        ],
      ),
      bottomNavigationBar: _buildBottomBar(),
    );
  }

  PreferredSizeWidget _buildAppBar() {
    return AppBar(
      backgroundColor: AppColors.background,
      elevation: 0,
      leading: IconButton(
        onPressed: () => Get.back(),
        icon: Icon(
          Icons.close,
          color: AppColors.textPrimary,
          size: 24.r,
        ),
      ),
      title: Column(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                Icons.lock_outline,
                color: AppColors.success,
                size: 14.r,
              ),
              SizedBox(width: 4.w),
              Flexible(
                child: Text(
                  _getDomain(_currentUrl),
                  style: GoogleFonts.inter(
                    fontSize: 12.sp,
                    color: AppColors.textSecondary,
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            ],
          ),
          if (_pageTitle.isNotEmpty)
            Text(
              _pageTitle,
              style: GoogleFonts.inter(
                fontSize: 16.sp,
                fontWeight: FontWeight.w600,
                color: AppColors.textPrimary,
              ),
              overflow: TextOverflow.ellipsis,
            )
          else
            Text(
              widget.title,
              style: GoogleFonts.inter(
                fontSize: 16.sp,
                fontWeight: FontWeight.w600,
                color: AppColors.textPrimary,
              ),
            ),
        ],
      ),
      centerTitle: true,
      actions: [
        IconButton(
          onPressed: () => _controller?.reload(),
          icon: Icon(
            Icons.refresh,
            color: AppColors.textSecondary,
            size: 22.r,
          ),
        ),
      ],
    );
  }

  Widget _buildBottomBar() {
    return Container(
      padding: EdgeInsets.symmetric(horizontal: 16.w, vertical: 12.h),
      decoration: BoxDecoration(
        color: AppColors.surface,
        border: Border(
          top: BorderSide(color: AppColors.border.withOpacity(0.2)),
        ),
      ),
      child: SafeArea(
        bottom: false,
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceAround,
          children: [
            // Back
            IconButton(
              onPressed: _canGoBack ? () => _controller?.goBack() : null,
              icon: Icon(
                Icons.arrow_back_ios,
                color: _canGoBack
                    ? AppColors.textPrimary
                    : AppColors.textSecondary.withOpacity(0.4),
                size: 20.r,
              ),
            ),
            // Forward
            IconButton(
              onPressed: _canGoForward ? () => _controller?.goForward() : null,
              icon: Icon(
                Icons.arrow_forward_ios,
                color: _canGoForward
                    ? AppColors.textPrimary
                    : AppColors.textSecondary.withOpacity(0.4),
                size: 20.r,
              ),
            ),
            // Codi branding
            Row(
              children: [
                Container(
                  padding:
                      EdgeInsets.symmetric(horizontal: 12.w, vertical: 6.h),
                  decoration: BoxDecoration(
                    gradient: const LinearGradient(
                      colors: [AppColors.primary, AppColors.info],
                    ),
                    borderRadius: BorderRadius.circular(16.r),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(
                        Icons.auto_awesome,
                        color: Colors.white,
                        size: 14.r,
                      ),
                      SizedBox(width: 4.w),
                      Text(
                        'Codi',
                        style: GoogleFonts.inter(
                          fontSize: 12.sp,
                          fontWeight: FontWeight.w700,
                          color: Colors.white,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  String _getDomain(String url) {
    try {
      final uri = Uri.parse(url);
      return uri.host;
    } catch (e) {
      return url;
    }
  }
}
