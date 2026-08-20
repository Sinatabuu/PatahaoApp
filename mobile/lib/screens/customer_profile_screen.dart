import 'package:flutter/material.dart';

import '../services/auth_service.dart';

class CustomerProfileScreen extends StatefulWidget {
  const CustomerProfileScreen({super.key, required this.onLogout});

  final Future<void> Function() onLogout;

  @override
  State<CustomerProfileScreen> createState() => _CustomerProfileScreenState();
}

class _CustomerProfileScreenState extends State<CustomerProfileScreen> {
  late Future<AuthUser> _profileFuture;

  @override
  void initState() {
    super.initState();
    _loadProfile();
  }

  void _loadProfile() {
    _profileFuture = AuthService.instance.getCurrentUser();
  }

  Future<void> _refreshProfile() async {
    setState(_loadProfile);
    await _profileFuture;
  }

  Future<void> _showLogoutDialog() async {
    final shouldLogout = await showDialog<bool>(
      context: context,
      builder: (dialogContext) {
        return AlertDialog(
          icon: const Icon(
            Icons.logout_rounded,
            size: 34,
            color: Color(0xFF14532D),
          ),
          title: const Text('Log out?'),
          content: const Text(
            'You will need to sign in again to access '
            'your saved properties, payments, receipts, '
            'and viewing requests.',
          ),
          actions: [
            TextButton(
              onPressed: () {
                Navigator.of(dialogContext).pop(false);
              },
              child: const Text('Stay Signed In'),
            ),
            FilledButton(
              onPressed: () {
                Navigator.of(dialogContext).pop(true);
              },
              child: const Text('Log Out'),
            ),
          ],
        );
      },
    );

    if (shouldLogout != true) {
      return;
    }

    await widget.onLogout();

    if (!mounted) {
      return;
    }

    Navigator.of(context).popUntil(
      (route) => route.isFirst,
    );
  }

  String _cleanError(Object error) {
    return error.toString().replaceFirst('Exception: ', '').trim();
  }

  String _initials(AuthUser user) {
    final source = user.displayName.trim();

    if (source.isEmpty) {
      return 'PH';
    }

    final words = source
        .split(RegExp(r'\s+'))
        .where((word) => word.isNotEmpty)
        .toList();

    if (words.isEmpty) {
      return 'PH';
    }

    if (words.length == 1) {
      final word = words.first;

      if (word.length == 1) {
        return word.toUpperCase();
      }

      return word.substring(0, 2).toUpperCase();
    }

    return '${words.first[0]}${words.last[0]}'.toUpperCase();
  }

  String _roleLabel(String role) {
    switch (role.trim().toLowerCase()) {
      case 'customer':
        return 'Customer';

      case 'partner':
        return 'Property Partner';

      case 'admin':
        return 'Administrator';

      default:
        return role
            .replaceAll('_', ' ')
            .split(' ')
            .where((word) => word.isNotEmpty)
            .map(
              (word) =>
                  '${word[0].toUpperCase()}'
                  '${word.substring(1).toLowerCase()}',
            )
            .join(' ');
    }
  }

  String _displayValue(String value, {String fallback = 'Not provided'}) {
    final cleaned = value.trim();

    return cleaned.isEmpty ? fallback : cleaned;
  }

  String _trustScoreLabel(double trustScore) {
    if (trustScore <= 0) {
      return 'Not rated yet';
    }

    return trustScore.toStringAsFixed(1);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF4F7F4),
      appBar: AppBar(
        title: const Text('My Profile'),
        backgroundColor: const Color(0xFF14532D),
        foregroundColor: Colors.white,
        actions: [
          IconButton(
            tooltip: 'Refresh profile',
            onPressed: _refreshProfile,
            icon: const Icon(Icons.refresh_rounded),
          ),
        ],
      ),
      body: FutureBuilder<AuthUser>(
        future: _profileFuture,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }

          if (snapshot.hasError) {
            return _ProfileErrorView(
              message: _cleanError(snapshot.error!),
              onRetry: _refreshProfile,
            );
          }

          final user = snapshot.data;

          if (user == null) {
            return _ProfileErrorView(
              message:
                  'Your account information could not '
                  'be loaded.',
              onRetry: _refreshProfile,
            );
          }

          return RefreshIndicator(
            onRefresh: _refreshProfile,
            child: ListView(
              physics: const AlwaysScrollableScrollPhysics(),
              padding: const EdgeInsets.fromLTRB(18, 20, 18, 36),
              children: [
                _ProfileHeader(
                  user: user,
                  initials: _initials(user),
                  roleLabel: _roleLabel(user.role),
                ),
                const SizedBox(height: 22),
                const Text(
                  'Account information',
                  style: TextStyle(
                    fontSize: 20,
                    fontWeight: FontWeight.bold,
                    color: Color(0xFF111827),
                  ),
                ),
                const SizedBox(height: 12),
                _ProfileSection(
                  children: [
                    _ProfileInformationRow(
                      icon: Icons.person_outline,
                      label: 'Full name',
                      value: _displayValue(user.fullName),
                    ),
                    const Divider(height: 1),
                    _ProfileInformationRow(
                      icon: Icons.alternate_email_rounded,
                      label: 'Username',
                      value: _displayValue(user.username),
                    ),
                    const Divider(height: 1),
                    _ProfileInformationRow(
                      icon: Icons.email_outlined,
                      label: 'Email address',
                      value: _displayValue(user.email),
                    ),
                    const Divider(height: 1),
                    _ProfileInformationRow(
                      icon: Icons.phone_outlined,
                      label: 'Phone number',
                      value: _displayValue(user.phoneNumber),
                    ),
                  ],
                ),
                const SizedBox(height: 22),
                const Text(
                  'Trust and verification',
                  style: TextStyle(
                    fontSize: 20,
                    fontWeight: FontWeight.bold,
                    color: Color(0xFF111827),
                  ),
                ),
                const SizedBox(height: 12),
                _ProfileSection(
                  children: [
                    _ProfileInformationRow(
                      icon: Icons.verified_user_outlined,
                      label: 'Account status',
                      value: user.isVerified ? 'Verified' : 'Not verified',
                      valueColor: user.isVerified
                          ? const Color(0xFF15803D)
                          : const Color(0xFFD97706),
                    ),
                    const Divider(height: 1),
                    _ProfileInformationRow(
                      icon: Icons.workspace_premium_outlined,
                      label: 'Trust score',
                      value: _trustScoreLabel(user.trustScore),
                    ),
                    const Divider(height: 1),
                    _ProfileInformationRow(
                      icon: Icons.account_circle_outlined,
                      label: 'Account type',
                      value: _roleLabel(user.role),
                    ),
                  ],
                ),
                const SizedBox(height: 22),
                Container(
                  padding: const EdgeInsets.all(17),
                  decoration: BoxDecoration(
                    color: const Color(0xFFF0FDF4),
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(color: const Color(0xFFBBF7D0)),
                  ),
                  child: const Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Icon(Icons.security_outlined, color: Color(0xFF15803D)),
                      SizedBox(width: 12),
                      Expanded(
                        child: Text(
                          'Your account helps Pata Hao '
                          'protect saved properties, viewing '
                          'requests, payments, and receipts.',
                          style: TextStyle(
                            color: Color(0xFF166534),
                            height: 1.45,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 24),
                SizedBox(
                  height: 54,
                  child: OutlinedButton.icon(
                    onPressed: _showLogoutDialog,
                    style: OutlinedButton.styleFrom(
                      foregroundColor: const Color(0xFFB91C1C),
                      side: const BorderSide(color: Color(0xFFFCA5A5)),
                    ),
                    icon: const Icon(Icons.logout_rounded),
                    label: const Text(
                      'Log Out',
                      style: TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                ),
              ],
            ),
          );
        },
      ),
    );
  }
}

class _ProfileHeader extends StatelessWidget {
  const _ProfileHeader({
    required this.user,
    required this.initials,
    required this.roleLabel,
  });

  final AuthUser user;
  final String initials;
  final String roleLabel;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(22),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [Color(0xFF14532D), Color(0xFF2F7D32)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(22),
        boxShadow: const [
          BoxShadow(
            color: Color(0x26000000),
            blurRadius: 16,
            offset: Offset(0, 7),
          ),
        ],
      ),
      child: Column(
        children: [
          CircleAvatar(
            radius: 42,
            backgroundColor: Colors.white,
            child: Text(
              initials,
              style: const TextStyle(
                color: Color(0xFF14532D),
                fontSize: 27,
                fontWeight: FontWeight.bold,
              ),
            ),
          ),
          const SizedBox(height: 14),
          Text(
            user.displayName,
            textAlign: TextAlign.center,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 23,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 5),
          Text(
            roleLabel,
            style: const TextStyle(
              color: Colors.white70,
              fontSize: 14,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 13),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
            decoration: BoxDecoration(
              color: Colors.white.withValues(alpha: 0.14),
              borderRadius: BorderRadius.circular(18),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(
                  user.isVerified
                      ? Icons.verified_rounded
                      : Icons.info_outline_rounded,
                  color: Colors.white,
                  size: 18,
                ),
                const SizedBox(width: 6),
                Text(
                  user.isVerified ? 'Verified account' : 'Verification pending',
                  style: const TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _ProfileSection extends StatelessWidget {
  const _ProfileSection({required this.children});

  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: const Color(0xFFE5E7EB)),
      ),
      child: Column(children: children),
    );
  }
}

class _ProfileInformationRow extends StatelessWidget {
  const _ProfileInformationRow({
    required this.icon,
    required this.label,
    required this.value,
    this.valueColor,
  });

  final IconData icon;
  final String label;
  final String value;
  final Color? valueColor;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 38,
            height: 38,
            decoration: BoxDecoration(
              color: const Color(0xFFE8F5E9),
              borderRadius: BorderRadius.circular(11),
            ),
            child: Icon(icon, size: 20, color: const Color(0xFF14532D)),
          ),
          const SizedBox(width: 13),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  label,
                  style: const TextStyle(fontSize: 12, color: Colors.black54),
                ),
                const SizedBox(height: 4),
                SelectableText(
                  value,
                  style: TextStyle(
                    fontSize: 15,
                    fontWeight: FontWeight.w700,
                    color: valueColor ?? const Color(0xFF111827),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _ProfileErrorView extends StatelessWidget {
  const _ProfileErrorView({required this.message, required this.onRetry});

  final String message;
  final Future<void> Function() onRetry;

  @override
  Widget build(BuildContext context) {
    return RefreshIndicator(
      onRefresh: onRetry,
      child: ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(24),
        children: [
          const SizedBox(height: 110),
          const Icon(
            Icons.person_off_outlined,
            size: 68,
            color: Colors.black38,
          ),
          const SizedBox(height: 18),
          const Text(
            'Could not load your profile',
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 21, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 10),
          Text(
            message,
            textAlign: TextAlign.center,
            style: const TextStyle(color: Colors.black54, height: 1.4),
          ),
          const SizedBox(height: 22),
          Center(
            child: FilledButton.icon(
              onPressed: onRetry,
              icon: const Icon(Icons.refresh),
              label: const Text('Try Again'),
            ),
          ),
        ],
      ),
    );
  }
}
