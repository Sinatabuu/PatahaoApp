import 'package:flutter/material.dart';

import 'package:mobile/models/partner_commission.dart';

class PartnerCommissionSettlementDetailScreen extends StatelessWidget {
  const PartnerCommissionSettlementDetailScreen({
    super.key,
    required this.settlement,
  });

  final PartnerCommissionSettlement settlement;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Commission Settlement')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          _HeaderCard(settlement: settlement),
          const SizedBox(height: 16),

          const Text(
            'Your Commission',
            style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 10),

          Card(
            elevation: 0,
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                children: [
                  _DetailRow(
                    label: 'My share',
                    value: _money(settlement.myShare),
                  ),
                  const Divider(height: 24),
                  _DetailRow(
                    label: 'Percentage',
                    value: '${settlement.myPercentage.toStringAsFixed(2)}%',
                  ),
                  const Divider(height: 24),
                  _DetailRow(
                    label: 'Paid',
                    value: _money(settlement.myPaidAmount),
                  ),
                  const Divider(height: 24),
                  _DetailRow(
                    label: 'Outstanding',
                    value: _money(settlement.myOutstandingAmount),
                  ),
                  const Divider(height: 24),
                  _DetailRow(
                    label: 'Payment status',
                    value: _humanize(settlement.myPaymentStatus),
                  ),
                ],
              ),
            ),
          ),

          const SizedBox(height: 20),

          const Text(
            'Settlement',
            style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 10),

          Card(
            elevation: 0,
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                children: [
                  _DetailRow(
                    label: 'Agreement',
                    value: settlement.agreementNumber.isEmpty
                        ? 'Not available'
                        : settlement.agreementNumber,
                  ),
                  const Divider(height: 24),
                  _DetailRow(
                    label: 'Settlement status',
                    value: _humanize(settlement.status),
                  ),
                  const Divider(height: 24),
                  _DetailRow(
                    label: 'Participant type',
                    value: _humanize(settlement.myParticipantType),
                  ),
                ],
              ),
            ),
          ),

          const SizedBox(height: 20),

          const Text(
            'Payment History',
            style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 10),

          if (settlement.payments.isEmpty)
            const _NoPaymentsCard()
          else
            ...settlement.payments.map(
              (payment) => Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: _PaymentCard(payment: payment),
              ),
            ),
        ],
      ),
    );
  }
}

class _HeaderCard extends StatelessWidget {
  const _HeaderCard({required this.settlement});

  final PartnerCommissionSettlement settlement;

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 0,
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Icon(
              Icons.account_balance_wallet_outlined,
              size: 32,
              color: Color(0xFF2E8B28),
            ),
            const SizedBox(height: 12),
            Text(
              settlement.propertyTitle.isEmpty
                  ? 'Commission Settlement'
                  : settlement.propertyTitle,
              style: const TextStyle(fontSize: 21, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 6),
            Text(
              _humanize(settlement.status),
              style: const TextStyle(
                color: Color(0xFF2E8B28),
                fontWeight: FontWeight.w700,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _DetailRow extends StatelessWidget {
  const _DetailRow({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(
          width: 125,
          child: Text(label, style: const TextStyle(color: Colors.black54)),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Text(
            value.isEmpty ? 'Not available' : value,
            textAlign: TextAlign.right,
            style: const TextStyle(fontWeight: FontWeight.w600),
          ),
        ),
      ],
    );
  }
}

class _PaymentCard extends StatelessWidget {
  const _PaymentCard({required this.payment});

  final PartnerCommissionPayment payment;

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 0,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            _DetailRow(label: 'Amount', value: _money(payment.amount)),
            const Divider(height: 24),
            _DetailRow(
              label: 'Method',
              value: payment.paymentMethodLabel.isEmpty
                  ? _humanize(payment.paymentMethod)
                  : payment.paymentMethodLabel,
            ),
            const Divider(height: 24),
            _DetailRow(label: 'Reference', value: payment.paymentReference),
            const Divider(height: 24),
            _DetailRow(
              label: 'Paid at',
              value: _formatDateTime(payment.paidAt),
            ),
          ],
        ),
      ),
    );
  }
}

class _NoPaymentsCard extends StatelessWidget {
  const _NoPaymentsCard();

  @override
  Widget build(BuildContext context) {
    return const Card(
      elevation: 0,
      child: Padding(
        padding: EdgeInsets.all(18),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(Icons.schedule_outlined, color: Colors.black54),
            SizedBox(width: 12),
            Expanded(
              child: Text(
                'No commission payout has been recorded '
                'for your share yet.',
                style: TextStyle(color: Colors.black54, height: 1.4),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

String _money(double value) {
  return 'KES ${value.toStringAsFixed(2)}';
}

String _humanize(String value) {
  if (value.trim().isEmpty) {
    return 'Not available';
  }

  return value
      .trim()
      .replaceAll('_', ' ')
      .split(' ')
      .where((word) => word.isNotEmpty)
      .map(
        (word) => '${word[0].toUpperCase()}${word.substring(1).toLowerCase()}',
      )
      .join(' ');
}

String _formatDateTime(String value) {
  if (value.trim().isEmpty) {
    return 'Not available';
  }

  final parsed = DateTime.tryParse(value);

  if (parsed == null) {
    return value;
  }

  final local = parsed.toLocal();

  String twoDigits(int number) {
    return number.toString().padLeft(2, '0');
  }

  return '${local.year}-${twoDigits(local.month)}-'
      '${twoDigits(local.day)} '
      '${twoDigits(local.hour)}:${twoDigits(local.minute)}';
}
