import 'package:flutter/material.dart';

import '../models/payment.dart';
import '../models/viewing.dart';
import '../services/payment_service.dart';
import '../services/viewing_service.dart';
import 'payment_success_screen.dart';

class CustomerReceiptsScreen extends StatefulWidget {
  const CustomerReceiptsScreen({super.key});

  @override
  State<CustomerReceiptsScreen> createState() => _CustomerReceiptsScreenState();
}

class _CustomerReceiptsScreenState extends State<CustomerReceiptsScreen> {
  final PaymentService _paymentService = PaymentService();

  final ViewingService _viewingService = ViewingService();

  late Future<List<_ReceiptRecord>> _receiptsFuture;

  @override
  void initState() {
    super.initState();
    _loadReceipts();
  }

  void _loadReceipts() {
    _receiptsFuture = _fetchReceipts();
  }

  Future<List<_ReceiptRecord>> _fetchReceipts() async {
    final results = await Future.wait<dynamic>([
      _paymentService.fetchPayments(),
      _viewingService.getMyViewings(),
    ]);

    final payments = results[0] as List<Payment>;
    final viewings = results[1] as List<Viewing>;

    final viewingsById = <int, Viewing>{
      for (final viewing in viewings) viewing.id: viewing,
    };

    final receipts = payments
        .where((payment) => payment.isSuccessful)
        .map(
          (payment) => _ReceiptRecord(
            payment: payment,
            viewing: viewingsById[payment.viewingId],
          ),
        )
        .toList();

    receipts.sort((first, second) {
      final firstDate = _paymentDate(first.payment);

      final secondDate = _paymentDate(second.payment);

      return secondDate.compareTo(firstDate);
    });

    return receipts;
  }

  static DateTime _paymentDate(Payment payment) {
    return DateTime.tryParse(payment.paidAt) ??
        DateTime.tryParse(payment.createdAt) ??
        DateTime.fromMillisecondsSinceEpoch(0);
  }

  Future<void> _refreshReceipts() async {
    setState(_loadReceipts);
    await _receiptsFuture;
  }

  Future<void> _openReceipt(_ReceiptRecord record) async {
    final viewing = record.viewing;

    if (viewing == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text(
            'The viewing details for this receipt '
            'could not be found.',
          ),
        ),
      );

      return;
    }

    Payment payment = record.payment;

    try {
      payment = await _paymentService.getViewingReceipt(viewingId: viewing.id);
    } catch (_) {
      // The payment list already contains a successful
      // payment, so its locally loaded receipt remains usable.
    }

    if (!mounted) {
      return;
    }

    await Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) =>
            PaymentSuccessScreen(viewing: viewing, payment: payment),
      ),
    );
  }

  String _cleanError(Object error) {
    return error.toString().replaceFirst('Exception: ', '').trim();
  }

  String _formatDate(Payment payment) {
    final parsed = _paymentDate(payment);

    if (parsed.millisecondsSinceEpoch == 0) {
      return 'Date unavailable';
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

  String _formatPaymentMethod(String value) {
    switch (value.trim().toLowerCase()) {
      case 'mpesa':
      case 'm_pesa':
        return 'M-Pesa';

      case 'airtel_money':
        return 'Airtel Money';

      case 'mobile_money':
        return 'Mobile Money';

      default:
        return value.replaceAll('_', ' ').trim();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF6F8F6),
      appBar: AppBar(
        title: const Text('Payment Receipts'),
        backgroundColor: const Color(0xFF14532D),
        foregroundColor: Colors.white,
        actions: [
          IconButton(
            tooltip: 'Refresh receipts',
            onPressed: _refreshReceipts,
            icon: const Icon(Icons.refresh_rounded),
          ),
        ],
      ),
      body: FutureBuilder<List<_ReceiptRecord>>(
        future: _receiptsFuture,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }

          if (snapshot.hasError) {
            return _ReceiptErrorView(
              message: _cleanError(snapshot.error!),
              onRetry: _refreshReceipts,
            );
          }

          final receipts = snapshot.data ?? <_ReceiptRecord>[];

          if (receipts.isEmpty) {
            return RefreshIndicator(
              onRefresh: _refreshReceipts,
              child: ListView(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: const EdgeInsets.all(24),
                children: const [
                  SizedBox(height: 110),
                  Icon(
                    Icons.receipt_long_outlined,
                    size: 78,
                    color: Color(0xFF34AD2C),
                  ),
                  SizedBox(height: 18),
                  Text(
                    'No receipts yet',
                    textAlign: TextAlign.center,
                    style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold),
                  ),
                  SizedBox(height: 10),
                  Text(
                    'Your successful viewing payments '
                    'will appear here automatically.',
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      color: Colors.black54,
                      fontSize: 15,
                      height: 1.5,
                    ),
                  ),
                ],
              ),
            );
          }

          return RefreshIndicator(
            onRefresh: _refreshReceipts,
            child: ListView.builder(
              physics: const AlwaysScrollableScrollPhysics(),
              padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
              itemCount: receipts.length,
              itemBuilder: (context, index) {
                final record = receipts[index];
                final payment = record.payment;
                final viewing = record.viewing;

                return Card(
                  margin: const EdgeInsets.only(bottom: 16),
                  elevation: 1,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(18),
                  ),
                  child: InkWell(
                    onTap: () => _openReceipt(record),
                    borderRadius: BorderRadius.circular(18),
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
                                  color: const Color(0xFFDCFCE7),
                                  borderRadius: BorderRadius.circular(14),
                                ),
                                child: const Icon(
                                  Icons.receipt_long_outlined,
                                  color: Color(0xFF15803D),
                                ),
                              ),
                              const SizedBox(width: 13),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      viewing?.propertyTitle
                                                  .trim()
                                                  .isNotEmpty ==
                                              true
                                          ? viewing!.propertyTitle
                                          : 'Viewing payment',
                                      style: const TextStyle(
                                        fontSize: 18,
                                        fontWeight: FontWeight.bold,
                                      ),
                                    ),
                                    const SizedBox(height: 5),
                                    Text(
                                      payment.displayReceiptNumber,
                                      style: const TextStyle(
                                        color: Colors.black54,
                                        fontSize: 13,
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                              const _PaidBadge(),
                            ],
                          ),
                          const SizedBox(height: 18),
                          _ReceiptInformationRow(
                            label: 'Amount',
                            value:
                                '${payment.currency} '
                                '${payment.amount.toStringAsFixed(0)}',
                            emphasize: true,
                          ),
                          const SizedBox(height: 10),
                          _ReceiptInformationRow(
                            label: 'Payment method',
                            value: _formatPaymentMethod(payment.paymentMethod),
                          ),
                          const SizedBox(height: 10),
                          _ReceiptInformationRow(
                            label: 'Payment date',
                            value: _formatDate(payment),
                          ),
                          if (payment.providerReceiptNumber
                              .trim()
                              .isNotEmpty) ...[
                            const SizedBox(height: 10),
                            _ReceiptInformationRow(
                              label: 'M-Pesa receipt',
                              value: payment.providerReceiptNumber,
                            ),
                          ],
                          const SizedBox(height: 16),
                          SizedBox(
                            width: double.infinity,
                            child: OutlinedButton.icon(
                              onPressed: () => _openReceipt(record),
                              icon: const Icon(Icons.visibility_outlined),
                              label: const Text('View Full Receipt'),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                );
              },
            ),
          );
        },
      ),
    );
  }
}

class _ReceiptRecord {
  const _ReceiptRecord({required this.payment, required this.viewing});

  final Payment payment;
  final Viewing? viewing;
}

class _PaidBadge extends StatelessWidget {
  const _PaidBadge();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: const Color(0xFFDCFCE7),
        borderRadius: BorderRadius.circular(18),
      ),
      child: const Text(
        'PAID',
        style: TextStyle(
          color: Color(0xFF166534),
          fontSize: 11,
          fontWeight: FontWeight.bold,
        ),
      ),
    );
  }
}

class _ReceiptInformationRow extends StatelessWidget {
  const _ReceiptInformationRow({
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

class _ReceiptErrorView extends StatelessWidget {
  const _ReceiptErrorView({required this.message, required this.onRetry});

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
            'Could not load your receipts',
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 21, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 10),
          Text(
            message,
            textAlign: TextAlign.center,
            style: const TextStyle(color: Colors.black54),
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
