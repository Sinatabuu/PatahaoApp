import 'package:flutter/material.dart';

import 'package:mobile/models/partner_transaction_history.dart';
import 'package:mobile/services/partner_transaction_history_service.dart';

class PartnerTransactionHistoryScreen extends StatefulWidget {
  const PartnerTransactionHistoryScreen({super.key});

  @override
  State<PartnerTransactionHistoryScreen> createState() {
    return _PartnerTransactionHistoryScreenState();
  }
}

class _PartnerTransactionHistoryScreenState
    extends State<PartnerTransactionHistoryScreen> {
  final TextEditingController _searchController = TextEditingController();

  bool _isLoading = true;
  String? _errorMessage;

  PartnerTransactionHistoryPage? _history;

  String _search = '';
  String _dealType = '';
  String _payoutState = '';

  int _page = 1;
  static const int _pageSize = 25;

  @override
  void initState() {
    super.initState();
    _loadHistory();
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _loadHistory() async {
    if (!mounted) {
      return;
    }

    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final history = await PartnerTransactionHistoryService.instance
          .fetchHistory(
            search: _search,
            dealType: _dealType,
            payoutState: _payoutState,
            page: _page,
            pageSize: _pageSize,
          );

      if (!mounted) {
        return;
      }

      setState(() {
        _history = history;
        _isLoading = false;
      });
    } catch (error) {
      if (!mounted) {
        return;
      }

      setState(() {
        _isLoading = false;
        _errorMessage = _cleanError(error);
      });
    }
  }

  String _cleanError(Object error) {
    return error.toString().replaceFirst(RegExp(r'^Exception:\s*'), '').trim();
  }

  Future<void> _runSearch() async {
    setState(() {
      _search = _searchController.text.trim();
      _page = 1;
    });

    await _loadHistory();
  }

  Future<void> _clearSearch() async {
    _searchController.clear();

    setState(() {
      _search = '';
      _page = 1;
    });

    await _loadHistory();
  }

  Future<void> _applyFilters() async {
    setState(() {
      _page = 1;
    });

    await _loadHistory();
  }

  Future<void> _clearFilters() async {
    setState(() {
      _dealType = '';
      _payoutState = '';
      _page = 1;
    });

    await _loadHistory();
  }

  Future<void> _nextPage() async {
    final history = _history;

    if (_isLoading || history == null || !history.hasNext) {
      return;
    }

    setState(() {
      _page++;
    });

    await _loadHistory();
  }

  Future<void> _previousPage() async {
    final history = _history;

    if (_isLoading || history == null || !history.hasPrevious || _page <= 1) {
      return;
    }

    setState(() {
      _page--;
    });

    await _loadHistory();
  }

  String _money(String currency, double amount) {
    final whole = amount == amount.roundToDouble();

    return '$currency '
        '${whole ? amount.toStringAsFixed(0) : amount.toStringAsFixed(2)}';
  }

  String _statusLabel(String value) {
    if (value.trim().isEmpty) {
      return 'Not recorded';
    }

    return value
        .replaceAll('_', ' ')
        .split(' ')
        .map(
          (word) => word.isEmpty
              ? word
              : '${word[0].toUpperCase()}'
                    '${word.substring(1)}',
        )
        .join(' ');
  }

  String _date(String raw) {
    if (raw.trim().isEmpty) {
      return 'Not recorded';
    }

    final parsed = DateTime.tryParse(raw);

    if (parsed == null) {
      return raw;
    }

    final local = parsed.toLocal();

    String two(int value) {
      return value.toString().padLeft(2, '0');
    }

    return '${local.year}-'
        '${two(local.month)}-'
        '${two(local.day)}';
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF6F8F6),
      appBar: AppBar(
        title: const Text('Transaction History'),
        backgroundColor: const Color(0xFF14532D),
        foregroundColor: Colors.white,
        actions: [
          IconButton(
            tooltip: 'Refresh',
            onPressed: _isLoading ? null : _loadHistory,
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      body: RefreshIndicator(onRefresh: _loadHistory, child: _buildBody()),
    );
  }

  Widget _buildBody() {
    if (_isLoading && _history == null) {
      return ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        children: const [
          SizedBox(height: 180),
          Center(child: CircularProgressIndicator()),
        ],
      );
    }

    if (_errorMessage != null && _history == null) {
      return ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(24),
        children: [
          const SizedBox(height: 100),
          const Icon(Icons.error_outline, size: 52, color: Color(0xFFB45309)),
          const SizedBox(height: 14),
          Text(_errorMessage!, textAlign: TextAlign.center),
          const SizedBox(height: 16),
          Center(
            child: FilledButton.icon(
              onPressed: _loadHistory,
              icon: const Icon(Icons.refresh),
              label: const Text('Try Again'),
            ),
          ),
        ],
      );
    }

    final history = _history;

    if (history == null) {
      return const SizedBox.shrink();
    }

    return ListView(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.all(16),
      children: [
        const Text(
          'My Completed Transactions',
          style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
        ),

        const SizedBox(height: 4),

        const Text(
          'Closed Pata Hao transactions linked to your '
          'partner account and your own payout evidence.',
          style: TextStyle(color: Colors.black54),
        ),

        const SizedBox(height: 18),

        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              children: [
                TextField(
                  controller: _searchController,
                  textInputAction: TextInputAction.search,
                  onSubmitted: (_) {
                    _runSearch();
                  },
                  decoration: InputDecoration(
                    labelText: 'Search transaction history',
                    hintText:
                        'Deal number, property, customer or payout reference',
                    prefixIcon: const Icon(Icons.search),
                    suffixIcon: _search.isNotEmpty
                        ? IconButton(
                            tooltip: 'Clear search',
                            onPressed: _clearSearch,
                            icon: const Icon(Icons.close),
                          )
                        : null,
                    border: const OutlineInputBorder(),
                  ),
                ),

                const SizedBox(height: 10),

                SizedBox(
                  width: double.infinity,
                  child: FilledButton.icon(
                    onPressed: _isLoading ? null : _runSearch,
                    icon: const Icon(Icons.manage_search),
                    label: const Text('Search Transactions'),
                  ),
                ),
              ],
            ),
          ),
        ),

        const SizedBox(height: 12),

        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              children: [
                DropdownButtonFormField<String>(
                  initialValue: _dealType,
                  decoration: const InputDecoration(
                    labelText: 'Deal type',
                    border: OutlineInputBorder(),
                  ),
                  items: const [
                    DropdownMenuItem(value: '', child: Text('All deal types')),
                    DropdownMenuItem(value: 'rental', child: Text('Rental')),
                    DropdownMenuItem(value: 'sale', child: Text('Sale')),
                  ],
                  onChanged: (value) {
                    setState(() {
                      _dealType = value ?? '';
                    });
                  },
                ),

                const SizedBox(height: 12),

                DropdownButtonFormField<String>(
                  initialValue: _payoutState,
                  decoration: const InputDecoration(
                    labelText: 'Payout state',
                    border: OutlineInputBorder(),
                  ),
                  items: const [
                    DropdownMenuItem(
                      value: '',
                      child: Text('All payout states'),
                    ),
                    DropdownMenuItem(value: 'paid', child: Text('Paid')),
                    DropdownMenuItem(
                      value: 'outstanding',
                      child: Text('Outstanding'),
                    ),
                  ],
                  onChanged: (value) {
                    setState(() {
                      _payoutState = value ?? '';
                    });
                  },
                ),

                const SizedBox(height: 12),

                Row(
                  children: [
                    Expanded(
                      child: OutlinedButton(
                        onPressed: _isLoading ? null : _clearFilters,
                        child: const Text('Clear Filters'),
                      ),
                    ),

                    const SizedBox(width: 10),

                    Expanded(
                      child: FilledButton.icon(
                        onPressed: _isLoading ? null : _applyFilters,
                        icon: const Icon(Icons.filter_alt),
                        label: const Text('Apply Filters'),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),

        const SizedBox(height: 20),

        Text(
          history.count == 1
              ? '1 completed transaction'
              : '${history.count} completed transactions',
          style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
        ),

        const SizedBox(height: 10),

        if (history.results.isEmpty)
          const Card(
            child: Padding(
              padding: EdgeInsets.all(18),
              child: Text(
                'No completed transactions match '
                'your current search or filters.',
              ),
            ),
          )
        else
          ...history.results.map(
            (transaction) => _TransactionCard(
              transaction: transaction,
              moneyFormatter: _money,
              statusFormatter: _statusLabel,
              dateFormatter: _date,
            ),
          ),

        if (history.count > 0) ...[
          const SizedBox(height: 18),

          Card(
            child: Padding(
              padding: const EdgeInsets.all(14),
              child: Column(
                children: [
                  Text(
                    'Page ${history.page} of '
                    '${history.totalPages}',
                    style: const TextStyle(fontWeight: FontWeight.w600),
                  ),

                  const SizedBox(height: 10),

                  Row(
                    children: [
                      Expanded(
                        child: OutlinedButton.icon(
                          onPressed: !_isLoading && history.hasPrevious
                              ? _previousPage
                              : null,
                          icon: const Icon(Icons.chevron_left),
                          label: const Text('Previous'),
                        ),
                      ),

                      const SizedBox(width: 10),

                      Expanded(
                        child: FilledButton.icon(
                          onPressed: !_isLoading && history.hasNext
                              ? _nextPage
                              : null,
                          icon: const Icon(Icons.chevron_right),
                          label: const Text('Next'),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ],

        const SizedBox(height: 24),
      ],
    );
  }
}

class _TransactionCard extends StatelessWidget {
  const _TransactionCard({
    required this.transaction,
    required this.moneyFormatter,
    required this.statusFormatter,
    required this.dateFormatter,
  });

  final PartnerTransactionHistoryItem transaction;

  final String Function(String currency, double amount) moneyFormatter;

  final String Function(String value) statusFormatter;

  final String Function(String value) dateFormatter;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    transaction.propertyTitle.trim().isEmpty
                        ? transaction.dealNumber
                        : transaction.propertyTitle,
                    style: const TextStyle(
                      fontSize: 17,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
                const Icon(Icons.history, color: Color(0xFF14532D)),
              ],
            ),

            const SizedBox(height: 4),

            Text(
              transaction.dealNumber,
              style: const TextStyle(color: Colors.black54, fontSize: 13),
            ),

            const SizedBox(height: 12),

            _HistoryRow(
              label: 'Customer',
              value: transaction.customerName.isEmpty
                  ? 'Not recorded'
                  : transaction.customerName,
            ),

            _HistoryRow(
              label: 'Deal type',
              value: statusFormatter(transaction.dealType),
            ),

            _HistoryRow(
              label: 'Closed',
              value: dateFormatter(transaction.closedAt),
            ),

            const Divider(height: 24),

            const Text(
              'My Commission',
              style: TextStyle(fontWeight: FontWeight.bold),
            ),

            const SizedBox(height: 8),

            _HistoryRow(
              label: 'My share',
              value: moneyFormatter(transaction.currency, transaction.myShare),
            ),

            _HistoryRow(
              label: 'Paid',
              value: moneyFormatter(
                transaction.currency,
                transaction.paidAmount,
              ),
            ),

            _HistoryRow(
              label: 'Outstanding',
              value: moneyFormatter(
                transaction.currency,
                transaction.outstandingAmount,
              ),
            ),

            _HistoryRow(
              label: 'Settlement',
              value: statusFormatter(transaction.settlementStatus),
            ),

            if (transaction.payments.isNotEmpty) ...[
              const Divider(height: 24),

              const Text(
                'Payout Evidence',
                style: TextStyle(fontWeight: FontWeight.bold),
              ),

              const SizedBox(height: 8),

              ...transaction.payments.map(
                (payment) => Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: Column(
                    children: [
                      _HistoryRow(
                        label: 'Reference',
                        value: payment.paymentReference.isEmpty
                            ? 'Not recorded'
                            : payment.paymentReference,
                      ),
                      _HistoryRow(
                        label: 'Amount',
                        value: moneyFormatter(
                          payment.currency.isEmpty
                              ? transaction.currency
                              : payment.currency,
                          payment.amount,
                        ),
                      ),
                      _HistoryRow(
                        label: 'Paid',
                        value: dateFormatter(payment.paidAt),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _HistoryRow extends StatelessWidget {
  const _HistoryRow({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 105,
            child: Text(label, style: const TextStyle(color: Colors.black54)),
          ),
          Expanded(
            child: Text(
              value,
              textAlign: TextAlign.right,
              style: const TextStyle(fontWeight: FontWeight.w500),
            ),
          ),
        ],
      ),
    );
  }
}
