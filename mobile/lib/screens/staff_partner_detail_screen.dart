import 'package:flutter/material.dart';

import 'package:mobile/services/staff_partner_admin_service.dart';

class StaffPartnerDetailScreen extends StatefulWidget {
  const StaffPartnerDetailScreen({super.key, required this.partnerId});

  final int partnerId;

  @override
  State<StaffPartnerDetailScreen> createState() {
    return _StaffPartnerDetailScreenState();
  }
}

class _StaffPartnerDetailScreenState extends State<StaffPartnerDetailScreen> {
  bool _isLoading = true;
  String? _errorMessage;
  Map<String, dynamic>? _partner;

  @override
  void initState() {
    super.initState();
    _loadPartner();
  }

  Future<void> _loadPartner() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final partner = await StaffPartnerAdminService.instance.fetchPartner(
        widget.partnerId,
      );

      if (!mounted) {
        return;
      }

      setState(() {
        _partner = partner;
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

  String _text(String key) {
    final value = _partner?[key];

    if (value == null) {
      return '';
    }

    return value.toString().trim();
  }

  int _integer(String key) {
    final value = _partner?[key];

    if (value is int) {
      return value;
    }

    return int.tryParse(value?.toString() ?? '') ?? 0;
  }

  bool _boolean(String key) {
    return _partner?[key] == true;
  }

  String _label(String value) {
    if (value.trim().isEmpty) {
      return 'Unknown';
    }

    return value
        .replaceAll('_', ' ')
        .split(' ')
        .where((part) => part.isNotEmpty)
        .map(
          (part) =>
              '${part[0].toUpperCase()}${part.substring(1).toLowerCase()}',
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

  String _location() {
    final town = _text('town');
    final county = _text('county');

    return [
      if (town.isNotEmpty) town,
      if (county.isNotEmpty) county,
    ].join(', ');
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF6F8F6),
      appBar: AppBar(
        title: const Text('Partner Details'),
        backgroundColor: const Color(0xFF14532D),
        foregroundColor: Colors.white,
        actions: [
          IconButton(
            tooltip: 'Refresh',
            onPressed: _isLoading ? null : _loadPartner,
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      body: _buildBody(),
    );
  }

  Widget _buildBody() {
    if (_isLoading && _partner == null) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_errorMessage != null && _partner == null) {
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
                onPressed: _loadPartner,
                icon: const Icon(Icons.refresh),
                label: const Text('Try Again'),
              ),
            ],
          ),
        ),
      );
    }

    if (_partner == null) {
      return const SizedBox.shrink();
    }

    final displayName = _text('display_name');
    final businessName = _text('business_name');
    final verificationStatus = _text('verification_status');

    final statusColor = _statusColor(verificationStatus);

    final commissionPlanId = _partner?['commission_plan_id'];

    final commissionRate = _partner?['commission_rate'];

    return RefreshIndicator(
      onRefresh: _loadPartner,
      child: ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(16),
        children: [
          Card(
            child: Padding(
              padding: const EdgeInsets.all(18),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const CircleAvatar(
                    radius: 28,
                    backgroundColor: Color(0xFFE7F5EC),
                    child: Icon(
                      Icons.person_outline,
                      size: 30,
                      color: Color(0xFF14532D),
                    ),
                  ),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          displayName.isEmpty ? 'Unnamed Partner' : displayName,
                          style: const TextStyle(
                            fontSize: 21,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        if (businessName.isNotEmpty &&
                            businessName != displayName) ...[
                          const SizedBox(height: 4),
                          Text(
                            businessName,
                            style: const TextStyle(color: Colors.black54),
                          ),
                        ],
                        const SizedBox(height: 8),
                        Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 10,
                            vertical: 5,
                          ),
                          decoration: BoxDecoration(
                            color: statusColor.withValues(alpha: 0.12),
                            borderRadius: BorderRadius.circular(20),
                          ),
                          child: Text(
                            _label(verificationStatus),
                            style: TextStyle(
                              color: statusColor,
                              fontSize: 12,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),

          const SizedBox(height: 14),

          _DetailCard(
            title: 'Partner',
            rows: [
              _DetailRow(label: 'Type', value: _label(_text('partner_type'))),
              _DetailRow(label: 'Code', value: _text('partner_code')),
              _DetailRow(label: 'Location', value: _location()),
              _DetailRow(label: 'Service area', value: _text('service_area')),
            ],
          ),

          const SizedBox(height: 14),

          _DetailCard(
            title: 'Operations',
            rows: [
              _DetailRow(
                label: 'Account',
                value: _boolean('is_active') ? 'Active' : 'Inactive',
              ),
              _DetailRow(
                label: 'Viewings',
                value: _boolean('accepts_viewing_requests')
                    ? 'Accepting requests'
                    : 'Not accepting requests',
              ),
              _DetailRow(
                label: 'Verification',
                value: _label(verificationStatus),
              ),
            ],
          ),

          const SizedBox(height: 14),

          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Row(
                children: [
                  Expanded(
                    child: _Metric(
                      value: _integer('property_count').toString(),
                      label: 'Properties',
                    ),
                  ),
                  Expanded(
                    child: _Metric(
                      value: _integer('published_property_count').toString(),
                      label: 'Published',
                    ),
                  ),
                ],
              ),
            ),
          ),

          const SizedBox(height: 14),

          _DetailCard(
            title: 'Commission',
            rows: [
              _DetailRow(
                label: 'Plan',
                value: commissionPlanId == null
                    ? 'Not assigned'
                    : 'Plan #$commissionPlanId',
              ),
              _DetailRow(
                label: 'Legacy rate',
                value: commissionRate == null ? '' : '$commissionRate%',
              ),
            ],
          ),

          if (_text('verification_notes').isNotEmpty) ...[
            const SizedBox(height: 14),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Verification Notes',
                      style: TextStyle(
                        fontSize: 17,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 10),
                    Text(_text('verification_notes')),
                  ],
                ),
              ),
            ),
          ],

          const SizedBox(height: 24),
        ],
      ),
    );
  }
}

class _DetailCard extends StatelessWidget {
  const _DetailCard({required this.title, required this.rows});

  final String title;
  final List<_DetailRow> rows;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              title,
              style: const TextStyle(fontSize: 17, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 12),
            ...rows,
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
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 105,
            child: Text(label, style: const TextStyle(color: Colors.black54)),
          ),
          Expanded(
            child: Text(
              value.trim().isEmpty ? '—' : value,
              style: const TextStyle(fontWeight: FontWeight.w500),
            ),
          ),
        ],
      ),
    );
  }
}

class _Metric extends StatelessWidget {
  const _Metric({required this.value, required this.label});

  final String value;
  final String label;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Text(
          value,
          style: const TextStyle(
            fontSize: 24,
            fontWeight: FontWeight.bold,
            color: Color(0xFF14532D),
          ),
        ),
        const SizedBox(height: 3),
        Text(label, style: const TextStyle(color: Colors.black54)),
      ],
    );
  }
}
