import 'package:flutter/material.dart';

import '../foundation/app_error_message.dart';
import '../models/viewing_credit.dart';
import '../services/payment_service.dart';

class CustomerViewingCreditScreen extends StatefulWidget {
  const CustomerViewingCreditScreen({
    super.key,
    this.initialBalance,
    this.paymentService,
  });

  final ViewingCreditBalance? initialBalance;
  final PaymentService? paymentService;

  @override
  State<CustomerViewingCreditScreen> createState() =>
      _CustomerViewingCreditScreenState();
}

class _CustomerViewingCreditScreenState
    extends State<CustomerViewingCreditScreen> {
  late final PaymentService _paymentService;
  late Future<ViewingCreditBalance> _balanceFuture;

  @override
  void initState() {
    super.initState();
    _paymentService = widget.paymentService ?? PaymentService();
    _balanceFuture = widget.initialBalance == null
        ? _paymentService.fetchViewingCreditBalance()
        : Future<ViewingCreditBalance>.value(widget.initialBalance);
  }

  Future<void> _refresh() async {
    setState(() {
      _balanceFuture = _paymentService.fetchViewingCreditBalance();
    });

    await _balanceFuture;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF4F7F4),
      appBar: AppBar(
        title: const Text('Viewing Credit'),
        backgroundColor: const Color(0xFF14532D),
        foregroundColor: Colors.white,
        actions: [
          IconButton(
            tooltip: 'Refresh credit balance',
            onPressed: _refresh,
            icon: const Icon(Icons.refresh_rounded),
          ),
        ],
      ),
      body: FutureBuilder<ViewingCreditBalance>(
        future: _balanceFuture,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }

          if (snapshot.hasError) {
            return _CreditErrorView(
              message: AppErrorMessage.forError(snapshot.error),
              onRetry: _refresh,
            );
          }

          final balance = snapshot.data!;
          final credits = balance.credits;

          return RefreshIndicator(
            onRefresh: _refresh,
            child: ListView(
              physics: const AlwaysScrollableScrollPhysics(),
              padding: const EdgeInsets.fromLTRB(18, 18, 18, 36),
              children: [
                ViewingCreditSummaryCard(balance: balance),
                const SizedBox(height: 16),
                const _CreditExplanationCard(),
                const SizedBox(height: 24),
                const Text(
                  'Credit activity',
                  style: TextStyle(
                    fontSize: 19,
                    fontWeight: FontWeight.bold,
                    color: Color(0xFF111827),
                  ),
                ),
                const SizedBox(height: 12),
                if (credits.isEmpty)
                  const _EmptyCreditActivity()
                else
                  ...credits.map(
                    (credit) => Padding(
                      padding: const EdgeInsets.only(bottom: 12),
                      child: _CreditActivityCard(credit: credit),
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

class ViewingCreditSummaryCard extends StatelessWidget {
  const ViewingCreditSummaryCard({
    super.key,
    required this.balance,
    this.onTap,
  });

  final ViewingCreditBalance? balance;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final availableAmount = balance?.availableAmount;
    final currency = balance?.currency.trim().isNotEmpty == true
        ? balance!.currency
        : 'KES';
    final amountLabel = availableAmount == null
        ? 'Balance unavailable'
        : '$currency ${_formatCreditAmount(availableAmount)}';
    final subtitle = availableAmount == null
        ? 'Tap to check your viewing credit.'
        : availableAmount > 0
        ? 'Available for your next property viewing.'
        : 'No viewing credit is currently available.';

    final content = Container(
      width: double.infinity,
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [Color(0xFF14532D), Color(0xFF2F7D32)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(20),
        boxShadow: const [
          BoxShadow(
            color: Color(0x22000000),
            blurRadius: 14,
            offset: Offset(0, 6),
          ),
        ],
      ),
      child: Row(
        children: [
          Container(
            width: 48,
            height: 48,
            decoration: BoxDecoration(
              color: Colors.white.withValues(alpha: 0.16),
              borderRadius: BorderRadius.circular(14),
            ),
            child: const Icon(
              Icons.account_balance_wallet_outlined,
              color: Colors.white,
            ),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Viewing Credit',
                  style: TextStyle(
                    color: Colors.white70,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  amountLabel,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 25,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  subtitle,
                  style: const TextStyle(color: Colors.white70, fontSize: 12),
                ),
              ],
            ),
          ),
          if (onTap != null)
            const Icon(Icons.chevron_right_rounded, color: Colors.white70),
        ],
      ),
    );

    if (onTap == null) {
      return content;
    }

    return Semantics(
      button: true,
      label: 'View viewing credit activity',
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(20),
        child: content,
      ),
    );
  }
}

class _CreditExplanationCard extends StatelessWidget {
  const _CreditExplanationCard();

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 0,
      color: const Color(0xFFF0FDF4),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: const BorderSide(color: Color(0xFFBBF7D0)),
      ),
      child: const Padding(
        padding: EdgeInsets.all(16),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(Icons.info_outline_rounded, color: Color(0xFF15803D)),
            SizedBox(width: 12),
            Expanded(
              child: Text(
                'When requesting another property viewing, choose “Use '
                'viewing credit” on the payment screen. If the credit does '
                'not cover the full fee, you pay only the difference.',
                style: TextStyle(color: Color(0xFF166534), height: 1.45),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _CreditActivityCard extends StatelessWidget {
  const _CreditActivityCard({required this.credit});

  final ViewingCredit credit;

  @override
  Widget build(BuildContext context) {
    final statusLabel = credit.isConsumed ? 'Used' : 'Available';
    final statusColor = credit.isConsumed
        ? const Color(0xFF6B7280)
        : const Color(0xFF15803D);

    return Card(
      elevation: 1,
      color: Colors.white,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Padding(
        padding: const EdgeInsets.all(17),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        credit.propertyTitle,
                        style: const TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.bold,
                          color: Color(0xFF111827),
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        'Issued ${_formatCreditDate(credit.issuedAt)}',
                        style: const TextStyle(
                          fontSize: 12,
                          color: Colors.black54,
                        ),
                      ),
                    ],
                  ),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 10,
                    vertical: 5,
                  ),
                  decoration: BoxDecoration(
                    color: statusColor.withValues(alpha: 0.10),
                    borderRadius: BorderRadius.circular(18),
                  ),
                  child: Text(
                    statusLabel,
                    style: TextStyle(
                      color: statusColor,
                      fontSize: 11,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 15),
            _CreditAmountRow(
              label: 'Credit issued',
              value: '${credit.currency} ${_formatCreditAmount(credit.amount)}',
            ),
            const SizedBox(height: 8),
            _CreditAmountRow(
              label: 'Credit used',
              value:
                  '${credit.currency} ${_formatCreditAmount(credit.usedAmount)}',
            ),
            const SizedBox(height: 8),
            _CreditAmountRow(
              label: 'Remaining',
              value:
                  '${credit.currency} ${_formatCreditAmount(credit.remainingAmount)}',
              emphasize: true,
            ),
            if (credit.reference.trim().isNotEmpty) ...[
              const SizedBox(height: 13),
              const Divider(height: 1),
              const SizedBox(height: 11),
              SelectableText(
                'Credit reference: ${credit.reference}',
                style: const TextStyle(fontSize: 11, color: Colors.black54),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _CreditAmountRow extends StatelessWidget {
  const _CreditAmountRow({
    required this.label,
    required this.value,
    this.emphasize = false,
  });

  final String label;
  final String value;
  final bool emphasize;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Expanded(
          child: Text(
            label,
            style: const TextStyle(color: Colors.black54, fontSize: 13),
          ),
        ),
        Text(
          value,
          style: TextStyle(
            color: emphasize
                ? const Color(0xFF14532D)
                : const Color(0xFF111827),
            fontWeight: FontWeight.bold,
          ),
        ),
      ],
    );
  }
}

class _EmptyCreditActivity extends StatelessWidget {
  const _EmptyCreditActivity();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: const Color(0xFFE5E7EB)),
      ),
      child: const Column(
        children: [
          Icon(
            Icons.account_balance_wallet_outlined,
            size: 46,
            color: Colors.black38,
          ),
          SizedBox(height: 12),
          Text(
            'No viewing credit activity yet',
            style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
          ),
          SizedBox(height: 6),
          Text(
            'Credits issued after an eligible viewing resolution will '
            'appear here.',
            textAlign: TextAlign.center,
            style: TextStyle(color: Colors.black54, height: 1.4),
          ),
        ],
      ),
    );
  }
}

class _CreditErrorView extends StatelessWidget {
  const _CreditErrorView({required this.message, required this.onRetry});

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
          const Icon(Icons.cloud_off_outlined, size: 66, color: Colors.black38),
          const SizedBox(height: 18),
          const Text(
            'Could not load viewing credit',
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 21, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 8),
          Text(
            message,
            textAlign: TextAlign.center,
            style: const TextStyle(color: Colors.black54),
          ),
          const SizedBox(height: 20),
          Center(
            child: FilledButton.icon(
              onPressed: onRetry,
              icon: const Icon(Icons.refresh_rounded),
              label: const Text('Try Again'),
            ),
          ),
        ],
      ),
    );
  }
}

String _formatCreditAmount(double amount) {
  if (amount == amount.roundToDouble()) {
    return amount.toStringAsFixed(0);
  }

  return amount.toStringAsFixed(2);
}

String _formatCreditDate(String value) {
  final parsed = DateTime.tryParse(value)?.toLocal();

  if (parsed == null) {
    return value.trim().isEmpty ? 'Date unavailable' : value;
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

  return '${parsed.day} ${months[parsed.month - 1]} ${parsed.year}';
}
