/// Image placeholder URLs using picsum.photos
library;

/// Image placeholders using picsum.photos (no local assets)
class ImagePlaceholders {
  ImagePlaceholders._();

  /// Base URL for picsum photos with seed for consistency
  static const String _baseUrl = 'https://picsum.photos/seed';

  /// Get a profile avatar placeholder
  static String userAvatar(String seed, {int size = 200}) =>
      '$_baseUrl/$seed/$size/$size';

  /// Get a project thumbnail
  static String projectThumbnail(String seed, {int width = 400, int height = 300}) =>
      '$_baseUrl/$seed/$width/$height';

  /// Get a generic placeholder image
  static String generic(String seed, {int width = 400, int height = 400}) =>
      '$_baseUrl/$seed/$width/$height';

  /// Agent avatar placeholder
  static String get agentAvatar =>
      '$_baseUrl/agent/200/200';

  /// No preview placeholder
  static String get noPreview =>
      '$_baseUrl/preview/400/300';

  /// Empty state placeholder
  static String get emptyState =>
      '$_baseUrl/empty/300/200';

  /// Error state placeholder
  static String get errorState =>
      '$_baseUrl/error/300/200';

  /// Codi logo placeholder
  static String get logo =>
      '$_baseUrl/codi-logo/200/200';

  /// GitHub logo (using inline data URI for consistency)
  static const String githubLogoUrl =
      'https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png';

  /// User avatar with fallback
  static String userAvatarWithFallback(String? avatarUrl, String? username) {
    if (avatarUrl != null && avatarUrl.isNotEmpty) {
      return avatarUrl;
    }
    return userAvatar(username ?? 'default');
  }
}
