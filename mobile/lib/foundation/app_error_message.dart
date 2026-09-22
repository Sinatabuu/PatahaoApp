import 'dart:async';

/// Converts internal failures into short, safe messages for customers,
/// partners, and staff.
abstract final class AppErrorMessage {
  static const String generic =
      'Something went wrong. Check the current screen before trying again.';

  static String forError(Object? error) {
    if (error == null) {
      return generic;
    }

    if (error is TimeoutException) {
      return 'The request took too long. Check your connection and try again.';
    }

    final typeName = error.runtimeType.toString().toLowerCase();

    if (typeName.contains('clientexception')) {
      return 'Pata Hao could not connect. Check your internet connection '
          'and try again.';
    }

    if (error is FormatException) {
      return 'Pata Hao received an unexpected server response. '
          'Please try again.';
    }

    var message = error.toString().trim();

    for (final prefix in <String>['Exception:', 'Error:', 'ClientException:']) {
      if (message.startsWith(prefix)) {
        message = message.substring(prefix.length).trim();
      }
    }

    final normalized = message.toLowerCase();
    if (typeName.contains('socketexception') ||
        typeName.contains('handshakeexception') ||
        normalized.contains('socketexception') ||
        normalized.contains('failed host lookup') ||
        normalized.contains('connection refused') ||
        normalized.contains('connection reset') ||
        normalized.contains('connection closed before full header')) {
      return 'Pata Hao could not connect. Check your internet connection '
          'and try again.';
    }

    if (normalized.contains('timeout') ||
        normalized.contains('future not completed')) {
      return 'The request took too long. Check your connection and try again.';
    }

    if (normalized.contains('unauthorized') ||
        RegExp(r'\b401\b').hasMatch(normalized)) {
      return 'Your session has expired. Please sign in again.';
    }

    if (normalized.contains('forbidden') ||
        RegExp(r'\b403\b').hasMatch(normalized)) {
      return 'Your account does not have permission to complete that action.';
    }

    if (RegExp(r'\b(500|502|503|504)\b').hasMatch(normalized)) {
      return 'Pata Hao is temporarily unavailable. Please try again shortly.';
    }

    if (_looksTechnicalOrUnsafe(message, normalized)) {
      return generic;
    }

    return message;
  }

  static bool _looksTechnicalOrUnsafe(String message, String normalized) {
    if (message.isEmpty || message.length > 280) {
      return true;
    }

    return normalized.contains('<!doctype') ||
        normalized.contains('<html') ||
        normalized.contains('stack trace') ||
        normalized.contains('package:flutter') ||
        normalized.contains('package:mobile') ||
        normalized.contains('nosuchmethoderror') ||
        normalized.contains('typeerror') ||
        normalized.startsWith("type '") ||
        normalized.contains('was called on null') ||
        normalized.contains('renderflex overflowed') ||
        normalized.contains('setstate() called') ||
        normalized.contains('looking up a deactivated widget') ||
        normalized.contains('failed assertion') ||
        normalized.contains('invalid response from upstream');
  }
}
