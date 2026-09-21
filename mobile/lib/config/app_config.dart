class AppConfig {
  AppConfig._();

  static const String _compiledApiBaseUrl = String.fromEnvironment(
    'PATAHAO_API_BASE_URL',
    defaultValue: 'https://patahao-api.roysafi.com',
  );

  static String get apiBaseUrl => normalizeApiBaseUrl(
    _compiledApiBaseUrl,
    requireHttps: const bool.fromEnvironment('dart.vm.product'),
  );

  static void validate() {
    apiBaseUrl;
  }

  static String normalizeApiBaseUrl(
    String value, {
    required bool requireHttps,
  }) {
    final candidate = value.trim();
    final uri = Uri.tryParse(candidate);

    if (candidate.isEmpty ||
        uri == null ||
        !uri.hasScheme ||
        !uri.hasAuthority ||
        uri.host.isEmpty ||
        (uri.scheme != 'http' && uri.scheme != 'https')) {
      throw const FormatException(
        'PATAHAO_API_BASE_URL must be an absolute HTTP or HTTPS origin.',
      );
    }

    if (requireHttps && uri.scheme != 'https') {
      throw const FormatException(
        'Release builds require an HTTPS PATAHAO_API_BASE_URL.',
      );
    }

    if (uri.userInfo.isNotEmpty ||
        (uri.path.isNotEmpty && uri.path != '/') ||
        uri.hasQuery ||
        uri.hasFragment) {
      throw const FormatException(
        'PATAHAO_API_BASE_URL must contain only the API origin.',
      );
    }

    return '${uri.scheme}://${uri.authority}';
  }
}
