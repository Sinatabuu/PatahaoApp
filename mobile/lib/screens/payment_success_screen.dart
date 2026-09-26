import 'package:flutter/material.dart';

import '../models/payment.dart';
import '../models/viewing.dart';

class PaymentSuccessScreen extends StatelessWidget {
  const PaymentSuccessScreen({
    super.key,
    required this.viewing,
    required this.payment,
  });

  final Viewing viewing;
  final Payment payment;
  bool get paymentSucceeded {
    final normalizedStatus = payment.status.toLowerCase();

    return normalizedStatus == 'successful' ||
        normalizedStatus == 'success' ||
        normalizedStatus == 'completed' ||
        normalizedStatus == 'paid';
  }

  String get confirmationTitle {
    return paymentSucceeded ? 'Viewing Confirmed' : 'Payment Pending';
  }

  String get confirmationMessage {
    if (!paymentSucceeded) {
      return 'Your payment is still being processed. '
          'The viewing will be confirmed after payment succeeds.';
    }

    if (payment.fullyCoveredByCredit) {
      return 'Your ${payment.currency} '
          '${payment.amount.toStringAsFixed(0)} viewing fee was covered by '
          'viewing credit. No M-Pesa payment was needed.';
    }

    if (payment.usedViewingCredit) {
      return '${payment.currency} '
          '${payment.creditAppliedAmount.toStringAsFixed(0)} viewing credit '
          'was applied and ${payment.currency} '
          '${payment.cashAmount.toStringAsFixed(0)} was paid by M-Pesa.';
    }

    return 'Your ${payment.currency} '
        '${payment.amount.toStringAsFixed(0)} viewing fee was received.';
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        automaticallyImplyLeading: false,
        title: const Text('Payment Receipt'),
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Icon(
                paymentSucceeded
                    ? Icons.check_circle
                    : Icons.hourglass_top_outlined,
                size: 90,
                color: paymentSucceeded
                    ? const Color(0xFF34AD2C)
                    : Colors.orange,
              ),
              const SizedBox(height: 16),
              Text(
                confirmationTitle,
                textAlign: TextAlign.center,
                style: const TextStyle(
                  fontSize: 28,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                confirmationMessage,
                textAlign: TextAlign.center,
                style: const TextStyle(fontSize: 16, color: Colors.black54),
              ),
              const SizedBox(height: 28),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(18),
                  child: Column(
                    children: [
                      _ReceiptRow(
                        label: 'Property',
                        value: viewing.propertyTitle,
                      ),
                      _ReceiptRow(
                        label: 'Viewing date',
                        value: viewing.requestedDate,
                      ),
                      _ReceiptRow(
                        label: 'Viewing time',
                        value: viewing.requestedTime,
                      ),
                      _ReceiptRow(
                        label: 'Total viewing fee',
                        value:
                            '${payment.currency} ${payment.amount.toStringAsFixed(2)}',
                      ),
                      if (payment.usedViewingCredit)
                        _ReceiptRow(
                          label: 'Viewing credit applied',
                          value:
                              '${payment.currency} '
                              '${payment.creditAppliedAmount.toStringAsFixed(2)}',
                        ),
                      if (payment.usedViewingCredit)
                        _ReceiptRow(
                          label: 'M-Pesa amount',
                          value:
                              '${payment.currency} '
                              '${payment.cashAmount.toStringAsFixed(2)}',
                        ),
                      _ReceiptRow(
                        label: 'Payment status',
                        value: payment.status.toUpperCase(),
                      ),
                      _ReceiptRow(
                        label: 'Pata Hao reference',
                        value: payment.paymentReference.isEmpty
                            ? 'Pending'
                            : payment.paymentReference,
                      ),
                      if (payment.providerReceiptNumber.isNotEmpty)
                        _ReceiptRow(
                          label: 'Provider receipt',
                          value: payment.providerReceiptNumber,
                        ),
                      if (payment.providerTransactionId.isNotEmpty)
                        _ReceiptRow(
                          label: 'Transaction ID',
                          value: payment.providerTransactionId,
                        ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 24),
              const Card(
                child: Padding(
                  padding: EdgeInsets.all(18),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Icon(Icons.info_outline, color: Color(0xFF14532D)),
                      SizedBox(width: 12),
                      Expanded(
                        child: Text(
                          'Keep this receipt. The property partner '
                          'will use the confirmed reservation when '
                          'coordinating your viewing.',
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 24),
              SizedBox(
                height: 54,
                child: FilledButton(
                  onPressed: () {
                    Navigator.of(context).popUntil((route) => route.isFirst);
                  },
                  child: const Text(
                    'Return to Properties',
                    style: TextStyle(fontSize: 17),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _ReceiptRow extends StatelessWidget {
  const _ReceiptRow({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 9),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            child: Text(label, style: const TextStyle(color: Colors.black54)),
          ),
          const SizedBox(width: 12),
          Flexible(
            child: SelectableText(
              value,
              textAlign: TextAlign.end,
              style: const TextStyle(fontWeight: FontWeight.bold),
            ),
          ),
        ],
      ),
    );
  }
}
