import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/foundation/app_error_message.dart';

class _ClientException implements Exception {
  const _ClientException();

  @override
  String toString() => 'write failed';
}

void main() {
  group('AppErrorMessage', () {
    test('preserves a short business validation message', () {
      expect(
        AppErrorMessage.forError(
          Exception('Only an active partner can complete this viewing.'),
        ),
        'Only an active partner can complete this viewing.',
      );
    });

    test('turns timeouts into a useful connection message', () {
      expect(
        AppErrorMessage.forError(TimeoutException('Future not completed')),
        'The request took too long. Check your connection and try again.',
      );
    });

    test('turns HTTP client failures into a useful connection message', () {
      expect(
        AppErrorMessage.forError(const _ClientException()),
        'Pata Hao could not connect. Check your internet connection '
        'and try again.',
      );
    });

    test('recognizes socket failures without importing dart:io', () {
      expect(
        AppErrorMessage.forError(
          Exception('SocketException: Failed host lookup'),
        ),
        'Pata Hao could not connect. Check your internet connection '
        'and try again.',
      );
    });

    test('explains expired authentication safely', () {
      expect(
        AppErrorMessage.forError(Exception('Server returned 401.')),
        'Your session has expired. Please sign in again.',
      );
    });

    test('hides server HTML and implementation failures', () {
      expect(
        AppErrorMessage.forError(
          Exception('<!DOCTYPE html><html>Bad gateway</html>'),
        ),
        AppErrorMessage.generic,
      );
      expect(
        AppErrorMessage.forError(
          Exception("type 'Null' is not a subtype of type 'String'"),
        ),
        AppErrorMessage.generic,
      );
    });

    test('turns server outages into a temporary-unavailable message', () {
      expect(
        AppErrorMessage.forError(Exception('Server returned 503.')),
        'Pata Hao is temporarily unavailable. Please try again shortly.',
      );
    });
  });
}
