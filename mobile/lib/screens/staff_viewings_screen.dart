import 'dart:async';

import 'package:flutter/material.dart';

import 'package:mobile/services/staff_viewing_admin_service.dart';
import 'package:mobile/screens/staff_viewing_detail_screen.dart';

class StaffViewingsScreen extends StatefulWidget {
  const StaffViewingsScreen({super.key});

  @override
  State<StaffViewingsScreen> createState() {
    return _StaffViewingsScreenState();
  }
}

class _StaffViewingsScreenState extends State<StaffViewingsScreen> {
  final TextEditingController _searchController = TextEditingController();

  Timer? _searchDebounce;

  bool _isLoading = true;
  String? _errorMessage;

  List<Map<String, dynamic>> _viewings = [];

  String _selectedStatus = '';
  String _selectedDateScope = '';

  int _page = 1;
  final int _pageSize = 25;

  int _totalCount = 0;
  int _totalPages = 1;
  bool _hasNext = false;
  bool _hasPrevious = false;

  static const List<_ViewingFilter> _statusFilters = [
    _ViewingFilter(label: 'All', value: ''),
    _ViewingFilter(label: 'Pending Payment', value: 'pending_payment'),
    _ViewingFilter(label: 'Processing', value: 'payment_processing'),
    _ViewingFilter(label: 'Awaiting Partner', value: 'paid_pending_partner'),
    _ViewingFilter(label: 'Reschedule', value: 'reschedule_proposed'),
    _ViewingFilter(label: 'Confirmed', value: 'confirmed'),
    _ViewingFilter(label: 'Completed', value: 'completed'),
    _ViewingFilter(label: 'Cancelled', value: 'cancelled'),
    _ViewingFilter(label: 'Declined', value: 'declined'),
    _ViewingFilter(label: 'Payment Failed', value: 'payment_failed'),
    _ViewingFilter(label: 'Refunded', value: 'refunded'),
    _ViewingFilter(label: 'Disputed', value: 'disputed'),
  ];

  static const List<_ViewingFilter> _dateFilters = [
    _ViewingFilter(label: 'All dates', value: ''),
    _ViewingFilter(label: 'Today', value: 'today'),
    _ViewingFilter(label: 'Upcoming', value: 'upcoming'),
    _ViewingFilter(label: 'Past', value: 'past'),
  ];

  @override
  void initState() {
    super.initState();

    _searchController.addListener(_handleSearchChanged);

    _loadViewings();
  }

  @override
  void dispose() {
    _searchDebounce?.cancel();
    _searchController.dispose();
    super.dispose();
  }

  void _handleSearchChanged() {
    _searchDebounce?.cancel();

    _searchDebounce = Timer(const Duration(milliseconds: 450), () {
      if (!mounted) {
        return;
      }

      _page = 1;
      _loadViewings();
    });
  }

  Future<void> _loadViewings() async {
    if (!mounted) {
      return;
    }

    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final response = await StaffViewingAdminService.instance.fetchViewings(
        search: _searchController.text.trim().isEmpty
            ? null
            : _searchController.text.trim(),
        status: _selectedStatus.isEmpty ? null : _selectedStatus,
        dateScope: _selectedDateScope.isEmpty ? null : _selectedDateScope,
        page: _page,
        pageSize: _pageSize,
      );

      final rawResults = response['results'];

      if (rawResults is! List) {
        throw const FormatException(
          'The viewing directory returned invalid results.',
        );
      }

      final viewings = rawResults
          .whereType<Map>()
          .map((item) => Map<String, dynamic>.from(item))
          .toList();

      if (!mounted) {
        return;
      }

      setState(() {
        _viewings = viewings;

        _totalCount = _parseInt(response['count']);

        _page = _parseInt(response['page'], fallback: 1);

        _totalPages = _parseInt(response['total_pages'], fallback: 1);

        if (_totalPages < 1) {
          _totalPages = 1;
        }

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

  Future<void> _selectStatus(String status) async {
    if (_selectedStatus == status) {
      return;
    }

    setState(() {
      _selectedStatus = status;
      _page = 1;
    });

    await _loadViewings();
  }

  Future<void> _selectDateScope(String? value) async {
    final selected = value ?? '';

    if (_selectedDateScope == selected) {
      return;
    }

    setState(() {
      _selectedDateScope = selected;
      _page = 1;
    });

    await _loadViewings();
  }

  Future<void> _clearFilters() async {
    _searchDebounce?.cancel();

    _searchController.clear();

    setState(() {
      _selectedStatus = '';
      _selectedDateScope = '';
      _page = 1;
    });

    await _loadViewings();
  }

  Future<void> _previousPage() async {
    if (!_hasPrevious || _page <= 1) {
      return;
    }

    setState(() {
      _page -= 1;
    });

    await _loadViewings();
  }

  Future<void> _nextPage() async {
    if (!_hasNext) {
      return;
    }

    setState(() {
      _page += 1;
    });

    await _loadViewings();
  }

  String _cleanError(Object error) {
    return error.toString().replaceFirst(RegExp(r'^Exception:\s*'), '').trim();
  }

  int _parseInt(dynamic value, {int fallback = 0}) {
    if (value is int) {
      return value;
    }

    if (value is num) {
      return value.toInt();
    }

    return int.tryParse(value?.toString() ?? '') ?? fallback;
  }

  String _text(Map<String, dynamic> viewing, String key) {
    final value = viewing[key];

    if (value == null) {
      return '';
    }

    return value.toString().trim();
  }

  String _statusLabel(String status) {
    if (status.isEmpty) {
      return 'Unknown';
    }

    return status
        .replaceAll('_', ' ')
        .split(' ')
        .where((part) => part.isNotEmpty)
        .map(
          (part) =>
              '${part[0].toUpperCase()}'
              '${part.substring(1).toLowerCase()}',
        )
        .join(' ');
  }

  Color _statusColor(String status) {
    switch (status) {
      case 'confirmed':
        return const Color(0xFF15803D);

      case 'completed':
        return const Color(0xFF0F766E);

      case 'pending_payment':
      case 'payment_processing':
      case 'paid_pending_partner':
      case 'reschedule_proposed':
        return const Color(0xFFB45309);

      case 'cancelled':
      case 'declined':
      case 'payment_failed':
        return const Color(0xFFB91C1C);

      case 'refunded':
        return const Color(0xFF0369A1);

      case 'disputed':
        return const Color(0xFF7C3AED);

      default:
        return Colors.black54;
    }
  }

  String _formatFee(Map<String, dynamic> viewing) {
    final raw = _text(viewing, 'fee_amount');

    if (raw.isEmpty) {
      return 'KES 0';
    }

    final amount = double.tryParse(raw);

    if (amount == null) {
      return 'KES $raw';
    }

    return 'KES ${amount.toStringAsFixed(0)}';
  }

  String _formatSchedule(Map<String, dynamic> viewing) {
    final date = _text(viewing, 'requested_date');

    final time = _text(viewing, 'requested_time');

    if (date.isEmpty && time.isEmpty) {
      return 'Schedule not provided';
    }

    if (time.isEmpty) {
      return date;
    }

    final cleanTime = time.length >= 5 ? time.substring(0, 5) : time;

    return '$date  $cleanTime';
  }

  bool get _hasFilters {
    return _searchController.text.trim().isNotEmpty ||
        _selectedStatus.isNotEmpty ||
        _selectedDateScope.isNotEmpty;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF6F8F6),
      appBar: AppBar(
        title: const Text('Viewings'),
        backgroundColor: const Color(0xFF14532D),
        foregroundColor: Colors.white,
        actions: [
          IconButton(
            tooltip: 'Refresh',
            onPressed: _isLoading ? null : _loadViewings,
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      body: Column(
        children: [
          _buildSearchAndFilters(),
          Expanded(child: _buildBody()),
        ],
      ),
    );
  }

  Widget _buildSearchAndFilters() {
    return Container(
      width: double.infinity,
      color: Colors.white,
      padding: const EdgeInsets.fromLTRB(12, 12, 12, 10),
      child: Column(
        children: [
          TextField(
            controller: _searchController,
            textInputAction: TextInputAction.search,
            decoration: InputDecoration(
              hintText: 'Search customer, property, partner, payment...',
              prefixIcon: const Icon(Icons.search),
              suffixIcon: _searchController.text.isEmpty
                  ? null
                  : IconButton(
                      tooltip: 'Clear search',
                      onPressed: () {
                        _searchDebounce?.cancel();

                        _searchController.clear();

                        setState(() {
                          _page = 1;
                        });

                        _loadViewings();
                      },
                      icon: const Icon(Icons.close),
                    ),
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(12),
              ),
              isDense: true,
            ),
          ),

          const SizedBox(height: 10),

          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: _statusFilters.map((filter) {
                final selected = filter.value == _selectedStatus;

                return Padding(
                  padding: const EdgeInsets.only(right: 8),
                  child: ChoiceChip(
                    label: Text(filter.label),
                    selected: selected,
                    onSelected: (_) {
                      _selectStatus(filter.value);
                    },
                  ),
                );
              }).toList(),
            ),
          ),

          const SizedBox(height: 10),

          DropdownButtonFormField<String>(
            initialValue: _selectedDateScope,
            isExpanded: true,
            decoration: const InputDecoration(
              labelText: 'Requested date',
              border: OutlineInputBorder(),
              isDense: true,
            ),
            items: _dateFilters
                .map(
                  (option) => DropdownMenuItem<String>(
                    value: option.value,
                    child: Text(option.label),
                  ),
                )
                .toList(),
            onChanged: _selectDateScope,
          ),

          const SizedBox(height: 8),

          Row(
            children: [
              Expanded(
                child: Text(
                  _totalCount == 1
                      ? '1 viewing found'
                      : '$_totalCount viewings found',
                  style: const TextStyle(
                    color: Colors.black54,
                    fontSize: 13,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ),
              if (_hasFilters)
                TextButton.icon(
                  onPressed: _clearFilters,
                  icon: const Icon(Icons.filter_alt_off_outlined, size: 18),
                  label: const Text('Clear'),
                ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildBody() {
    if (_isLoading && _viewings.isEmpty) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_errorMessage != null && _viewings.isEmpty) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(
                Icons.error_outline,
                size: 52,
                color: Color(0xFFB45309),
              ),
              const SizedBox(height: 14),
              Text(_errorMessage!, textAlign: TextAlign.center),
              const SizedBox(height: 16),
              ElevatedButton.icon(
                onPressed: _loadViewings,
                icon: const Icon(Icons.refresh),
                label: const Text('Try Again'),
              ),
            ],
          ),
        ),
      );
    }

    if (_viewings.isEmpty) {
      return RefreshIndicator(
        onRefresh: _loadViewings,
        child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          children: [
            const SizedBox(height: 100),
            const Icon(
              Icons.calendar_month_outlined,
              size: 58,
              color: Colors.black26,
            ),
            const SizedBox(height: 16),
            const Center(
              child: Text(
                'No viewings match these filters.',
                style: TextStyle(color: Colors.black54),
              ),
            ),
            if (_hasFilters) ...[
              const SizedBox(height: 12),
              Center(
                child: TextButton(
                  onPressed: _clearFilters,
                  child: const Text('Clear filters'),
                ),
              ),
            ],
          ],
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: _loadViewings,
      child: ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(16),
        children: [
          if (_isLoading)
            const Padding(
              padding: EdgeInsets.only(bottom: 10),
              child: LinearProgressIndicator(),
            ),

          ..._viewings.map(
            (viewing) => Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: _ViewingAdminCard(
                viewingId: _parseInt(viewing['id']),
                customerName: _text(viewing, 'customer_name'),
                customerId: _parseInt(viewing['customer']),
                propertyTitle: _text(viewing, 'property_title'),
                partnerName: _text(viewing, 'assigned_partner_name'),
                fee: _formatFee(viewing),
                schedule: _formatSchedule(viewing),
                status: _text(viewing, 'status'),
                statusLabel: _statusLabel(_text(viewing, 'status')),
                statusColor: _statusColor(_text(viewing, 'status')),
                paymentReference: _text(viewing, 'payment_reference'),
                onTap: () async {
                  final viewingId = _parseInt(viewing['id']);

                  if (viewingId <= 0) {
                    return;
                  }

                  await Navigator.of(context).push(
                    MaterialPageRoute<void>(
                      builder: (_) {
                        return StaffViewingDetailScreen(viewingId: viewingId);
                      },
                    ),
                  );

                  if (!mounted) {
                    return;
                  }

                  await _loadViewings();
                },
              ),
            ),
          ),

          if (_totalPages > 1) ...[
            const SizedBox(height: 8),
            Card(
              child: Padding(
                padding: const EdgeInsets.symmetric(
                  horizontal: 10,
                  vertical: 8,
                ),
                child: Row(
                  children: [
                    IconButton(
                      tooltip: 'Previous page',
                      onPressed: _hasPrevious && !_isLoading
                          ? _previousPage
                          : null,
                      icon: const Icon(Icons.chevron_left),
                    ),
                    Expanded(
                      child: Text(
                        'Page $_page of $_totalPages',
                        textAlign: TextAlign.center,
                        style: const TextStyle(fontWeight: FontWeight.w600),
                      ),
                    ),
                    IconButton(
                      tooltip: 'Next page',
                      onPressed: _hasNext && !_isLoading ? _nextPage : null,
                      icon: const Icon(Icons.chevron_right),
                    ),
                  ],
                ),
              ),
            ),
          ],

          const SizedBox(height: 16),
        ],
      ),
    );
  }
}

class _ViewingFilter {
  const _ViewingFilter({required this.label, required this.value});

  final String label;
  final String value;
}

class _ViewingAdminCard extends StatelessWidget {
  const _ViewingAdminCard({
    required this.customerName,
    required this.customerId,
    required this.propertyTitle,
    required this.partnerName,
    required this.fee,
    required this.schedule,
    required this.status,
    required this.statusLabel,
    required this.statusColor,
    required this.paymentReference,
    required this.viewingId,
    required this.onTap,
  });

  final String customerName;
  final int customerId;
  final String propertyTitle;
  final String partnerName;
  final String fee;
  final String schedule;
  final String status;
  final String statusLabel;
  final Color statusColor;
  final String paymentReference;
  final int viewingId;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final displayCustomer = customerName.isNotEmpty
        ? customerName
        : 'Customer #$customerId';

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
                    child: Text(
                      propertyTitle.isEmpty ? 'Property' : propertyTitle,
                      style: const TextStyle(
                        fontSize: 17,
                        fontWeight: FontWeight.bold,
                      ),
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

              const SizedBox(height: 10),

              Text(
                fee,
                style: const TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.w600,
                  color: Color(0xFF14532D),
                ),
              ),

              const SizedBox(height: 8),

              _ViewingLine(icon: Icons.person_outline, text: displayCustomer),

              if (partnerName.isNotEmpty) ...[
                const SizedBox(height: 6),
                _ViewingLine(icon: Icons.groups_outlined, text: partnerName),
              ],

              const SizedBox(height: 6),

              _ViewingLine(icon: Icons.calendar_today_outlined, text: schedule),

              if (paymentReference.isNotEmpty) ...[
                const SizedBox(height: 6),
                _ViewingLine(
                  icon: Icons.receipt_long_outlined,
                  text: paymentReference,
                ),
              ],

              const SizedBox(height: 8),

              const Align(
                alignment: Alignment.centerRight,
                child: Icon(Icons.chevron_right, color: Colors.black38),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _ViewingLine extends StatelessWidget {
  const _ViewingLine({required this.icon, required this.text});

  final IconData icon;
  final String text;

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(icon, size: 17, color: Colors.black45),
        const SizedBox(width: 6),
        Expanded(
          child: Text(text, style: const TextStyle(color: Colors.black54)),
        ),
      ],
    );
  }
}
