import 'dart:async';

import 'package:flutter/material.dart';

import 'package:mobile/screens/staff_partner_detail_screen.dart';
import 'package:mobile/services/staff_partner_admin_service.dart';

class StaffPartnersScreen extends StatefulWidget {
  const StaffPartnersScreen({super.key});

  @override
  State<StaffPartnersScreen> createState() {
    return _StaffPartnersScreenState();
  }
}

class _StaffPartnersScreenState extends State<StaffPartnersScreen> {
  final TextEditingController _searchController = TextEditingController();

  Timer? _searchDebounce;

  bool _isLoading = true;
  String? _errorMessage;

  List<Map<String, dynamic>> _partners = [];

  String _selectedStatus = '';
  String _selectedPartnerType = '';
  String _selectedActivity = '';

  int _page = 1;
  final int _pageSize = 25;

  int _totalCount = 0;
  int _totalPages = 1;
  bool _hasNext = false;
  bool _hasPrevious = false;

  static const List<_PartnerStatusFilter> _statusFilters = [
    _PartnerStatusFilter(label: 'All', value: ''),
    _PartnerStatusFilter(label: 'Pending', value: 'pending'),
    _PartnerStatusFilter(label: 'Under Review', value: 'under_review'),
    _PartnerStatusFilter(label: 'Approved', value: 'approved'),
    _PartnerStatusFilter(label: 'Rejected', value: 'rejected'),
    _PartnerStatusFilter(label: 'Suspended', value: 'suspended'),
  ];

  static const List<_PartnerOption> _partnerTypes = [
    _PartnerOption(label: 'All types', value: ''),
    _PartnerOption(label: 'Agent', value: 'agent'),
    _PartnerOption(label: 'Agency', value: 'agency'),
    _PartnerOption(label: 'Developer', value: 'developer'),
    _PartnerOption(label: 'Owner', value: 'owner'),
  ];

  static const List<_PartnerOption> _activityOptions = [
    _PartnerOption(label: 'All accounts', value: ''),
    _PartnerOption(label: 'Active', value: 'active'),
    _PartnerOption(label: 'Inactive', value: 'inactive'),
  ];

  @override
  void initState() {
    super.initState();

    _searchController.addListener(_handleSearchChanged);

    _loadPartners();
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
      _loadPartners();
    });
  }

  Future<void> _loadPartners() async {
    if (!mounted) {
      return;
    }

    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final response = await StaffPartnerAdminService.instance.fetchPartners(
        search: _searchController.text.trim().isEmpty
            ? null
            : _searchController.text.trim(),
        status: _selectedStatus.isEmpty ? null : _selectedStatus,
        partnerType: _selectedPartnerType.isEmpty ? null : _selectedPartnerType,
        isActive: _selectedActivity == 'active'
            ? true
            : _selectedActivity == 'inactive'
            ? false
            : null,
        page: _page,
        pageSize: _pageSize,
      );

      final rawResults = response['results'];

      if (rawResults is! List) {
        throw const FormatException(
          'The partner directory returned invalid results.',
        );
      }

      final partners = rawResults
          .whereType<Map>()
          .map((item) => Map<String, dynamic>.from(item))
          .toList();

      if (!mounted) {
        return;
      }

      setState(() {
        _partners = partners;

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

    await _loadPartners();
  }

  Future<void> _selectPartnerType(String? value) async {
    final selected = value ?? '';

    if (_selectedPartnerType == selected) {
      return;
    }

    setState(() {
      _selectedPartnerType = selected;
      _page = 1;
    });

    await _loadPartners();
  }

  Future<void> _selectActivity(String? value) async {
    final selected = value ?? '';

    if (_selectedActivity == selected) {
      return;
    }

    setState(() {
      _selectedActivity = selected;
      _page = 1;
    });

    await _loadPartners();
  }

  Future<void> _clearFilters() async {
    _searchDebounce?.cancel();

    _searchController.clear();

    setState(() {
      _selectedStatus = '';
      _selectedPartnerType = '';
      _selectedActivity = '';
      _page = 1;
    });

    await _loadPartners();
  }

  Future<void> _previousPage() async {
    if (!_hasPrevious || _page <= 1) {
      return;
    }

    setState(() {
      _page -= 1;
    });

    await _loadPartners();
  }

  Future<void> _nextPage() async {
    if (!_hasNext) {
      return;
    }

    setState(() {
      _page += 1;
    });

    await _loadPartners();
  }

  Future<void> _openPartner(Map<String, dynamic> partner) async {
    final partnerId = _integer(partner, 'id');

    if (partnerId <= 0) {
      return;
    }

    await Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) {
          return StaffPartnerDetailScreen(partnerId: partnerId);
        },
      ),
    );

    if (!mounted) {
      return;
    }

    await _loadPartners();
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

  String _text(Map<String, dynamic> partner, String key) {
    final value = partner[key];

    if (value == null) {
      return '';
    }

    return value.toString().trim();
  }

  int _integer(Map<String, dynamic> partner, String key) {
    return _parseInt(partner[key]);
  }

  bool _boolean(Map<String, dynamic> partner, String key) {
    return partner[key] == true;
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
      case 'approved':
        return const Color(0xFF15803D);

      case 'pending':
        return const Color(0xFFB45309);

      case 'under_review':
        return const Color(0xFF1D4ED8);

      case 'rejected':
        return const Color(0xFFB91C1C);

      case 'suspended':
        return const Color(0xFF7C3AED);

      default:
        return Colors.black54;
    }
  }

  String _partnerTypeLabel(String value) {
    switch (value) {
      case 'agent':
        return 'Agent';

      case 'agency':
        return 'Agency';

      case 'developer':
        return 'Developer';

      case 'owner':
        return 'Owner';

      default:
        return _statusLabel(value);
    }
  }

  String _location(Map<String, dynamic> partner) {
    final town = _text(partner, 'town');

    final county = _text(partner, 'county');

    final values = <String>[
      if (town.isNotEmpty) town,
      if (county.isNotEmpty) county,
    ];

    return values.join(', ');
  }

  bool get _hasFilters {
    return _searchController.text.trim().isNotEmpty ||
        _selectedStatus.isNotEmpty ||
        _selectedPartnerType.isNotEmpty ||
        _selectedActivity.isNotEmpty;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF6F8F6),
      appBar: AppBar(
        title: const Text('Partners'),
        backgroundColor: const Color(0xFF14532D),
        foregroundColor: Colors.white,
        actions: [
          IconButton(
            tooltip: 'Refresh',
            onPressed: _isLoading ? null : _loadPartners,
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
              hintText: 'Search name, business, town, county...',
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

                        _loadPartners();
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

          Row(
            children: [
              Expanded(
                child: DropdownButtonFormField<String>(
                  initialValue: _selectedPartnerType,
                  isExpanded: true,
                  decoration: const InputDecoration(
                    labelText: 'Partner type',
                    border: OutlineInputBorder(),
                    isDense: true,
                  ),
                  items: _partnerTypes
                      .map(
                        (option) => DropdownMenuItem<String>(
                          value: option.value,
                          child: Text(option.label),
                        ),
                      )
                      .toList(),
                  onChanged: _selectPartnerType,
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: DropdownButtonFormField<String>(
                  initialValue: _selectedActivity,
                  isExpanded: true,
                  decoration: const InputDecoration(
                    labelText: 'Account',
                    border: OutlineInputBorder(),
                    isDense: true,
                  ),
                  items: _activityOptions
                      .map(
                        (option) => DropdownMenuItem<String>(
                          value: option.value,
                          child: Text(option.label),
                        ),
                      )
                      .toList(),
                  onChanged: _selectActivity,
                ),
              ),
            ],
          ),

          const SizedBox(height: 8),

          Row(
            children: [
              Expanded(
                child: Text(
                  _totalCount == 1
                      ? '1 partner found'
                      : '$_totalCount partners found',
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
    if (_isLoading && _partners.isEmpty) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_errorMessage != null && _partners.isEmpty) {
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
                onPressed: _loadPartners,
                icon: const Icon(Icons.refresh),
                label: const Text('Try Again'),
              ),
            ],
          ),
        ),
      );
    }

    if (_partners.isEmpty) {
      return RefreshIndicator(
        onRefresh: _loadPartners,
        child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          children: [
            const SizedBox(height: 100),
            const Icon(Icons.groups_outlined, size: 58, color: Colors.black26),
            const SizedBox(height: 16),
            const Center(
              child: Text(
                'No partners match these filters.',
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
      onRefresh: _loadPartners,
      child: ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(16),
        children: [
          if (_isLoading)
            const Padding(
              padding: EdgeInsets.only(bottom: 10),
              child: LinearProgressIndicator(),
            ),

          ..._partners.map(
            (partner) => Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: _PartnerAdminCard(
                displayName: _text(partner, 'display_name'),
                businessName: _text(partner, 'business_name'),
                partnerType: _partnerTypeLabel(_text(partner, 'partner_type')),
                statusLabel: _statusLabel(
                  _text(partner, 'verification_status'),
                ),
                statusColor: _statusColor(
                  _text(partner, 'verification_status'),
                ),
                location: _location(partner),
                isActive: _boolean(partner, 'is_active'),
                acceptsViewings: _boolean(partner, 'accepts_viewing_requests'),
                propertyCount: _integer(partner, 'property_count'),
                publishedPropertyCount: _integer(
                  partner,
                  'published_property_count',
                ),
                onTap: () {
                  _openPartner(partner);
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

class _PartnerStatusFilter {
  const _PartnerStatusFilter({required this.label, required this.value});

  final String label;
  final String value;
}

class _PartnerOption {
  const _PartnerOption({required this.label, required this.value});

  final String label;
  final String value;
}

class _PartnerAdminCard extends StatelessWidget {
  const _PartnerAdminCard({
    required this.displayName,
    required this.businessName,
    required this.partnerType,
    required this.statusLabel,
    required this.statusColor,
    required this.location,
    required this.isActive,
    required this.acceptsViewings,
    required this.propertyCount,
    required this.publishedPropertyCount,
    required this.onTap,
  });

  final String displayName;
  final String businessName;
  final String partnerType;
  final String statusLabel;
  final Color statusColor;
  final String location;
  final bool isActive;
  final bool acceptsViewings;
  final int propertyCount;
  final int publishedPropertyCount;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final secondaryName = businessName.isNotEmpty && businessName != displayName
        ? businessName
        : '';

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
                  const CircleAvatar(
                    backgroundColor: Color(0xFFE7F5EC),
                    child: Icon(Icons.person_outline, color: Color(0xFF14532D)),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          displayName.isEmpty ? 'Unnamed Partner' : displayName,
                          style: const TextStyle(
                            fontSize: 17,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        if (secondaryName.isNotEmpty)
                          Padding(
                            padding: const EdgeInsets.only(top: 3),
                            child: Text(
                              secondaryName,
                              style: const TextStyle(color: Colors.black54),
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
              const SizedBox(height: 14),
              Text(
                partnerType,
                style: const TextStyle(fontWeight: FontWeight.w600),
              ),
              if (location.isNotEmpty) ...[
                const SizedBox(height: 6),
                Row(
                  children: [
                    const Icon(
                      Icons.location_on_outlined,
                      size: 17,
                      color: Colors.black45,
                    ),
                    const SizedBox(width: 5),
                    Expanded(
                      child: Text(
                        location,
                        style: const TextStyle(color: Colors.black54),
                      ),
                    ),
                  ],
                ),
              ],
              const SizedBox(height: 14),
              Row(
                children: [
                  Expanded(
                    child: _PartnerMetric(
                      label: 'Properties',
                      value: propertyCount.toString(),
                    ),
                  ),
                  Expanded(
                    child: _PartnerMetric(
                      label: 'Published',
                      value: publishedPropertyCount.toString(),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              Row(
                children: [
                  Expanded(
                    child: Wrap(
                      spacing: 8,
                      runSpacing: 6,
                      children: [
                        _SmallStatus(
                          icon: isActive
                              ? Icons.check_circle_outline
                              : Icons.block_outlined,
                          label: isActive ? 'Active' : 'Inactive',
                        ),
                        _SmallStatus(
                          icon: acceptsViewings
                              ? Icons.event_available_outlined
                              : Icons.event_busy_outlined,
                          label: acceptsViewings
                              ? 'Accepts viewings'
                              : 'Viewings off',
                        ),
                      ],
                    ),
                  ),
                  const Icon(Icons.chevron_right, color: Colors.black38),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _PartnerMetric extends StatelessWidget {
  const _PartnerMetric({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          value,
          style: const TextStyle(fontSize: 19, fontWeight: FontWeight.bold),
        ),
        Text(
          label,
          style: const TextStyle(color: Colors.black54, fontSize: 12),
        ),
      ],
    );
  }
}

class _SmallStatus extends StatelessWidget {
  const _SmallStatus({required this.icon, required this.label});

  final IconData icon;
  final String label;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: 16, color: Colors.black45),
        const SizedBox(width: 4),
        Text(
          label,
          style: const TextStyle(color: Colors.black54, fontSize: 12),
        ),
      ],
    );
  }
}
