import 'package:flutter/material.dart';
import 'package:webview_flutter/webview_flutter.dart';
import '../../../core/utils/logger.dart';

/// A WebView widget that handles GitHub OAuth authentication.
/// 
/// It loads the [authUrl] and intercepts navigation to the callback URL.
/// When the callback URL is matched, it returns a [Map] containing the
/// 'code' and 'state' parameters.
class GitHubAuthWebView extends StatefulWidget {
  final String authUrl;
  final String callbackUrl;

  const GitHubAuthWebView({
    super.key,
    required this.authUrl,
    required this.callbackUrl,
  });

  @override
  State<GitHubAuthWebView> createState() => _GitHubAuthWebViewState();
}

class _GitHubAuthWebViewState extends State<GitHubAuthWebView> {
  late final WebViewController _controller;
  bool _isLoading = true;
  bool _hasReturnedResult = false;

  @override
  void initState() {
    super.initState();
    _controller = WebViewController()
      ..setJavaScriptMode(JavaScriptMode.unrestricted)
      ..setNavigationDelegate(
        NavigationDelegate(
          onPageStarted: (url) {
            setState(() {
              _isLoading = true;
            });
            AppLogger.debug('WebView started loading: $url');
          },
          onPageFinished: (url) {
            setState(() {
              _isLoading = false;
            });
            AppLogger.debug('WebView finished loading: $url');
            
            // Check if we landed on callback URL (fast redirect case)
            // This handles when user is already authed with GitHub
            _tryExtractCallback(url);
          },
          onNavigationRequest: (NavigationRequest request) {
            final url = request.url;
            AppLogger.debug('WebView navigation request: $url');

            // Try to extract callback - if successful, prevent further navigation
            if (_tryExtractCallback(url)) {
              return NavigationDecision.prevent;
            }
            return NavigationDecision.navigate;
          },
          onWebResourceError: (WebResourceError error) {
            AppLogger.error('WebView error: ${error.description}');
          },
        ),
      )
      ..loadRequest(Uri.parse(widget.authUrl));
  }

  /// Try to extract code/state from callback URL
  /// Returns true if successful and result was returned
  bool _tryExtractCallback(String url) {
    // Prevent returning multiple times
    if (_hasReturnedResult) return false;

    final uri = Uri.parse(url);
    final isCallbackPath = uri.path.endsWith('/auth/github/callback');
    final hasCode = uri.queryParameters.containsKey('code');
    final hasState = uri.queryParameters.containsKey('state');

    if (isCallbackPath && hasCode && hasState) {
      final code = uri.queryParameters['code']!;
      final state = uri.queryParameters['state']!;
      
      _hasReturnedResult = true;
      AppLogger.info('WebView intercepted callback URL with code and state');
      Navigator.pop(context, {
        'code': code,
        'state': state,
      });
      return true;
    }
    
    // Check for error in callback
    final hasError = uri.queryParameters.containsKey('error');
    if (isCallbackPath && hasError) {
      final error = uri.queryParameters['error'] ?? 'Unknown error';
      final errorDescription = uri.queryParameters['error_description'] ?? '';
      
      _hasReturnedResult = true;
      AppLogger.error('GitHub OAuth error: $error - $errorDescription');
      Navigator.pop(context, {
        'error': errorDescription.isNotEmpty ? errorDescription : error,
      });
      return true;
    }
    
    return false;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Login with GitHub'),
        leading: IconButton(
          icon: const Icon(Icons.close),
          onPressed: () => Navigator.pop(context),
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => _controller.reload(),
          ),
        ],
      ),
      body: Stack(
        children: [
          WebViewWidget(controller: _controller),
          if (_isLoading)
            const Center(
              child: CircularProgressIndicator(),
            ),
        ],
      ),
    );
  }
}
