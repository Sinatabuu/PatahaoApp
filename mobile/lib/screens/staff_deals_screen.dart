import 'dart:async';

import 'package:flutter/material.dart';

import 'package:mobile/services/staff_deal_admin_service.dart';
import 'package:mobile/screens/staff_deal_detail_screen.dart';

class StaffDealsScreen extends StatefulWidget {
  const StaffDealsScreen({super.key});

  @override
  State<StaffDealsScreen> createState() {
    return _StaffDealsScreenState();
  }
}

class _StaffDealsScreenState extends State<StaffDealsScreen> {
  final TextEditingController _searchController = TextEditingController();

  Timer? _searchDebounce;

  bool _isLoading = true;
  String? _errorMessage;

  List<Map<String, dynamic>> _deals = [];

  int _page = 1;
  int _pageSize = 25;
  int _count = 0;
  int _totalPages = 0;
  bool _hasNext = false;
  bool _hasPrevious = false;

  String _statusFilter = '';
  String _dealTypeFilter = '';

  static const List<_DealFilter> _statusFilters = [
    _DealFilter(label: 'All', value: ''),
    _DealFilter(label: 'Awaiting', value: 'awaiting_confirmations'),
    _DealFilter(label: 'Negotiating', value: 'negotiating'),
    _DealFilter(label: 'Agreed', value: 'agreed'),
    _DealFilter(label: 'Documents', value: 'documents_pending'),
    _DealFilter(label: 'Commission due', value: 'commission_due'),
    _DealFilter(label: 'Commission paid', value: 'commission_paid'),
    _DealFilter(label: 'Completed', value: 'completed'),
    _DealFilter(label: 'Disputed', value: 'disputed'),
    _DealFilter(label: 'Cancelled', value: 'cancelled'),
  ];

  @override
  void initState() {
    super.initState();

    _searchController.addListener(_handleSearchChanged);

    _loadDeals();
  }

  @override
  void dispose() {
    _searchDebounce?.cancel();

    _searchController
      ..removeListener(_handleSearchChanged)
      ..dispose();

    super.dispose();
  }

  void _handleSearchChanged() {
    _searchDebounce?.cancel();

    _searchDebounce = Timer(const Duration(milliseconds: 450), () {
      if (!mounted) {
        return;
      }

      _page = 1;
      _loadDeals();
    });
  }

  Future<void> _loadDeals() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final response = await StaffDealAdminService.instance.fetchDeals(
        search: _searchController.text,
        status: _statusFilter,
        dealType: _dealTypeFilter,
        page: _page,
        pageSize: _pageSize,
      );

      final rawResults = response['results'];

      final deals = <Map<String, dynamic>>[];

      if (rawResults is List) {
        for (final item in rawResults) {
          if (item is Map) {
            deals.add(Map<String, dynamic>.from(item));
          }
        }
      }

      if (!mounted) {
        return;
      }

      setState(() {
        _deals = deals;
        _count = _parseInt(response['count']);
        _page = _parseInt(response['page'], fallback: 1);
        _pageSize = _parseInt(response['page_size'], fallback: 25);
        _totalPages = _parseInt(response['total_pages']);
        _hasNext = response['has_next'] == true;
        _hasPrevious = response['has_previous'] == true;

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

  Future<void> _previousPage() async {
    if (!_hasPrevious || _isLoading) {
      return;
    }

    setState(() {
      _page--;
    });

    await _loadDeals();
  }

  Future<void> _nextPage() async {
    if (!_hasNext || _isLoading) {
      return;
    }

    setState(() {
      _page++;
    });

    await _loadDeals();
  }

  void _setStatusFilter(String value) {
    if (_statusFilter == value) {
      return;
    }

    setState(() {
      _statusFilter = value;
      _page = 1;
    });

    _loadDeals();
  }

  void _setDealTypeFilter(String value) {
    if (_dealTypeFilter == value) {
      return;
    }

    setState(() {
      _dealTypeFilter = value;
      _page = 1;
    });

    _loadDeals();
  }

  void _clearFilters() {
    _searchController.clear();

    setState(() {
      _statusFilter = '';
      _dealTypeFilter = '';
      _page = 1;
    });

    _loadDeals();
  }

  bool get _hasFilters {
    return _searchController.text.trim().isNotEmpty ||
        _statusFilter.isNotEmpty ||
        _dealTypeFilter.isNotEmpty;
  }

  int _parseInt(dynamic value, {int fallback = 0}) {
    if (value is int) {
      return value;
    }

    return int.tryParse(value?.toString() ?? '') ?? fallback;
  }

  String _text(Map<String, dynamic> item, String key) {
    final value = item[key];

    if (value == null) {
      return '';
    }

    return value.toString().trim();
  }

  String _cleanError(Object error) {
    final text = error.toString();

    if (text.startsWith('Exception: ')) {
      return text.substring('Exception: '.length);
    }

    return text;
  }

  String _statusLabel(String status) {
    switch (status) {
      case 'draft':
        return 'Draft';

      case 'awaiting_customer':
        return 'Awaiting customer';

      case 'awaiting_owner':
        return 'Awaiting owner';

      case 'awaiting_confirmations':
        return 'Awaiting confirmations';

      case 'negotiating':
        return 'Negotiating';

      case 'agreed':
        return 'Agreed';

      case 'documents_pending':
        return 'Documents pending';

      case 'commission_due':
        return 'Commission due';

      case 'commission_paid':
        return 'Commission paid';

      case 'completed':
        return 'Completed';

      case 'cancelled':
        return 'Cancelled';

      case 'disputed':
        return 'Disputed';

      default:
        if (status.isEmpty) {
          return 'Unknown';
        }

        return status
            .replaceAll('_', ' ')
            .split(' ')
            .map((word) {
              if (word.isEmpty) {
                return word;
              }

              return '${word[0].toUpperCase()}'
                  '${word.substring(1)}';
            })
            .join(' ');
    }
  }

  Color _statusColor(String status) {
    switch (status) {
      case 'agreed':
      case 'commission_paid':
      case 'completed':
        return const Color(0xFF15803D);

      case 'commission_due':
      case 'documents_pending':
      case 'negotiating':
        return const Color(0xFFB45309);

      case 'disputed':
        return const Color(0xFFB91C1C);

      case 'cancelled':
        return Colors.grey.shade700;

      case 'awaiting_customer':
      case 'awaiting_owner':
      case 'awaiting_confirmations':
        return const Color(0xFF1D4ED8);

      default:
        return Colors.blueGrey;
    }
  }

  String _dealTypeLabel(String dealType) {
    switch (dealType) {
      case 'rental':
        return 'Rental';

      case 'sale':
        return 'Sale';

      default:
        return 'Not set';
    }
  }

  String _formatMoney(dynamic value) {
    if (value == null) {
      return 'Not set';
    }

    final amount = double.tryParse(value.toString());

    if (amount == null) {
      return 'Not set';
    }

    final whole = amount.round();

    final formatted = whole.toString().replaceAllMapped(
      RegExp(r'\B(?=(\d{3})+(?!\d))'),
      (match) => ',',
    );

    return 'KES $formatted';
  }

  Widget _buildFilters() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        TextField(
          controller: _searchController,
          decoration: InputDecoration(
            hintText: 'Search deal, property, customer or partner',
            prefixIcon: const Icon(Icons.search),
            suffixIcon: _searchController.text.isNotEmpty
                ? IconButton(
                    onPressed: () {
                      _searchController.clear();
                    },
                    icon: const Icon(Icons.close),
                  )
                : null,
            border: const OutlineInputBorder(),
          ),
        ),
        const SizedBox(height: 12),
        SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          child: Row(
            children: _statusFilters.map((filter) {
              final selected = _statusFilter == filter.value;

              return Padding(
                padding: const EdgeInsets.only(right: 8),
                child: ChoiceChip(
                  label: Text(filter.label),
                  selected: selected,
                  onSelected: (_) {
                    _setStatusFilter(filter.value);
                  },
                ),
              );
            }).toList(),
          ),
        ),
        const SizedBox(height: 10),
        Row(
          children: [
            Expanded(
              child: DropdownButtonFormField<String>(
                initialValue: _dealTypeFilter,
                decoration: const InputDecoration(
                  labelText: 'Deal type',
                  border: OutlineInputBorder(),
                  isDense: true,
                ),
                items: const [
                  DropdownMenuItem(value: '', child: Text('All deal types')),
                  DropdownMenuItem(value: 'rental', child: Text('Rental')),
                  DropdownMenuItem(value: 'sale', child: Text('Sale')),
                ],
                onChanged: (value) {
                  _setDealTypeFilter(value ?? '');
                },
              ),
            ),
            if (_hasFilters) ...[
              const SizedBox(width: 10),
              TextButton.icon(
                onPressed: _clearFilters,
                icon: const Icon(Icons.filter_alt_off_outlined),
                label: const Text('Clear'),
              ),
            ],
          ],
        ),
      ],
    );
  }

  Widget _buildPagination() {
    if (_totalPages <= 1) {
      return const SizedBox.shrink();
    }

    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        OutlinedButton.icon(
          onPressed: _hasPrevious && !_isLoading ? _previousPage : null,
          icon: const Icon(Icons.chevron_left),
          label: const Text('Previous'),
        ),
        Text(
          'Page $_page of $_totalPages',
          style: const TextStyle(fontWeight: FontWeight.w600),
        ),
        OutlinedButton.icon(
          onPressed: _hasNext && !_isLoading ? _nextPage : null,
          iconAlignment: IconAlignment.end,
          icon: const Icon(Icons.chevron_right),
          label: const Text('Next'),
        ),
      ],
    );
  }

  Widget _buildBody() {
    if (_isLoading && _deals.isEmpty) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_errorMessage != null && _deals.isEmpty) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(
                Icons.error_outline,
                size: 48,
                color: Colors.redAccent,
              ),
              const SizedBox(height: 12),
              Text(_errorMessage!, textAlign: TextAlign.center),
              const SizedBox(height: 16),
              FilledButton.icon(
                onPressed: _loadDeals,
                icon: const Icon(Icons.refresh),
                label: const Text('Try again'),
              ),
            ],
          ),
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: _loadDeals,
      child: ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(16),
        children: [
          _buildFilters(),
          const SizedBox(height: 14),
          Row(
            children: [
              Text(
                '$_count deals',
                style: const TextStyle(fontWeight: FontWeight.w600),
              ),
              const Spacer(),
              if (_isLoading)
                const SizedBox(
                  width: 18,
                  height: 18,
                  child: CircularProgressIndicator(strokeWidth: 2),
                ),
            ],
          ),
          const SizedBox(height: 12),

          if (_errorMessage != null)
            Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: Material(
                color: Colors.red.shade50,
                borderRadius: BorderRadius.circular(8),
                child: Padding(
                  padding: const EdgeInsets.all(12),
                  child: Text(
                    _errorMessage!,
                    style: TextStyle(color: Colors.red.shade800),
                  ),
                ),
              ),
            ),

          if (_deals.isEmpty)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 70),
              child: Column(
                children: [
                  const Icon(
                    Icons.handshake_outlined,
                    size: 58,
                    color: Colors.black26,
                  ),
                  const SizedBox(height: 14),
                  const Text(
                    'No deals match these filters.',
                    style: TextStyle(color: Colors.black54),
                  ),
                  if (_hasFilters) ...[
                    const SizedBox(height: 10),
                    TextButton(
                      onPressed: _clearFilters,
                      child: const Text('Clear filters'),
                    ),
                  ],
                ],
              ),
            )
          else
            ..._deals.map((deal) {
              return Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: _DealAdminCard(
                  dealNumber: _text(deal, 'deal_number'),
                  dealType: _dealTypeLabel(_text(deal, 'deal_type')),
                  propertyTitle: _text(deal, 'property_title'),
                  customerName: _text(deal, 'customer_name'),
                  partnerName: _text(deal, 'partner_name'),
                  transactionValue: _formatMoney(deal['transaction_value']),
                  commissionAmount: _formatMoney(deal['commission_amount']),
                  statusLabel: _statusLabel(_text(deal, 'status')),
                  statusColor: _statusColor(_text(deal, 'status')),
                  customerConfirmed: deal['customer_confirmed'] == true,
                  partnerConfirmed: deal['partner_confirmed'] == true,
                  ownerConfirmed: deal['owner_confirmed'] == true,
                  onTap: () {
                    final dealId = _parseInt(deal['id']);

                    if (dealId <= 0) {
                      return;
                    }

                    Navigator.of(context).push(
                      MaterialPageRoute<void>(
                        builder: (_) {
                          return StaffDealDetailScreen(dealId: dealId);
                        },
                      ),
                    );
                  },
                ),
              );
            }),

          if (_totalPages > 1) ...[
            const SizedBox(height: 8),
            _buildPagination(),
          ],

          const SizedBox(height: 20),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Deals'),
        actions: [
          IconButton(
            onPressed: _isLoading ? null : _loadDeals,
            tooltip: 'Refresh',
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      body: _buildBody(),
    );
  }
}

class _DealFilter {
  const _DealFilter({required this.label, required this.value});

  final String label;
  final String value;
}

class _DealAdminCard extends StatelessWidget {
  const _DealAdminCard({
    required this.dealNumber,
    required this.dealType,
    required this.propertyTitle,
    required this.customerName,
    required this.partnerName,
    required this.transactionValue,
    required this.commissionAmount,
    required this.statusLabel,
    required this.statusColor,
    required this.customerConfirmed,
    required this.partnerConfirmed,
    required this.ownerConfirmed,
    required this.onTap,
  });

  final String dealNumber;
  final String dealType;
  final String propertyTitle;
  final String customerName;
  final String partnerName;
  final String transactionValue;
  final String commissionAmount;

  final String statusLabel;
  final Color statusColor;

  final bool customerConfirmed;
  final bool partnerConfirmed;
  final bool ownerConfirmed;

  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(16),
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
                          propertyTitle.isEmpty ? 'Property' : propertyTitle,
                          style: const TextStyle(
                            fontSize: 17,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        const SizedBox(height: 3),
                        Text(
                          dealNumber.isEmpty ? 'Deal' : dealNumber,
                          style: const TextStyle(
                            fontSize: 12,
                            color: Colors.black54,
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: 8),
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 9,
                      vertical: 5,
                    ),
                    decoration: BoxDecoration(
                      color: statusColor.withValues(alpha: 0.12),
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: Text(
                      statusLabel,
                      style: TextStyle(
                        color: statusColor,
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  _SmallBadge(icon: Icons.home_work_outlined, label: dealType),
                  _SmallBadge(
                    icon: Icons.attach_money,
                    label: transactionValue,
                  ),
                ],
              ),
              const SizedBox(height: 12),
              _DealLine(
                icon: Icons.person_outline,
                text: customerName.isEmpty ? 'Customer' : customerName,
              ),
              const SizedBox(height: 6),
              _DealLine(
                icon: Icons.groups_outlined,
                text: partnerName.isEmpty ? 'Partner' : partnerName,
              ),
              const SizedBox(height: 10),
              Text(
                'Commission: $commissionAmount',
                style: const TextStyle(
                  fontWeight: FontWeight.w600,
                  color: Color(0xFF14532D),
                ),
              ),
              const SizedBox(height: 14),
              const Text(
                'Confirmations',
                style: TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                  color: Colors.black54,
                ),
              ),
              const SizedBox(height: 7),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  _ConfirmationBadge(
                    label: 'Customer',
                    confirmed: customerConfirmed,
                  ),
                  _ConfirmationBadge(
                    label: 'Partner',
                    confirmed: partnerConfirmed,
                  ),
                  _ConfirmationBadge(label: 'Owner', confirmed: ownerConfirmed),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _DealLine extends StatelessWidget {
  const _DealLine({required this.icon, required this.text});

  final IconData icon;
  final String text;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Icon(icon, size: 18, color: Colors.black54),
        const SizedBox(width: 8),
        Expanded(child: Text(text)),
      ],
    );
  }
}

class _SmallBadge extends StatelessWidget {
  const _SmallBadge({required this.icon, required this.label});

  final IconData icon;
  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 6),
      decoration: BoxDecoration(
        color: Colors.blueGrey.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 15, color: Colors.black54),
          const SizedBox(width: 5),
          Text(label, style: const TextStyle(fontSize: 12)),
        ],
      ),
    );
  }
}

class _ConfirmationBadge extends StatelessWidget {
  const _ConfirmationBadge({required this.label, required this.confirmed});

  final String label;
  final bool confirmed;

  @override
  Widget build(BuildContext context) {
    final color = confirmed ? const Color(0xFF15803D) : const Color(0xFFB45309);

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 6),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.10),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            confirmed ? Icons.check_circle_outline : Icons.schedule_outlined,
            size: 15,
            color: color,
          ),
          const SizedBox(width: 5),
          Text(
            confirmed ? '$label confirmed' : '$label waiting',
            style: TextStyle(
              color: color,
              fontSize: 11,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }
}
