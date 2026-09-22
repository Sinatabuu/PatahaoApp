import 'dart:async';
import 'dart:ui';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

import '../widgets/app_failure_view.dart';
import 'app_error_message.dart';

typedef AppCrashReporter =
    FutureOr<void> Function(
      String safeError,
      StackTrace stackTrace,
      String source,
    );

/// The last line of defence for failures that escape individual screens.
///
/// Expected API failures should still be handled by the screen that initiated
/// them. This handler prevents unexpected framework and asynchronous failures
/// from exposing Flutter's red error page to users.
class AppErrorHandler {
  AppErrorHandler._();

  static final AppErrorHandler instance = AppErrorHandler._();

  final GlobalKey<NavigatorState> navigatorKey = GlobalKey<NavigatorState>();
  final GlobalKey<ScaffoldMessengerState> scaffoldMessengerKey =
      GlobalKey<ScaffoldMessengerState>();

  bool _installed = false;
  bool _appReady = false;
  String? _pendingNotice;
  DateTime? _lastNoticeAt;
  VoidCallback? _restartApp;
  AppCrashReporter? _reporter;

  void install() {
    if (_installed) {
      return;
    }

    _installed = true;

    FlutterError.onError = (details) {
      recordError(
        details.exception,
        details.stack ?? StackTrace.current,
        source: details.context?.toDescription() ?? 'flutter-framework',
        notifyUser: false,
      );

      if (kDebugMode) {
        FlutterError.presentError(details);
      }
    };

    ErrorWidget.builder = (details) {
      return Directionality(
        textDirection: TextDirection.ltr,
        child: AppFailureView(
          title: 'Pata Hao needs to recover',
          message: AppErrorMessage.generic,
          primaryLabel: 'Return to Start',
          onPrimary: restartApp,
        ),
      );
    };

    PlatformDispatcher.instance.onError = (error, stackTrace) {
      recordError(error, stackTrace, source: 'platform-dispatcher');
      return true;
    };
  }

  void attachApp({required VoidCallback restartApp}) {
    _restartApp = restartApp;

    WidgetsBinding.instance.addPostFrameCallback((_) {
      _appReady = true;
      final pendingNotice = _pendingNotice;
      _pendingNotice = null;

      if (pendingNotice != null) {
        _showNotice(pendingNotice);
      }
    });
  }

  void detachApp() {
    _restartApp = null;
    _appReady = false;
  }

  void setReporter(AppCrashReporter? reporter) {
    _reporter = reporter;
  }

  void restartApp() {
    final restart = _restartApp;

    if (restart != null) {
      restart();
      return;
    }

    final navigator = navigatorKey.currentState;

    if (navigator != null) {
      navigator.popUntil((route) => route.isFirst);
    }
  }

  void recordError(
    Object error,
    StackTrace stackTrace, {
    required String source,
    bool notifyUser = true,
  }) {
    final safeSource = source.trim().isEmpty ? 'unknown' : source.trim();

    debugPrint('APP ERROR [$safeSource]: ${_safeDiagnostic(error)}');
    debugPrintStack(stackTrace: stackTrace);

    final reporter = _reporter;

    if (reporter != null) {
      unawaited(
        Future<void>.sync(
          () => reporter(_safeDiagnostic(error), stackTrace, safeSource),
        ).catchError((Object reportingError, StackTrace reportingStack) {
          debugPrint(
            'APP ERROR REPORTING FAILED: ${_safeDiagnostic(reportingError)}',
          );
          debugPrintStack(stackTrace: reportingStack);
        }),
      );
    }

    if (notifyUser) {
      showUserNotice(AppErrorMessage.forError(error));
    }
  }

  void showUserNotice(String message) {
    final safeMessage = message.trim().isEmpty
        ? AppErrorMessage.generic
        : message.trim();

    if (!_appReady || scaffoldMessengerKey.currentState == null) {
      _pendingNotice = safeMessage;
      return;
    }

    _showNotice(safeMessage);
  }

  void _showNotice(String message) {
    final now = DateTime.now();

    if (_lastNoticeAt != null &&
        now.difference(_lastNoticeAt!) < const Duration(seconds: 2)) {
      return;
    }

    _lastNoticeAt = now;
    final messenger = scaffoldMessengerKey.currentState;

    if (messenger == null) {
      _pendingNotice = message;
      return;
    }

    messenger
      ..hideCurrentSnackBar()
      ..showSnackBar(
        SnackBar(
          content: Text(message),
          duration: const Duration(seconds: 7),
          action: SnackBarAction(
            label: 'Dismiss',
            onPressed: messenger.hideCurrentSnackBar,
          ),
        ),
      );
  }

  String _safeDiagnostic(Object error) {
    var message = error.toString();

    message = message.replaceAll(
      RegExp(r'Bearer\s+[A-Za-z0-9._~+/=-]+', caseSensitive: false),
      'Bearer [REDACTED]',
    );
    message = message.replaceAll(
      RegExp(
        r'''((?:password|token|secret|authorization)["'\s:=]+)[^,}\s]+''',
        caseSensitive: false,
      ),
      r'$1[REDACTED]',
    );

    if (message.length > 2000) {
      return '${message.substring(0, 2000)}…';
    }

    return message;
  }
}
