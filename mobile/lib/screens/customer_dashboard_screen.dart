import 'package:flutter/material.dart';

import '../models/favorite.dart';
import '../models/payment.dart';
import '../models/viewing.dart';
import '../services/auth_service.dart';
import '../services/favorite_service.dart';
import '../services/payment_service.dart';
import '../services/viewing_service.dart';
import 'customer_profile_screen.dart';
import 'customer_receipts_screen.dart';

import 'pending_payments_screen.dart';
import 'property_list_screen.dart';

import 'customer_settings_screen.dart';


class CustomerDashboardScreen extends StatefulWidget {
  const CustomerDashboardScreen({super.key, required this.onLogout});

  final Future<void> Function() onLogout;

  @override
  State<CustomerDashboardScreen> createState() =>
      _CustomerDashboardScreenState();
}

class _CustomerDashboardScreenState extends State<CustomerDashboardScreen> {
  final PaymentService _paymentService = PaymentService();
  final ViewingService _viewingService = ViewingService();

  late Future<_CustomerDashboardData> _dashboardFuture;

  @override
  void initState() {
    super.initState();
    _loadDashboard();
  }

  void _loadDashboard() {
    _dashboardFuture = _fetchDashboardData();
  }

  Future<_CustomerDashboardData> _fetchDashboardData() async {
    final results = await Future.wait<dynamic>([
      _loadCurrentUserSafely(),
      _loadFavoritesSafely(),
      _loadViewingsSafely(),
      _loadPaymentsSafely(),
    ]);

    final user = results[0] as AuthUser?;
    final favorites = results[1] as List<Favorite>;
    final viewings = results[2] as List<Viewing>;
    final payments = results[3] as List<Payment>;

    return _CustomerDashboardData(
      user: user,
      favorites: favorites,
      viewings: viewings,
      payments: payments,
    );
  }

  Future<AuthUser?> _loadCurrentUserSafely() async {
    try {
      return await AuthService.instance.getCurrentUser();
    } catch (error) {
      debugPrint('CUSTOMER DASHBOARD USER ERROR: $error');

      return null;
    }
  }

  Future<List<Favorite>> _loadFavoritesSafely() async {
    try {
      return await FavoriteService.instance.fetchFavorites();
    } catch (error) {
      debugPrint('CUSTOMER DASHBOARD FAVORITES ERROR: $error');

      return <Favorite>[];
    }
  }

  Future<List<Viewing>> _loadViewingsSafely() async {
    try {
      return await _viewingService.getMyViewings();
    } catch (error) {
      debugPrint('CUSTOMER DASHBOARD VIEWINGS ERROR: $error');

      return <Viewing>[];
    }
  }

  Future<List<Payment>> _loadPaymentsSafely() async {
    try {
      return await _paymentService.fetchPayments();
    } catch (error) {
      debugPrint('CUSTOMER DASHBOARD PAYMENTS ERROR: $error');

      return <Payment>[];
    }
  }

  Future<void> _refreshDashboard() async {
    setState(_loadDashboard);

    await _dashboardFuture;
  }

  Future<void> _openBrowseProperties() async {
    await Navigator.of(
      context,
    ).push(MaterialPageRoute<void>(builder: (_) => const PropertyListScreen()));

    if (!mounted) {
      return;
    }

    await _refreshDashboard();
  }

  Future<void> _openPendingPayments() async {
    await Navigator.of(context).push(
      MaterialPageRoute<void>(builder: (_) => const PendingPaymentsScreen()),
    );

    if (!mounted) {
      return;
    }

    await _refreshDashboard();
  }

  Future<void> _openReceipts() async {
    await Navigator.of(context).push(
      MaterialPageRoute<void>(builder: (_) => const CustomerReceiptsScreen()),
    );

    if (!mounted) {
      return;
    }

    await _refreshDashboard();
  }

  Future<void> _openProfile() async {
    await Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) => CustomerProfileScreen(onLogout: widget.onLogout),
      ),
    );

    if (!mounted) {
      return;
    }

    await _refreshDashboard();
  }

  Future<void> _openSettings() async {
    await Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) => CustomerSettingsScreen(onLogout: widget.onLogout),
      ),
    );

    if (!mounted) {
      return;
    }

    await _refreshDashboard();
  }

  Future<void> _showComingSoon(String feature) async {
    if (!mounted) {
      return;
    }

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          '$feature is being prepared for the next '
          'customer-experience phase.',
        ),
      ),
    );
  }

  Future<void> _showLogoutDialog() async {
    final shouldLogout = await showDialog<bool>(
      context: context,
      builder: (dialogContext) {
        return AlertDialog(
          icon: const Icon(
            Icons.logout_rounded,
            color: Color(0xFF14532D),
            size: 34,
          ),
          title: const Text('Log out?'),
          content: const Text(
            'You will need to sign in again to manage '
            'saved properties, payments, and viewings.',
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
  }

  String _firstName(AuthUser? user) {
    final displayName = user?.displayName.trim() ?? '';

    if (displayName.isEmpty) {
      return 'Customer';
    }

    return displayName.split(RegExp(r'\s+')).first;
  }

  String _cleanStatus(String status) {
    return status.trim().toLowerCase();
  }

  bool _isPendingPayment(Viewing viewing) {
    final status = _cleanStatus(viewing.status);

    return status == 'pending_payment' || status == 'payment_pending';
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF4F7F4),
      appBar: AppBar(
        backgroundColor: const Color(0xFF14532D),
        foregroundColor: Colors.white,
        title: const Text(
          'Pata Hao',
          style: TextStyle(fontWeight: FontWeight.bold),
        ),
        actions: [
          IconButton(
            tooltip: 'Refresh dashboard',
            onPressed: _refreshDashboard,
            icon: const Icon(Icons.refresh_rounded),
          ),
          IconButton(
            tooltip: 'Log out',
            onPressed: _showLogoutDialog,
            icon: const Icon(Icons.logout_rounded),
          ),
        ],
      ),
      body: FutureBuilder<_CustomerDashboardData>(
        future: _dashboardFuture,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }

          if (snapshot.hasError) {
            return _DashboardErrorView(
              message: snapshot.error.toString().replaceFirst(
                'Exception: ',
                '',
              ),
              onRetry: _refreshDashboard,
            );
          }

          final data =
              snapshot.data ??
              const _CustomerDashboardData(
                user: null,
                favorites: <Favorite>[],
                viewings: <Viewing>[],
                payments: <Payment>[],
              );

          final pendingPayments = data.viewings
              .where(_isPendingPayment)
              .toList();

          final successfulPayments = data.payments
              .where((payment) => payment.isSuccessful)
              .toList();

          final nextActionViewing = pendingPayments.isNotEmpty
              ? pendingPayments.first
              : null;

          return RefreshIndicator(
            onRefresh: _refreshDashboard,
            child: ListView(
              physics: const AlwaysScrollableScrollPhysics(),
              padding: const EdgeInsets.fromLTRB(18, 20, 18, 36),
              children: [
                _WelcomeCard(
                  firstName: _firstName(data.user),
                  onBrowse: _openBrowseProperties,
                ),

                const SizedBox(height: 22),

                const Text(
                  'Account activity',
                  style: TextStyle(
                    fontSize: 19,
                    fontWeight: FontWeight.bold,
                    color: Color(0xFF111827),
                  ),
                ),

                const SizedBox(height: 12),

                Row(
                  children: [
                    Expanded(
                      child: _DashboardActionCard(
                        icon: Icons.payments_outlined,
                        title: 'Payments',
                        count: pendingPayments.length,
                        countLabel: pendingPayments.length == 1
                            ? 'payment to finish'
                            : 'payments to finish',
                        accentColor: const Color(0xFFD97706),
                        onTap: _openPendingPayments,
                      ),
                    ),

                    const SizedBox(width: 12),

                    Expanded(
                      child: _DashboardActionCard(
                        icon: Icons.receipt_long_outlined,
                        title: 'Receipts',
                        count: successfulPayments.length,
                        countLabel: successfulPayments.length == 1
                            ? 'payment receipt'
                            : 'payment receipts',
                        accentColor: const Color(0xFF7C3AED),
                        onTap: _openReceipts,
                      ),
                    ),
                  ],
                ),

                const SizedBox(height: 24),

                if (nextActionViewing != null)
                  _ContinueJourneyCard(
                    viewing: nextActionViewing,
                    onContinue: _openPendingPayments,
                  )
                else
                  _StartJourneyCard(onBrowse: _openBrowseProperties),

                const SizedBox(height: 24),

                _DashboardListTile(
                  icon: Icons.settings_outlined,
                  title: 'Settings',
                  subtitle: 'Manage notifications and preferences.',
                  onTap: _openSettings,
                ),

                const SizedBox(height: 10),

                _DashboardListTile(
                  icon: Icons.notifications_outlined,
                  title: 'Notifications',
                  subtitle: 'Viewing confirmations and important updates.',
                  onTap: () => _showComingSoon('Notifications'),
                ),

                const SizedBox(height: 10),

                _DashboardListTile(
                  icon: Icons.person_outline,
                  title: 'My Profile',
                  subtitle: 'Review your account and contact information.',
                  onTap: _openProfile,
                ),
              ],
            ),
          );
        },
      ),
    );
  }
}

class _CustomerDashboardData {
  const _CustomerDashboardData({
    required this.user,
    required this.favorites,
    required this.viewings,
    required this.payments,
  });

  final AuthUser? user;
  final List<Favorite> favorites;
  final List<Viewing> viewings;
  final List<Payment> payments;
}

class _WelcomeCard extends StatelessWidget {
  const _WelcomeCard({required this.firstName, required this.onBrowse});

  final String firstName;
  final VoidCallback onBrowse;

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
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Good morning, $firstName',
            style: const TextStyle(
              color: Colors.white70,
              fontSize: 15,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 8),
          const Text(
            'What would you like to do today?',
            style: TextStyle(
              color: Colors.white,
              fontSize: 25,
              height: 1.2,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 18),
          FilledButton.icon(
            onPressed: onBrowse,
            style: FilledButton.styleFrom(
              backgroundColor: Colors.white,
              foregroundColor: const Color(0xFF14532D),
            ),
            icon: const Icon(Icons.search_rounded),
            label: const Text('Find a Property'),
          ),
        ],
      ),
    );
  }
}

class _DashboardActionCard extends StatelessWidget {
  const _DashboardActionCard({
    required this.icon,
    required this.title,
    required this.count,
    required this.countLabel,
    required this.accentColor,
    required this.onTap,
  });

  final IconData icon;
  final String title;
  final int count;
  final String countLabel;
  final Color accentColor;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.white,
      borderRadius: BorderRadius.circular(18),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(18),
        child: Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(18),
            border: Border.all(color: const Color(0xFFE5E7EB)),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                width: 42,
                height: 42,
                decoration: BoxDecoration(
                  color: accentColor.withValues(alpha: 0.10),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Icon(icon, color: accentColor),
              ),
              const Spacer(),
              Text(
                '$count',
                style: const TextStyle(
                  fontSize: 25,
                  fontWeight: FontWeight.bold,
                  color: Color(0xFF111827),
                ),
              ),
              const SizedBox(height: 2),
              Text(
                title,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(height: 3),
              Text(
                countLabel,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontSize: 11, color: Colors.black54),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _ContinueJourneyCard extends StatelessWidget {
  const _ContinueJourneyCard({required this.viewing, required this.onContinue});

  final Viewing viewing;
  final VoidCallback onContinue;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: const Color(0xFFFFFBEB),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: const Color(0xFFFDE68A)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Row(
            children: [
              Icon(Icons.bolt_rounded, color: Color(0xFFD97706)),
              SizedBox(width: 8),
              Text(
                'Action required',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
              ),
            ],
          ),
          const SizedBox(height: 14),
          Text(
            viewing.propertyTitle.trim().isEmpty
                ? 'Viewing request'
                : viewing.propertyTitle,
            style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w700),
          ),
          const SizedBox(height: 5),
          const Text(
            'Your viewing request is waiting for payment.',
            style: TextStyle(color: Colors.black54),
          ),
          const SizedBox(height: 15),
          FilledButton.icon(
            onPressed: onContinue,
            icon: const Icon(Icons.arrow_forward_rounded),
            label: const Text('Continue Payment'),
          ),
        ],
      ),
    );
  }
}

class _StartJourneyCard extends StatelessWidget {
  const _StartJourneyCard({required this.onBrowse});

  final VoidCallback onBrowse;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: const Color(0xFFF0FDF4),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: const Color(0xFFBBF7D0)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const CircleAvatar(
            backgroundColor: Color(0xFFDCFCE7),
            child: Icon(Icons.manage_search_outlined, color: Color(0xFF15803D)),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Start your home search',
                  style: TextStyle(fontSize: 17, fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 5),
                const Text(
                  'Browse properties, save your favorites, '
                  'and request a secure viewing.',
                  style: TextStyle(color: Colors.black54, height: 1.4),
                ),
                const SizedBox(height: 12),
                TextButton.icon(
                  onPressed: onBrowse,
                  icon: const Icon(Icons.arrow_forward_rounded),
                  label: const Text('Browse Properties'),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _DashboardListTile extends StatelessWidget {
  const _DashboardListTile({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.onTap,
  });

  final IconData icon;
  final String title;
  final String subtitle;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.white,
      borderRadius: BorderRadius.circular(16),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(16),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Row(
            children: [
              CircleAvatar(
                backgroundColor: const Color(0xFFE8F5E9),
                child: Icon(icon, color: const Color(0xFF14532D)),
              ),
              const SizedBox(width: 13),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      title,
                      style: const TextStyle(fontWeight: FontWeight.bold),
                    ),
                    const SizedBox(height: 3),
                    Text(
                      subtitle,
                      style: const TextStyle(
                        fontSize: 13,
                        color: Colors.black54,
                      ),
                    ),
                  ],
                ),
              ),
              const Icon(Icons.chevron_right_rounded, color: Colors.black38),
            ],
          ),
        ),
      ),
    );
  }
}

class _DashboardErrorView extends StatelessWidget {
  const _DashboardErrorView({required this.message, required this.onRetry});

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
          const Icon(Icons.cloud_off_outlined, size: 68, color: Colors.black38),
          const SizedBox(height: 18),
          const Text(
            'Could not load your dashboard',
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 21, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 9),
          Text(
            message,
            textAlign: TextAlign.center,
            style: const TextStyle(color: Colors.black54),
          ),
          const SizedBox(height: 20),
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
