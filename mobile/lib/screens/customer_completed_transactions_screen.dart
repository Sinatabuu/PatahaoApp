import 'package:flutter/material.dart';
import 'package:mobile/models/customer_completed_transaction.dart';
import 'package:mobile/services/deal_service.dart';

class CustomerCompletedTransactionsScreen extends StatefulWidget {
  const CustomerCompletedTransactionsScreen({super.key});

  @override
  State<CustomerCompletedTransactionsScreen> createState() {
    return _CustomerCompletedTransactionsScreenState();
  }
}

class _CustomerCompletedTransactionsScreenState
    extends State<CustomerCompletedTransactionsScreen> {
  bool _isLoading = true;
  String? _errorMessage;

  List<CustomerCompletedTransaction> _transactions = [];

  @override
  void initState() {
    super.initState();
    _loadTransactions();
  }

  Future<void> _loadTransactions() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final transactions = await DealService.instance
          .fetchCompletedTransactions();

      if (!mounted) {
        return;
      }

      setState(() {
        _transactions = transactions;
        _isLoading = false;
      });
    } catch (error) {
      if (!mounted) {
        return;
      }

      setState(() {
        _errorMessage = error.toString().replaceFirst('Exception: ', '');

        _isLoading = false;
      });
    }
  }

  String _formatDate(String value) {
    if (value.trim().isEmpty) {
      return 'Date not recorded';
    }

    final parsed = DateTime.tryParse(value);

    if (parsed == null) {
      return value;
    }

    const months = [
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

    final local = parsed.toLocal();

    return '${local.day} '
        '${months[local.month - 1]} '
        '${local.year}';
  }

  Widget _buildBody() {
    if (_isLoading && _transactions.isEmpty) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_errorMessage != null && _transactions.isEmpty) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.error_outline, size: 52, color: Colors.black38),
              const SizedBox(height: 16),
              Text(_errorMessage!, textAlign: TextAlign.center),
              const SizedBox(height: 16),
              FilledButton.icon(
                onPressed: _loadTransactions,
                icon: const Icon(Icons.refresh),
                label: const Text('Try again'),
              ),
            ],
          ),
        ),
      );
    }

    if (_transactions.isEmpty) {
      return RefreshIndicator(
        onRefresh: _loadTransactions,
        child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(24),
          children: const [
            SizedBox(height: 100),
            Icon(Icons.receipt_long_outlined, size: 64, color: Colors.black26),
            SizedBox(height: 16),
            Text(
              'No completed transactions yet.',
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.w600),
            ),
            SizedBox(height: 8),
            Text(
              'Completed rentals or property purchases '
              'will appear here.',
              textAlign: TextAlign.center,
              style: TextStyle(color: Colors.black54),
            ),
          ],
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: _loadTransactions,
      child: ListView.separated(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(16),
        itemCount: _transactions.length,
        separatorBuilder: (_, _) {
          return const SizedBox(height: 10);
        },
        itemBuilder: (context, index) {
          final transaction = _transactions[index];

          return Card(
            child: Padding(
              padding: const EdgeInsets.all(18),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    transaction.propertyTitle,
                    style: const TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    transaction.dealTypeLabel,
                    style: const TextStyle(color: Colors.black54),
                  ),
                  const SizedBox(height: 14),
                  Row(
                    children: [
                      const Icon(Icons.tag, size: 18, color: Colors.black45),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          transaction.dealNumber.isEmpty
                              ? 'Deal reference unavailable'
                              : transaction.dealNumber,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 10),
                  Row(
                    children: [
                      const Icon(
                        Icons.groups_outlined,
                        size: 18,
                        color: Colors.black45,
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          transaction.partnerName.isEmpty
                              ? 'Pata Hao partner'
                              : transaction.partnerName,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 14),
                  Row(
                    children: [
                      const Icon(
                        Icons.check_circle_outline,
                        size: 20,
                        color: Color(0xFF15803D),
                      ),
                      const SizedBox(width: 8),
                      Text(
                        'Completed',
                        style: const TextStyle(
                          color: Color(0xFF15803D),
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                      const Spacer(),
                      Text(
                        _formatDate(transaction.completedAt),
                        style: const TextStyle(color: Colors.black54),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Completed Transactions'),
        actions: [
          IconButton(
            onPressed: _isLoading ? null : _loadTransactions,
            tooltip: 'Refresh',
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      body: _buildBody(),
    );
  }
}
