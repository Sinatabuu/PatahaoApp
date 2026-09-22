import 'dart:async';

import 'package:flutter/material.dart';

import 'config/app_config.dart';
import 'foundation/app_error_handler.dart';
import 'screens/app_entry_screen.dart';
import 'widgets/app_failure_view.dart';

void main() {
  runZonedGuarded<void>(
    () {
      WidgetsFlutterBinding.ensureInitialized();
      AppErrorHandler.instance.install();

      try {
        AppConfig.validate();
        runApp(const PataHaoApp());
      } catch (error, stackTrace) {
        AppErrorHandler.instance.recordError(
          error,
          stackTrace,
          source: 'app-startup',
          notifyUser: false,
        );
        runApp(const _StartupFailureApp());
      }
    },
    (error, stackTrace) {
      AppErrorHandler.instance.recordError(
        error,
        stackTrace,
        source: 'root-zone',
      );
    },
  );
}

class PataHaoApp extends StatefulWidget {
  const PataHaoApp({super.key});

  @override
  State<PataHaoApp> createState() => _PataHaoAppState();
}

class _PataHaoAppState extends State<PataHaoApp> {
  Key _applicationKey = UniqueKey();

  @override
  void initState() {
    super.initState();
    AppErrorHandler.instance.attachApp(restartApp: _restartApp);
  }

  @override
  void dispose() {
    AppErrorHandler.instance.detachApp();
    super.dispose();
  }

  void _restartApp() {
    if (!mounted) {
      return;
    }

    setState(() {
      _applicationKey = UniqueKey();
    });
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      key: _applicationKey,
      navigatorKey: AppErrorHandler.instance.navigatorKey,
      scaffoldMessengerKey: AppErrorHandler.instance.scaffoldMessengerKey,
      title: 'Pata Hao',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF34AD2C)),
        useMaterial3: true,
      ),
      home: const AppEntryScreen(),
    );
  }
}

class _StartupFailureApp extends StatelessWidget {
  const _StartupFailureApp();

  @override
  Widget build(BuildContext context) {
    return const MaterialApp(
      debugShowCheckedModeBanner: false,
      home: Scaffold(
        body: AppFailureView(
          title: 'Pata Hao could not start',
          message: 'Close and reopen the app. If the problem continues, '
              'contact Pata Hao support.',
        ),
      ),
    );
  }
}
