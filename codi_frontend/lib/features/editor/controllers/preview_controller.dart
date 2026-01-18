import 'package:flutter/material.dart';
import 'package:flutter_inappwebview/flutter_inappwebview.dart';
import 'package:get/get.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../../core/api/api_service.dart';
import '../../../core/utils/logger.dart';
import 'editor_controller.dart';

/// Controller for preview WebView panel using InAppWebView
class PreviewController extends GetxController {
  late final EditorController _editorController;
  final ApiService _apiService = Get.find<ApiService>();
  InAppWebViewController? webViewController;
  PullToRefreshController? pullToRefreshController;

  // State
  final deploymentUrl = RxnString();
  final isLoading = false.obs;
  final hasError = false.obs;
  final loadProgress = 0.obs;
  final isScrollingDown = false.obs;
  int _lastScrollY = 0;

  // Build state (container building/deploying)
  final isBuilding = false.obs;
  final buildStage = ''.obs;
  final buildProgress = 0.0.obs;

  // Deployment state
  final containerId = RxnString();
  final deploymentId = RxnString();
  final currentBranch = 'main'.obs;
  final isPreviewDeployment = false.obs;

  @override
  void onInit() {
    super.onInit();
    _editorController = Get.find<EditorController>();

    // Initialize with current deployment URL and container ID
    deploymentUrl.value = _editorController.previewUrl.value;
    containerId.value = _editorController.currentProject.value?.activeContainerId;

    // Listen for URL changes
    ever(_editorController.previewUrl, (String? url) {
      if (url != null && url.isNotEmpty) {
        updatePreviewUrl(url);
      }
    });

    // Listen for project changes to update container ID
    ever(_editorController.currentProject, (project) {
      if (project?.activeContainerId != null && containerId.value == null) {
        containerId.value = project!.activeContainerId;
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
      try {
        isLoading.value = true;
        hasError.value = false;
        webViewController!.reload();
      } catch (e) {
        AppLogger.error('Failed to reload WebView', error: e);
        webViewController = null;
      }
    }
  }

  @override
  void onClose() {
    webViewController = null;
    super.onClose();
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

  /// Create a new deployment (container-based)
  Future<bool> createDeployment(
      {String branch = 'main', bool isPreview = false}) async {
    final projectId = _editorController.currentProject.value?.id;
    if (projectId == null) return false;

    try {
      isBuilding.value = true;
      buildStage.value = 'Creating deployment...';
      buildProgress.value = 0.1;

      final response = await _apiService.post(
        '/deployments',
        data: {
          'project_id': projectId,
          'branch': branch,
          'is_preview': isPreview,
        },
      );

      if (response.statusCode == 200) {
        final data = response.data as Map<String, dynamic>;
        deploymentId.value = data['id'] as String?;
        containerId.value = data['container_id'] as String?;
        currentBranch.value = branch;
        isPreviewDeployment.value = isPreview;

        // Update preview URL
        final url = data['url'] as String?;
        if (url != null) {
          deploymentUrl.value = url;
          loadUrl(url);
        }

        buildStage.value = 'Deployment active';
        buildProgress.value = 1.0;
        AppLogger.info('Deployment created: $url');
        return true;
      }
    } catch (e) {
      debugPrint("=============$e");
      AppLogger.error('Failed to create deployment', error: e);
      buildStage.value = 'Deployment failed';
    } finally {
      isBuilding.value = false;
    }
    return false;
  }

  /// Redeploy current deployment
  Future<bool> redeploy() async {
    if (deploymentId.value == null) return false;

    try {
      isBuilding.value = true;
      buildStage.value = 'Redeploying...';

      final response = await _apiService.post(
        '/deployments/${deploymentId.value}/redeploy',
      );

      if (response.statusCode == 200) {
        final data = response.data as Map<String, dynamic>;
        final url = data['url'] as String?;
        if (url != null) {
          deploymentUrl.value = url;
          loadUrl(url);
        }
        return true;
      }
    } catch (e) {
      AppLogger.error('Failed to redeploy', error: e);
    } finally {
      isBuilding.value = false;
    }
    return false;
  }
}
