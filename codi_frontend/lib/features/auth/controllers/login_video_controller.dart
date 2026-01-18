/// Login video controller
library;

import 'package:chewie/chewie.dart';
import 'package:get/get.dart';
import 'package:video_player/video_player.dart';

import '../../../core/utils/logger.dart';

/// Controller for managing login screen video background
class LoginVideoController extends GetxController {
  final Rx<VideoPlayerController?> videoPlayerController =
      Rx<VideoPlayerController?>(null);
  final Rx<ChewieController?> chewieController = Rx<ChewieController?>(null);
  final showVideo = false.obs;
  final isVideoInitialized = false.obs;
  final isVideoStopped = false.obs; // Persists stopped state across rebuilds

  @override
  void onInit() {
    super.onInit();
    _initializeVideoController();
  }

  Future<void> _initializeVideoController() async {
    try {
      videoPlayerController.value = VideoPlayerController.asset(
        'assets/videos/login_bg.mp4',
      );

      await videoPlayerController.value!.initialize();
      isVideoInitialized.value = true;

      chewieController.value = ChewieController(
        videoPlayerController: videoPlayerController.value!,
        autoPlay: false, // Don't auto-play, we control this via playVideo()
        looping: true,
        showControls: false,
        aspectRatio: videoPlayerController.value!.value.aspectRatio,
        allowFullScreen: false,
        allowMuting: false,
        showControlsOnInitialize: false,
        allowedScreenSleep: false,
      );

      // Set playback speed to slow motion for aesthetic effect
      videoPlayerController.value!.setPlaybackSpeed(0.45);

      // Mute the video
      videoPlayerController.value!.setVolume(0.0);

      AppLogger.info('Video controller initialized successfully');
    } catch (e) {
      AppLogger.error('Failed to initialize video controller', error: e);
      isVideoInitialized.value = false;
    }
  }

  void playVideo() {
    // Don't play if video has been explicitly stopped (e.g., for onboarding form)
    if (isVideoStopped.value) {
      AppLogger.info('Video play blocked - video is in stopped state');
      return;
    }
    
    if (!showVideo.value &&
        chewieController.value != null &&
        isVideoInitialized.value) {
      showVideo.value = true;
      videoPlayerController.value?.play();
      AppLogger.info('Video playback started');
    }
  }

  void pauseVideo() {
    videoPlayerController.value?.pause();
    AppLogger.info('Video playback paused');
  }

  void stopVideo() {
    isVideoStopped.value = true; // Mark as stopped to prevent restart
    showVideo.value = false;
    videoPlayerController.value?.pause();
    videoPlayerController.value?.seekTo(Duration.zero);
    AppLogger.info('Video playback stopped and locked');
  }

  /// Reset video state (e.g., when returning to login screen)
  void resetVideo() {
    isVideoStopped.value = false;
    showVideo.value = false;
    videoPlayerController.value?.pause();
    videoPlayerController.value?.seekTo(Duration.zero);
    AppLogger.info('Video state reset');
  }

  @override
  void onClose() {
    AppLogger.info('Disposing video controllers');
    videoPlayerController.value?.dispose();
    chewieController.value?.dispose();
    super.onClose();
  }
}
