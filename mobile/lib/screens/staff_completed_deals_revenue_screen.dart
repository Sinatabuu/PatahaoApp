import 'package:flutter/material.dart';

import 'package:mobile/screens/staff_deal_detail_screen.dart';
import 'package:mobile/services/staff_commission_report_service.dart';

class StaffCompletedDealsRevenueScreen extends StatefulWidget {
  const StaffCompletedDealsRevenueScreen({super.key});

  @override
  State<StaffCompletedDealsRevenueScreen> createState() {
    return _StaffCompletedDealsRevenueScreenState();
  }
}

class _StaffCompletedDealsRevenueScreenState
    extends State<StaffCompletedDealsRevenueScreen> {
  bool _isLoading = true;
  String? _errorMessage;
  StaffCommissionReport? _report;

  final TextEditingController _searchController = TextEditingController();

  String _search = '';

  int _page = 1;
  static const int _pageSize = 50;

  bool _filtersExpanded = false;

  String _dealType = '';
  String _settlementStatus = '';
  String _payoutState = '';
  String _sort = 'newest_closed';

  DateTime? _closedFrom;
  DateTime? _closedTo;

  @override
  void initState() {
    super.initState();
    _loadReport();
  }

  Future<void> _loadReport() async {
    if (!mounted) {
      return;
    }

    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final report = await StaffCommissionReportService.instance.fetchReport(
        search: _search,
        dealType: _dealType,
        settlementStatus: _settlementStatus,
        payoutState: _payoutState,
        closedFrom: _apiDate(_closedFrom),
        closedTo: _apiDate(_closedTo),
        sort: _sort,
        page: _page,
        pageSize: _pageSize,
      );

      if (!mounted) {
        return;
      }

      setState(() {
        _report = report;
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

  Future<void> _runSearch() async {
    final value = _searchController.text.trim();

    if (!mounted) {
      return;
    }

    setState(() {
      _search = value;
      _page = 1;
    });

    await _loadReport();
  }

  Future<void> _clearSearch() async {
    _searchController.clear();

    if (!mounted) {
      return;
    }

    setState(() {
      _search = '';
      _page = 1;
    });

    await _loadReport();
  }

  Future<void> _nextPage() async {
    final report = _report;

    if (_isLoading || report == null || !report.hasNext) {
      return;
    }

    setState(() {
      _page++;
    });

    await _loadReport();
  }

  Future<void> _previousPage() async {
    final report = _report;

    if (_isLoading || report == null || !report.hasPrevious || _page <= 1) {
      return;
    }

    setState(() {
      _page--;
    });

    await _loadReport();
  }

  String _apiDate(DateTime? value) {
    if (value == null) {
      return '';
    }

    String twoDigits(int number) {
      return number.toString().padLeft(2, '0');
    }

    return '${value.year}-'
        '${twoDigits(value.month)}-'
        '${twoDigits(value.day)}';
  }

  Future<void> _pickClosedFrom() async {
    final picked = await showDatePicker(
      context: context,
      initialDate: _closedFrom ?? DateTime.now(),
      firstDate: DateTime(2000),
      lastDate: DateTime.now(),
    );

    if (picked == null || !mounted) {
      return;
    }

    setState(() {
      _closedFrom = picked;
    });
  }

  Future<void> _pickClosedTo() async {
    final picked = await showDatePicker(
      context: context,
      initialDate: _closedTo ?? DateTime.now(),
      firstDate: DateTime(2000),
      lastDate: DateTime.now(),
    );

    if (picked == null || !mounted) {
      return;
    }

    setState(() {
      _closedTo = picked;
    });
  }

  Future<void> _applyFilters() async {
    if (_closedFrom != null &&
        _closedTo != null &&
        _closedFrom!.isAfter(_closedTo!)) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Closed-from date cannot be after closed-to date.'),
        ),
      );
      return;
    }

    setState(() {
      _page = 1;
    });

    await _loadReport();
  }

  Future<void> _clearFilters() async {
    setState(() {
      _dealType = '';
      _settlementStatus = '';
      _payoutState = '';
      _sort = 'newest_closed';
      _closedFrom = null;
      _closedTo = null;
      _page = 1;
    });

    await _loadReport();
  }

  String _cleanError(Object error) {
    return error.toString().replaceFirst(RegExp(r'^Exception:\s*'), '').trim();
  }

  String _money(String currency, String rawAmount) {
    final amount = double.tryParse(rawAmount) ?? 0;

    final whole = amount == amount.roundToDouble();

    return '$currency '
        '${whole ? amount.toStringAsFixed(0) : amount.toStringAsFixed(2)}';
  }

  String _statusLabel(String value) {
    switch (value) {
      case 'completed':
        return 'Completed';
      case 'paid':
        return 'Paid';
      case 'partially_paid':
        return 'Partially paid';
      case 'approved':
        return 'Approved';
      case 'commission_paid':
        return 'Commission paid';
      default:
        if (value.trim().isEmpty) {
          return 'Not recorded';
        }

        return value
            .replaceAll('_', ' ')
            .split(' ')
            .map(
              (word) => word.isEmpty
                  ? word
                  : '${word[0].toUpperCase()}${word.substring(1)}',
            )
            .join(' ');
    }
  }

  String _formatDateTime(String raw) {
    if (raw.trim().isEmpty) {
      return 'Not recorded';
    }

    final parsed = DateTime.tryParse(raw);

    if (parsed == null) {
      return raw;
    }

    final local = parsed.toLocal();

    String twoDigits(int value) {
      return value.toString().padLeft(2, '0');
    }

    return '${local.year}-'
        '${twoDigits(local.month)}-'
        '${twoDigits(local.day)} '
        '${twoDigits(local.hour)}:'
        '${twoDigits(local.minute)}';
  }

  Future<void> _openDeal(StaffCommissionReportDeal deal) async {
    await Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) {
          return StaffDealDetailScreen(dealId: deal.dealId);
        },
      ),
    );

    if (!mounted) {
      return;
    }

    await _loadReport();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF6F8F6),
      appBar: AppBar(
        title: const Text('Completed Deals & Revenue'),
        backgroundColor: const Color(0xFF14532D),
        foregroundColor: Colors.white,
        actions: [
          IconButton(
            tooltip: 'Refresh',
            onPressed: _isLoading ? null : _loadReport,
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      body: RefreshIndicator(onRefresh: _loadReport, child: _buildBody()),
    );
  }

  Widget _buildBody() {
    if (_isLoading && _report == null) {
      return ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        children: const [
          SizedBox(height: 180),
          Center(child: CircularProgressIndicator()),
        ],
      );
    }

    if (_errorMessage != null && _report == null) {
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
              onPressed: _loadReport,
              icon: const Icon(Icons.refresh),
              label: const Text('Try Again'),
            ),
          ),
        ],
      );
    }

    final report = _report;

    if (report == null) {
      return const SizedBox.shrink();
    }

    return ListView(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.all(16),
      children: [
        const Text(
          'Commission Overview',
          style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
        ),

        const SizedBox(height: 4),

        const Text(
          'Backend-derived commission, payout, and '
          'retained revenue reporting.',
          style: TextStyle(color: Colors.black54),
        ),

        const SizedBox(height: 18),

        GridView.count(
          crossAxisCount: 2,
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          crossAxisSpacing: 12,
          mainAxisSpacing: 12,
          childAspectRatio: 1.18,
          children: [
            _RevenueSummaryCard(
              label: 'Completed deals',
              value: '${report.completedDeals}',
              icon: Icons.task_alt_outlined,
            ),
            _RevenueSummaryCard(
              label: 'Gross commission',
              value: _money(report.currency, report.grossCommission),
              icon: Icons.payments_outlined,
            ),
            _RevenueSummaryCard(
              label: 'Partner payouts',
              value: _money(report.currency, report.externalPayouts),
              icon: Icons.account_balance_wallet_outlined,
            ),
            _RevenueSummaryCard(
              label: 'Pata Hao retained',
              value: _money(report.currency, report.pataHaoRetainedRevenue),
              icon: Icons.savings_outlined,
            ),
          ],
        ),

        const SizedBox(height: 16),

        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Settlement Position',
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                ),

                const SizedBox(height: 12),

                _ReportRow(
                  label: 'Fully settled deals',
                  value: '${report.fullySettledDeals}',
                ),
                _ReportRow(
                  label: 'External allocations',
                  value: _money(report.currency, report.externalAllocations),
                ),
                _ReportRow(
                  label: 'Outstanding payouts',
                  value: _money(report.currency, report.outstandingPayouts),
                ),
              ],
            ),
          ),
        ),

        const SizedBox(height: 22),

        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Audit Search',
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                ),

                const SizedBox(height: 6),

                const Text(
                  'Search by deal number, property, customer, '
                  'partner, owner, invoice number, or payment reference.',
                  style: TextStyle(color: Colors.black54, fontSize: 13),
                ),

                const SizedBox(height: 12),

                TextField(
                  controller: _searchController,
                  textInputAction: TextInputAction.search,
                  onSubmitted: (_) {
                    _runSearch();
                  },
                  decoration: InputDecoration(
                    labelText: 'Search any audit reference',
                    hintText:
                        'e.g. PH-DEAL..., Garden Bush, Oti Star, invoice or payment ref',
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
                    label: const Text('Search Closed Deals'),
                  ),
                ),

                if (_search.isNotEmpty) ...[
                  const SizedBox(height: 10),
                  Text(
                    'Showing results for: "$_search"',
                    style: const TextStyle(color: Colors.black54, fontSize: 13),
                  ),
                ],
              ],
            ),
          ),
        ),

        const SizedBox(height: 12),

        Card(
          child: Column(
            children: [
              ListTile(
                leading: const Icon(Icons.tune, color: Color(0xFF14532D)),
                title: const Text(
                  'Advanced Filters',
                  style: TextStyle(fontWeight: FontWeight.w600),
                ),
                subtitle: const Text(
                  'Date, deal type, payout state, settlement and sorting',
                ),
                trailing: Icon(
                  _filtersExpanded ? Icons.expand_less : Icons.expand_more,
                ),
                onTap: () {
                  setState(() {
                    _filtersExpanded = !_filtersExpanded;
                  });
                },
              ),

              if (_filtersExpanded)
                Padding(
                  padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
                  child: Column(
                    children: [
                      DropdownButtonFormField<String>(
                        initialValue: _dealType,
                        decoration: const InputDecoration(
                          labelText: 'Deal type',
                          border: OutlineInputBorder(),
                        ),
                        items: const [
                          DropdownMenuItem(
                            value: '',
                            child: Text('All deal types'),
                          ),
                          DropdownMenuItem(
                            value: 'rental',
                            child: Text('Rental'),
                          ),
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
                        initialValue: _settlementStatus,
                        decoration: const InputDecoration(
                          labelText: 'Settlement status',
                          border: OutlineInputBorder(),
                        ),
                        items: const [
                          DropdownMenuItem(
                            value: '',
                            child: Text('All settlements'),
                          ),
                          DropdownMenuItem(
                            value: 'approved',
                            child: Text('Approved'),
                          ),
                          DropdownMenuItem(
                            value: 'partially_paid',
                            child: Text('Partially paid'),
                          ),
                          DropdownMenuItem(value: 'paid', child: Text('Paid')),
                        ],
                        onChanged: (value) {
                          setState(() {
                            _settlementStatus = value ?? '';
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
                          DropdownMenuItem(
                            value: 'fully_paid',
                            child: Text('Fully paid'),
                          ),
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

                      DropdownButtonFormField<String>(
                        initialValue: _sort,
                        decoration: const InputDecoration(
                          labelText: 'Sort',
                          border: OutlineInputBorder(),
                        ),
                        items: const [
                          DropdownMenuItem(
                            value: 'newest_closed',
                            child: Text('Newest closed first'),
                          ),
                          DropdownMenuItem(
                            value: 'oldest_closed',
                            child: Text('Oldest closed first'),
                          ),
                          DropdownMenuItem(
                            value: 'highest_commission',
                            child: Text('Highest commission first'),
                          ),
                          DropdownMenuItem(
                            value: 'lowest_commission',
                            child: Text('Lowest commission first'),
                          ),
                        ],
                        onChanged: (value) {
                          setState(() {
                            _sort = value ?? 'newest_closed';
                          });
                        },
                      ),

                      const SizedBox(height: 12),

                      Row(
                        children: [
                          Expanded(
                            child: OutlinedButton.icon(
                              onPressed: _pickClosedFrom,
                              icon: const Icon(Icons.calendar_today_outlined),
                              label: Text(
                                _closedFrom == null
                                    ? 'Closed from'
                                    : _apiDate(_closedFrom),
                              ),
                            ),
                          ),
                          const SizedBox(width: 10),
                          Expanded(
                            child: OutlinedButton.icon(
                              onPressed: _pickClosedTo,
                              icon: const Icon(Icons.event_outlined),
                              label: Text(
                                _closedTo == null
                                    ? 'Closed to'
                                    : _apiDate(_closedTo),
                              ),
                            ),
                          ),
                        ],
                      ),

                      const SizedBox(height: 14),

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
            ],
          ),
        ),

        const SizedBox(height: 22),

        Text(
          _search.isEmpty ? 'Recent Completed Deals' : 'Audit Search Results',
          style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
        ),

        const SizedBox(height: 10),

        if (report.recentDeals.isEmpty)
          const Card(
            child: Padding(
              padding: EdgeInsets.all(18),
              child: Text('No reportable completed deals yet.'),
            ),
          )
        else
          ...report.recentDeals.map(
            (deal) => _CompletedDealCard(
              deal: deal,
              moneyFormatter: _money,
              statusFormatter: _statusLabel,
              dateFormatter: _formatDateTime,
              onTap: () {
                _openDeal(deal);
              },
            ),
          ),

        if (report.count > 0) ...[
          const SizedBox(height: 18),

          Card(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
              child: Column(
                children: [
                  Text(
                    'Page ${report.page} of ${report.totalPages} '
                    '? ${report.count} matching deal'
                    '${report.count == 1 ? '' : 's'}',
                    textAlign: TextAlign.center,
                    style: const TextStyle(fontWeight: FontWeight.w600),
                  ),

                  const SizedBox(height: 10),

                  Row(
                    children: [
                      Expanded(
                        child: OutlinedButton.icon(
                          onPressed: !_isLoading && report.hasPrevious
                              ? _previousPage
                              : null,
                          icon: const Icon(Icons.chevron_left),
                          label: const Text('Previous'),
                        ),
                      ),

                      const SizedBox(width: 12),

                      Expanded(
                        child: FilledButton.icon(
                          onPressed: !_isLoading && report.hasNext
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

class _RevenueSummaryCard extends StatelessWidget {
  const _RevenueSummaryCard({
    required this.label,
    required this.value,
    required this.icon,
  });

  final String label;
  final String value;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Icon(icon, color: const Color(0xFF14532D)),
            Text(
              value,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
            ),
            Text(
              label,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(
                color: Colors.black54,
                fontWeight: FontWeight.w500,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _CompletedDealCard extends StatelessWidget {
  const _CompletedDealCard({
    required this.deal,
    required this.moneyFormatter,
    required this.statusFormatter,
    required this.dateFormatter,
    required this.onTap,
  });

  final StaffCommissionReportDeal deal;
  final String Function(String, String) moneyFormatter;
  final String Function(String) statusFormatter;
  final String Function(String) dateFormatter;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 10),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Text(
                      deal.propertyTitle.trim().isEmpty
                          ? deal.dealNumber
                          : deal.propertyTitle,
                      style: const TextStyle(
                        fontSize: 17,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                  const Icon(Icons.chevron_right),
                ],
              ),

              const SizedBox(height: 4),

              Text(
                deal.dealNumber,
                style: const TextStyle(color: Colors.black54, fontSize: 13),
              ),

              const SizedBox(height: 10),

              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: const Color(0xFFF8FAF8),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: Colors.black12),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Audit Identity',
                      style: TextStyle(fontWeight: FontWeight.bold),
                    ),

                    const SizedBox(height: 8),

                    _ReportRow(
                      label: 'Customer',
                      value: deal.customerName.trim().isEmpty
                          ? 'Not recorded'
                          : deal.customerName,
                    ),

                    _ReportRow(
                      label: 'Partner',
                      value: deal.partnerName.trim().isEmpty
                          ? 'Not recorded'
                          : deal.partnerName,
                    ),

                    _ReportRow(
                      label: 'Owner',
                      value: deal.ownerName.trim().isEmpty
                          ? 'Not recorded'
                          : deal.ownerName,
                    ),

                    _ReportRow(
                      label: 'Invoice',
                      value: deal.invoiceNumber.trim().isEmpty
                          ? 'Not recorded'
                          : deal.invoiceNumber,
                    ),
                  ],
                ),
              ),

              const SizedBox(height: 12),

              _ReportRow(
                label: 'Gross commission',
                value: moneyFormatter(deal.currency, deal.grossCommission),
              ),

              _ReportRow(
                label: 'Partner payouts',
                value: moneyFormatter(deal.currency, deal.externalPayouts),
              ),

              _ReportRow(
                label: 'Pata Hao retained',
                value: moneyFormatter(
                  deal.currency,
                  deal.pataHaoRetainedRevenue,
                ),
              ),

              _ReportRow(
                label: 'Outstanding',
                value: moneyFormatter(deal.currency, deal.outstandingPayouts),
              ),

              _ReportRow(
                label: 'Deal status',
                value: statusFormatter(deal.dealStatus),
              ),

              _ReportRow(
                label: 'Settlement',
                value: statusFormatter(deal.settlementStatus),
              ),

              if (deal.closedAt.isNotEmpty)
                _ReportRow(
                  label: 'Closed',
                  value: dateFormatter(deal.closedAt),
                ),
            ],
          ),
        ),
      ),
    );
  }
}

class _ReportRow extends StatelessWidget {
  const _ReportRow({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            child: Text(label, style: const TextStyle(color: Colors.black54)),
          ),
          const SizedBox(width: 12),
          Flexible(
            child: Text(
              value,
              textAlign: TextAlign.right,
              style: const TextStyle(fontWeight: FontWeight.w600),
            ),
          ),
        ],
      ),
    );
  }
}
