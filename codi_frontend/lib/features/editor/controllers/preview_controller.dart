import 'package:flutter/material.dart';
import 'package:flutter_inappwebview/flutter_inappwebview.dart';
import 'package:get/get.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../../core/utils/logger.dart';
import 'editor_controller.dart';

/// Controller for preview WebView panel using InAppWebView
class PreviewController extends GetxController {
  late final EditorController _editorController;
  InAppWebViewController? webViewController;
  PullToRefreshController? pullToRefreshController;

  // State
  final deploymentUrl = RxnString();
  final isLoading = false.obs;
  final hasError = false.obs;
  final loadProgress = 0.obs;
  final isScrollingDown = false.obs;
  int _lastScrollY = 0;

  // Build state (GitHub Actions workflow running)
  final isBuilding = false.obs;
  final buildStage = ''.obs;
  final buildProgress = 0.0.obs;

  @override
  void onInit() {
    super.onInit();
    _editorController = Get.find<EditorController>();

    // Initialize with current deployment URL
    deploymentUrl.value = _editorController.previewUrl.value;

    // Listen for URL changes
    ever(_editorController.previewUrl, (String? url) {
      if (url != null && url.isNotEmpty) {
        updatePreviewUrl(url);
      }
    });

    _initPullToRefresh();
  }

  void _initPullToRefresh() {
    pullToRefreshController = PullToRefreshController(
      settings: PullToRefreshSettings(
        color: Colors.blue,
      ),
      onRefresh: () async {
        refreshPreview();
      },
    );
  }

  /// Called when WebView is created
  void onWebViewCreated(InAppWebViewController controller) {
    webViewController = controller;

    // Load initial URL if available
    if (deploymentUrl.value != null && deploymentUrl.value!.isNotEmpty) {
      loadUrl(deploymentUrl.value!);
    }
  }

  /// Handle progress changes
  void onProgressChanged(int progress) {
    loadProgress.value = progress;
    isLoading.value = progress < 100;

    if (progress == 100) {
      pullToRefreshController?.endRefreshing();
    }
  }

  /// Handle page load start
  void onLoadStart(Uri? url) {
    isLoading.value = true;
    hasError.value = false;
    AppLogger.debug('WebView loading: $url');
  }

  /// Handle page load stop
  void onLoadStop(Uri? url) {
    isLoading.value = false;
    pullToRefreshController?.endRefreshing();
    AppLogger.debug('WebView loaded: $url');
  }

  void onScrollChanged(int x, int y) {
    if (y > _lastScrollY) {
      // ⬇️ scrolling down
      isScrollingDown.value = true;
    } else if (y < _lastScrollY) {
      // ⬆️ scrolling up
      isScrollingDown.value = false;
    }

    _lastScrollY = y;
  }

  /// Handle load errors
  void onLoadError(Uri? url, int code, String message) {
    isLoading.value = false;
    hasError.value = true;
    pullToRefreshController?.endRefreshing();
    AppLogger.error('WebView error ($code): $message');
  }

  /// Load URL in WebView
  void loadUrl(String url) {
    if (webViewController != null) {
      try {
        webViewController!.loadUrl(urlRequest: URLRequest(url: WebUri(url)));
      } catch (e) {
        AppLogger.error('Failed to load URL', error: e);
        hasError.value = true;
      }
    }
  }

  /// Update and load new preview URL
  void updatePreviewUrl(String url) {
    deploymentUrl.value = url;
    loadUrl(url);
  }

  /// Refresh preview
  void refreshPreview() {
    if (webViewController != null) {
      isLoading.value = true;
      hasError.value = false;
      webViewController!.reload();
    }
  }

  /// Open in external browser
  Future<void> openInBrowser() async {
    final url = deploymentUrl.value;
    if (url == null || url.isEmpty) return;

    try {
      final uri = Uri.parse(url);
      if (await canLaunchUrl(uri)) {
        await launchUrl(uri, mode: LaunchMode.externalApplication);
      }
    } catch (e) {
      AppLogger.error('Failed to open URL', error: e);
    }
  }

  /// Go back in WebView history
  Future<void> goBack() async {
    if (webViewController != null) {
      if (await webViewController!.canGoBack()) {
        await webViewController!.goBack();
      }
    }
  }

  /// Go forward in WebView history
  Future<void> goForward() async {
    if (webViewController != null) {
      if (await webViewController!.canGoForward()) {
        await webViewController!.goForward();
      }
    }
  }
}
