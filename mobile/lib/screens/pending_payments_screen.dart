import 'package:flutter/material.dart';

import '../models/viewing.dart';
import '../services/viewing_service.dart';
import 'payment_screen.dart';

class PendingPaymentsScreen extends StatefulWidget {
  const PendingPaymentsScreen({super.key});

  @override
  State<PendingPaymentsScreen> createState() => _PendingPaymentsScreenState();
}

class _PendingPaymentsScreenState extends State<PendingPaymentsScreen> {
  final ViewingService _viewingService = ViewingService();

  late Future<List<Viewing>> _pendingPaymentsFuture;

  @override
  void initState() {
    super.initState();
    _loadPendingPayments();
  }

  void _loadPendingPayments() {
    _pendingPaymentsFuture = _fetchPendingPayments();
  }

  Future<List<Viewing>> _fetchPendingPayments() async {
    final viewings = await _viewingService.getMyViewings();

    final pendingViewings = viewings.where((viewing) {
      final status = viewing.status.trim().toLowerCase();

      return status == 'pending_payment' || status == 'payment_processing';
    }).toList();

    pendingViewings.sort((first, second) => second.id.compareTo(first.id));

    return pendingViewings;
  }

  Future<void> _refreshPendingPayments() async {
    setState(_loadPendingPayments);

    await _pendingPaymentsFuture;
  }

  Future<void> _continuePayment(Viewing viewing) async {
    await Navigator.of(context).push(
      MaterialPageRoute<void>(builder: (_) => PaymentScreen(viewing: viewing)),
    );

    if (!mounted) {
      return;
    }

    await _refreshPendingPayments();
  }

  String _cleanError(Object error) {
    return error.toString().replaceFirst('Exception: ', '').trim();
  }

  String _formatStatus(String status) {
    switch (status.trim().toLowerCase()) {
      case 'pending_payment':
        return 'Awaiting Payment';

      case 'payment_processing':
        return 'Payment Processing';

      default:
        return status
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

  String _formatDate(String value) {
    final parsed = DateTime.tryParse(value);

    if (parsed == null) {
      return value;
    }

    const months = <String>[
      'Jan',
      'Feb',
      'Mar',
      'Apr',
      'May',
      'Jun',
      'Jul',
      'Aug',
      'Sep',
      'Oct',
      'Nov',
      'Dec',
    ];

    return '${parsed.day} '
        '${months[parsed.month - 1]} '
        '${parsed.year}';
  }

  String _formatTime(String value) {
    final parts = value.split(':');

    if (parts.length < 2) {
      return value;
    }

    final hour = int.tryParse(parts[0]);
    final minute = int.tryParse(parts[1]);

    if (hour == null || minute == null) {
      return value;
    }

    final period = hour >= 12 ? 'PM' : 'AM';

    final displayHour = hour == 0
        ? 12
        : hour > 12
        ? hour - 12
        : hour;

    return '$displayHour:'
        '${minute.toString().padLeft(2, '0')} '
        '$period';
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF6F8F6),
      appBar: AppBar(
        title: const Text('Pending Payments'),
        backgroundColor: const Color(0xFF14532D),
        foregroundColor: Colors.white,
        actions: [
          IconButton(
            tooltip: 'Refresh',
            onPressed: _refreshPendingPayments,
            icon: const Icon(Icons.refresh_rounded),
          ),
        ],
      ),
      body: FutureBuilder<List<Viewing>>(
        future: _pendingPaymentsFuture,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }

          if (snapshot.hasError) {
            return _PendingPaymentsErrorView(
              message: _cleanError(snapshot.error!),
              onRetry: _refreshPendingPayments,
            );
          }

          final pendingViewings = snapshot.data ?? <Viewing>[];

          if (pendingViewings.isEmpty) {
            return RefreshIndicator(
              onRefresh: _refreshPendingPayments,
              child: ListView(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: const EdgeInsets.all(24),
                children: const [
                  SizedBox(height: 110),
                  Icon(
                    Icons.check_circle_outline_rounded,
                    size: 78,
                    color: Color(0xFF34AD2C),
                  ),
                  SizedBox(height: 18),
                  Text(
                    'No pending payments',
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      fontSize: 22,
                      fontWeight: FontWeight.bold,
                      color: Color(0xFF111827),
                    ),
                  ),
                  SizedBox(height: 10),
                  Text(
                    'You have completed all your current '
                    'viewing payments.',
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      fontSize: 15,
                      height: 1.5,
                      color: Colors.black54,
                    ),
                  ),
                ],
              ),
            );
          }

          return RefreshIndicator(
            onRefresh: _refreshPendingPayments,
            child: ListView.builder(
              physics: const AlwaysScrollableScrollPhysics(),
              padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
              itemCount: pendingViewings.length,
              itemBuilder: (context, index) {
                final viewing = pendingViewings[index];

                return _PendingPaymentCard(
                  viewing: viewing,
                  formattedStatus: _formatStatus(viewing.status),
                  formattedDate: _formatDate(viewing.requestedDate),
                  formattedTime: _formatTime(viewing.requestedTime),
                  onContinue: () {
                    _continuePayment(viewing);
                  },
                );
              },
            ),
          );
        },
      ),
    );
  }
}

class _PendingPaymentCard extends StatelessWidget {
  const _PendingPaymentCard({
    required this.viewing,
    required this.formattedStatus,
    required this.formattedDate,
    required this.formattedTime,
    required this.onContinue,
  });

  final Viewing viewing;
  final String formattedStatus;
  final String formattedDate;
  final String formattedTime;
  final VoidCallback onContinue;

  bool get isProcessing {
    return viewing.status.trim().toLowerCase() == 'payment_processing';
  }

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 16),
      elevation: 1,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  width: 48,
                  height: 48,
                  decoration: BoxDecoration(
                    color: const Color(0xFFFFF7ED),
                    borderRadius: BorderRadius.circular(14),
                  ),
                  child: const Icon(
                    Icons.payments_outlined,
                    color: Color(0xFFD97706),
                  ),
                ),
                const SizedBox(width: 13),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        viewing.propertyTitle.trim().isEmpty
                            ? 'Viewing request'
                            : viewing.propertyTitle,
                        style: const TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.bold,
                          color: Color(0xFF111827),
                        ),
                      ),
                      const SizedBox(height: 5),
                      Text(
                        'Viewing #${viewing.id}',
                        style: const TextStyle(
                          fontSize: 13,
                          color: Colors.black54,
                        ),
                      ),
                    ],
                  ),
                ),
                _PaymentStatusBadge(
                  label: formattedStatus,
                  isProcessing: isProcessing,
                ),
              ],
            ),
            const SizedBox(height: 18),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: const Color(0xFFF9FAFB),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Column(
                children: [
                  _PaymentInformationRow(
                    icon: Icons.calendar_today_outlined,
                    label: 'Viewing date',
                    value: formattedDate,
                  ),
                  const SizedBox(height: 12),
                  _PaymentInformationRow(
                    icon: Icons.schedule_outlined,
                    label: 'Viewing time',
                    value: formattedTime,
                  ),
                  const SizedBox(height: 12),
                  _PaymentInformationRow(
                    icon: Icons.account_balance_wallet_outlined,
                    label: 'Amount due',
                    value: 'KES ${viewing.feeAmount.toStringAsFixed(0)}',
                    emphasize: true,
                  ),
                ],
              ),
            ),
            const SizedBox(height: 14),
            Text(
              isProcessing
                  ? 'A payment attempt already exists. '
                        'Continue safely from the same reservation.'
                  : 'Complete the viewing fee to submit '
                        'your request to the property partner.',
              style: const TextStyle(color: Colors.black54, height: 1.4),
            ),
            const SizedBox(height: 16),
            SizedBox(
              width: double.infinity,
              height: 52,
              child: FilledButton.icon(
                onPressed: onContinue,
                style: FilledButton.styleFrom(
                  backgroundColor: const Color(0xFF14532D),
                  foregroundColor: Colors.white,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                ),
                icon: Icon(
                  isProcessing
                      ? Icons.refresh_rounded
                      : Icons.lock_outline_rounded,
                ),
                label: Text(
                  isProcessing ? 'Resume Payment' : 'Continue to Payment',
                  style: const TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _PaymentStatusBadge extends StatelessWidget {
  const _PaymentStatusBadge({required this.label, required this.isProcessing});

  final String label;
  final bool isProcessing;

  @override
  Widget build(BuildContext context) {
    final backgroundColor = isProcessing
        ? const Color(0xFFDBEAFE)
        : const Color(0xFFFEF3C7);

    final foregroundColor = isProcessing
        ? const Color(0xFF1D4ED8)
        : const Color(0xFF92400E);

    return Container(
      constraints: const BoxConstraints(maxWidth: 116),
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
      decoration: BoxDecoration(
        color: backgroundColor,
        borderRadius: BorderRadius.circular(18),
      ),
      child: Text(
        label,
        textAlign: TextAlign.center,
        style: TextStyle(
          fontSize: 11,
          fontWeight: FontWeight.bold,
          color: foregroundColor,
        ),
      ),
    );
  }
}

class _PaymentInformationRow extends StatelessWidget {
  const _PaymentInformationRow({
    required this.icon,
    required this.label,
    required this.value,
    this.emphasize = false,
  });

  final IconData icon;
  final String label;
  final String value;
  final bool emphasize;

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(icon, size: 19, color: const Color(0xFF14532D)),
        const SizedBox(width: 9),
        Expanded(
          child: Text(label, style: const TextStyle(color: Colors.black54)),
        ),
        const SizedBox(width: 12),
        Flexible(
          child: Text(
            value,
            textAlign: TextAlign.end,
            style: TextStyle(
              fontWeight: FontWeight.bold,
              color: emphasize
                  ? const Color(0xFF14532D)
                  : const Color(0xFF111827),
            ),
          ),
        ),
      ],
    );
  }
}

class _PendingPaymentsErrorView extends StatelessWidget {
  const _PendingPaymentsErrorView({
    required this.message,
    required this.onRetry,
  });

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
          const SizedBox(height: 100),
          const Icon(Icons.cloud_off_outlined, size: 68, color: Colors.black38),
          const SizedBox(height: 18),
          const Text(
            'Could not load pending payments',
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
