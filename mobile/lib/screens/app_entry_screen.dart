import 'package:flutter/material.dart';

import 'package:mobile/screens/partner_dashboard_screen.dart';
import 'package:mobile/screens/property_list_screen.dart';
import 'package:mobile/screens/welcome_screen.dart';
import 'package:mobile/services/auth_service.dart';
import 'package:mobile/screens/staff_operations_dashboard_screen.dart';

class AppEntryScreen extends StatefulWidget {
  const AppEntryScreen({super.key});

  @override
  State<AppEntryScreen> createState() => _AppEntryScreenState();
}

class _AppEntryScreenState extends State<AppEntryScreen> {
  bool _isCheckingSession = true;
  bool _isLoggedIn = false;

  AuthUser? _currentUser;
  String? _sessionError;

  @override
  void initState() {
    super.initState();
    _checkSession();
  }

  Future<void> _checkSession() async {
    if (mounted) {
      setState(() {
        _isCheckingSession = true;
        _sessionError = null;
      });
    }

    try {
      final isLoggedIn = await AuthService.instance.isLoggedIn();

      if (!isLoggedIn) {
        if (!mounted) {
          return;
        }

        setState(() {
          _isLoggedIn = false;
          _currentUser = null;
          _isCheckingSession = false;
        });

        return;
      }

      final currentUser = await AuthService.instance.getCurrentUser();

      if (!mounted) {
        return;
      }

      setState(() {
        _isLoggedIn = true;
        _currentUser = currentUser;
        _isCheckingSession = false;
      });
    } catch (error) {
      await AuthService.instance.logout();

      if (!mounted) {
        return;
      }

      setState(() {
        _isLoggedIn = false;
        _currentUser = null;
        _isCheckingSession = false;
        _sessionError = _cleanError(error);
      });
    }
  }

  void _handleLoginSuccess() {
    _loadUserAfterLogin();
  }

  Future<void> _loadUserAfterLogin() async {
    setState(() {
      _isCheckingSession = true;
      _sessionError = null;
    });

    try {
      final currentUser = await AuthService.instance.getCurrentUser();

      if (!mounted) {
        return;
      }

      setState(() {
        _currentUser = currentUser;
        _isLoggedIn = true;
        _isCheckingSession = false;
      });
    } catch (error) {
      await AuthService.instance.logout();

      if (!mounted) {
        return;
      }

      setState(() {
        _currentUser = null;
        _isLoggedIn = false;
        _isCheckingSession = false;
        _sessionError = _cleanError(error);
      });
    }
  }

  Future<void> _handleLogout() async {
    await AuthService.instance.logout();

    if (!mounted) {
      return;
    }

    // Close Profile, Saved, Viewings, property details,
    // and any other customer screens that were pushed
    // above the main app entry screen.
    Navigator.of(context).popUntil((route) => route.isFirst);

    if (!mounted) {
      return;
    }

    setState(() {
      _isLoggedIn = false;
      _currentUser = null;
      _sessionError = null;
    });
  }

  String _cleanError(Object error) {
    return error.toString().replaceFirst('Exception: ', '');
  }

  Widget _buildAuthenticatedScreen() {
    final currentUser = _currentUser;

    if (currentUser == null) {
      return SessionErrorScreen(
        message: 'Unable to determine the account type.',
        onRetry: _checkSession,
        onSignOut: _handleLogout,
      );
    }

    if (currentUser.isStaff) {
      return StaffOperationsDashboardScreen(
        currentUser: currentUser,
        onLogout: _handleLogout,
      );
    }

    switch (currentUser.role) {
      case 'partner':
        return PartnerDashboardScreen(onLogout: _handleLogout);

      case 'customer':
        return PropertyListScreen(onLogout: _handleLogout);

      default:
        return SessionErrorScreen(
          message:
              'The account role "${currentUser.role}" is not supported yet.',
          onRetry: _checkSession,
          onSignOut: _handleLogout,
        );
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_isCheckingSession) {
      return const SplashScreen();
    }

    if (_isLoggedIn) {
      return _buildAuthenticatedScreen();
    }

    return Stack(
      children: [
        WelcomeScreen(onLoginSuccess: _handleLoginSuccess),
        if (_sessionError != null)
          Positioned(
            left: 16,
            right: 16,
            bottom: 20,
            child: SafeArea(
              child: Material(
                elevation: 4,
                borderRadius: BorderRadius.circular(12),
                color: const Color(0xFFFFF3E0),
                child: Padding(
                  padding: const EdgeInsets.all(14),
                  child: Row(
                    children: [
                      const Icon(
                        Icons.warning_amber_rounded,
                        color: Color(0xFF9A3412),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Text(
                          _sessionError!,
                          style: const TextStyle(color: Color(0xFF7C2D12)),
                        ),
                      ),
                      IconButton(
                        onPressed: () {
                          setState(() {
                            _sessionError = null;
                          });
                        },
                        icon: const Icon(Icons.close),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
      ],
    );
  }
}

class SplashScreen extends StatelessWidget {
  const SplashScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return const Scaffold(
      backgroundColor: Color(0xFFF6F8F6),
      body: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            CircularProgressIndicator(),
            SizedBox(height: 18),
            Text(
              'Opening Pata Hao...',
              style: TextStyle(color: Colors.black54, fontSize: 15),
            ),
          ],
        ),
      ),
    );
  }
}

class SessionErrorScreen extends StatelessWidget {
  const SessionErrorScreen({
    super.key,
    required this.message,
    required this.onRetry,
    required this.onSignOut,
  });

  final String message;
  final Future<void> Function() onRetry;
  final Future<void> Function() onSignOut;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF6F8F6),
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 460),
              child: Card(
                child: Padding(
                  padding: const EdgeInsets.all(24),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const Icon(
                        Icons.account_circle_outlined,
                        size: 60,
                        color: Color(0xFF9A3412),
                      ),
                      const SizedBox(height: 18),
                      const Text(
                        'Account unavailable',
                        style: TextStyle(
                          fontSize: 22,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      const SizedBox(height: 10),
                      Text(
                        message,
                        textAlign: TextAlign.center,
                        style: const TextStyle(
                          color: Colors.black54,
                          height: 1.4,
                        ),
                      ),
                      const SizedBox(height: 22),
                      SizedBox(
                        width: double.infinity,
                        child: ElevatedButton.icon(
                          onPressed: onRetry,
                          icon: const Icon(Icons.refresh),
                          label: const Text('Try Again'),
                        ),
                      ),
                      const SizedBox(height: 10),
                      SizedBox(
                        width: double.infinity,
                        child: OutlinedButton.icon(
                          onPressed: onSignOut,
                          icon: const Icon(Icons.logout),
                          label: const Text('Sign Out'),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
