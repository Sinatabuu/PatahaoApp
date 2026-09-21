import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/config/app_config.dart';

void main() {
  group('AppConfig', () {
    test('uses the current HTTPS API origin by default', () {
      expect(AppConfig.apiBaseUrl, 'https://patahao-api.roysafi.com');
    });

    test('normalizes a trailing slash', () {
      expect(
        AppConfig.normalizeApiBaseUrl(
          'https://api.patahao.example/',
          requireHttps: true,
        ),
        'https://api.patahao.example',
      );
    });

    test('allows an HTTP development origin', () {
      expect(
        AppConfig.normalizeApiBaseUrl(
          'http://10.0.2.2:8000',
          requireHttps: false,
        ),
        'http://10.0.2.2:8000',
      );
    });

    test('rejects HTTP for a release configuration', () {
      expect(
        () => AppConfig.normalizeApiBaseUrl(
          'http://api.patahao.example',
          requireHttps: true,
        ),
        throwsFormatException,
      );
    });

    test('rejects paths, query strings, and embedded credentials', () {
      for (final value in <String>[
        'https://api.patahao.example/api/',
        'https://api.patahao.example?secret=value',
        'https://user:password@api.patahao.example',
      ]) {
        expect(
          () => AppConfig.normalizeApiBaseUrl(value, requireHttps: true),
          throwsFormatException,
          reason: value,
        );
      }
    });
  });
}
