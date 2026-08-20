import 'package:flutter/material.dart';

import 'package:mobile/services/staff_viewing_admin_service.dart';

class StaffViewingDetailScreen extends StatefulWidget {
  const StaffViewingDetailScreen({
    super.key,
    required this.viewingId,
  });

  final int viewingId;

  @override
  State<StaffViewingDetailScreen> createState() {
    return _StaffViewingDetailScreenState();
  }
}

class _StaffViewingDetailScreenState
    extends State<StaffViewingDetailScreen> {
  bool _isLoading = true;
  String? _errorMessage;

  Map<String, dynamic>? _viewing;
  List<Map<String, dynamic>> _events = [];

  @override
  void initState() {
    super.initState();
    _loadViewing();
  }

  Future<void> _loadViewing() async {
    if (!mounted) {
      return;
    }

    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final response =
          await StaffViewingAdminService.instance.fetchViewing(
        widget.viewingId,
      );

      final rawViewing = response['viewing'];
      final rawEvents = response['events'];

      if (rawViewing is! Map) {
        throw const FormatException(
          'The viewing detail response is invalid.',
        );
      }

      final viewing = Map<String, dynamic>.from(
        rawViewing,
      );

      final events = <Map<String, dynamic>>[];

      if (rawEvents is List) {
        for (final item in rawEvents) {
          if (item is Map) {
            events.add(
              Map<String, dynamic>.from(item),
            );
          }
        }
      }

      if (!mounted) {
        return;
      }

      setState(() {
        _viewing = viewing;
        _events = events;
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
    return error
        .toString()
        .replaceFirst(
          RegExp(r'^Exception:\s*'),
          '',
        )
        .trim();
  }

  String _text(
    Map<String, dynamic> data,
    String key,
  ) {
    final value = data[key];

    if (value == null) {
      return '';
    }

    return value.toString().trim();
  }

  String _displayText(
    String value, {
    String fallback = 'Not recorded',
  }) {
    if (value.trim().isEmpty) {
      return fallback;
    }

    return value.trim();
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

  String _formatFee(
    Map<String, dynamic> viewing,
  ) {
    final raw = _text(
      viewing,
      'fee_amount',
    );

    if (raw.isEmpty) {
      return 'KES 0';
    }

    final amount = double.tryParse(raw);

    if (amount == null) {
      return 'KES $raw';
    }

    return 'KES ${amount.toStringAsFixed(0)}';
  }

  String _formatDateTime(String value) {
    if (value.trim().isEmpty) {
      return 'Not recorded';
    }

    final parsed = DateTime.tryParse(value);

    if (parsed == null) {
      return value;
    }

    final local = parsed.toLocal();

    final year = local.year.toString().padLeft(4, '0');
    final month = local.month.toString().padLeft(2, '0');
    final day = local.day.toString().padLeft(2, '0');

    final hour = local.hour.toString().padLeft(2, '0');
    final minute =
        local.minute.toString().padLeft(2, '0');

    return '$year-$month-$day  $hour:$minute';
  }

  String _formatSchedule(
    String date,
    String time,
  ) {
    if (date.isEmpty && time.isEmpty) {
      return 'Not recorded';
    }

    if (time.isEmpty) {
      return date;
    }

    final cleanTime =
        time.length >= 5 ? time.substring(0, 5) : time;

    if (date.isEmpty) {
      return cleanTime;
    }

    return '$date  $cleanTime';
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF6F8F6),
      appBar: AppBar(
        title: Text(
          'Viewing #${widget.viewingId}',
        ),
        backgroundColor: const Color(0xFF14532D),
        foregroundColor: Colors.white,
        actions: [
          IconButton(
            tooltip: 'Refresh',
            onPressed:
                _isLoading ? null : _loadViewing,
            icon: const Icon(
              Icons.refresh,
            ),
          ),
        ],
      ),
      body: _buildBody(),
    );
  }

  Widget _buildBody() {
    if (_isLoading && _viewing == null) {
      return const Center(
        child: CircularProgressIndicator(),
      );
    }

    if (_errorMessage != null &&
        _viewing == null) {
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
              Text(
                _errorMessage!,
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 16),
              ElevatedButton.icon(
                onPressed: _loadViewing,
                icon: const Icon(
                  Icons.refresh,
                ),
                label: const Text(
                  'Try Again',
                ),
              ),
            ],
          ),
        ),
      );
    }

    final viewing = _viewing;

    if (viewing == null) {
      return const Center(
        child: Text(
          'Viewing information is unavailable.',
        ),
      );
    }

    final status = _text(
      viewing,
      'status',
    );

    final customerName = _text(
      viewing,
      'customer_name',
    );

    final customerId = _text(
      viewing,
      'customer',
    );

    final propertyTitle = _text(
      viewing,
      'property_title',
    );

    final propertyId = _text(
      viewing,
      'property',
    );

    final partnerName = _text(
      viewing,
      'assigned_partner_name',
    );

    final partnerId = _text(
      viewing,
      'assigned_partner',
    );

    final dealId = _text(
      viewing,
      'deal_id',
    );

    final partnerOutcomeSubmitted =
        viewing['partner_outcome_submitted'] == true;

    return RefreshIndicator(
      onRefresh: _loadViewing,
      child: ListView(
        physics:
            const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(16),
        children: [
          if (_isLoading)
            const Padding(
              padding: EdgeInsets.only(
                bottom: 12,
              ),
              child: LinearProgressIndicator(),
            ),

          Card(
            child: Padding(
              padding: const EdgeInsets.all(18),
              child: Column(
                crossAxisAlignment:
                    CrossAxisAlignment.start,
                children: [
                  Row(
                    crossAxisAlignment:
                        CrossAxisAlignment.start,
                    children: [
                      Expanded(
                        child: Text(
                          propertyTitle.isEmpty
                              ? 'Viewing #${widget.viewingId}'
                              : propertyTitle,
                          style: const TextStyle(
                            fontSize: 22,
                            fontWeight:
                                FontWeight.bold,
                          ),
                        ),
                      ),
                      const SizedBox(width: 10),
                      Container(
                        padding:
                            const EdgeInsets.symmetric(
                          horizontal: 10,
                          vertical: 6,
                        ),
                        decoration: BoxDecoration(
                          color: _statusColor(status)
                              .withValues(
                            alpha: 0.12,
                          ),
                          borderRadius:
                              BorderRadius.circular(
                            20,
                          ),
                        ),
                        child: Text(
                          _statusLabel(status),
                          style: TextStyle(
                            color:
                                _statusColor(status),
                            fontWeight:
                                FontWeight.w600,
                            fontSize: 12,
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  Text(
                    _formatFee(viewing),
                    style: const TextStyle(
                      color: Color(0xFF14532D),
                      fontSize: 18,
                      fontWeight:
                          FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    _displayText(
                      _text(
                        viewing,
                        'listing_type',
                      ),
                    ),
                    style: const TextStyle(
                      color: Colors.black54,
                    ),
                  ),
                ],
              ),
            ),
          ),

          const SizedBox(height: 12),

          _DetailSection(
            title: 'Participants',
            icon: Icons.people_outline,
            children: [
              _DetailRow(
                label: 'Customer',
                value: customerName.isNotEmpty
                    ? customerName
                    : customerId.isNotEmpty
                        ? 'Customer #$customerId'
                        : 'Not recorded',
              ),
              _DetailRow(
                label: 'Property',
                value: propertyTitle.isNotEmpty
                    ? '$propertyTitle'
                        '${propertyId.isNotEmpty ? '  (#$propertyId)' : ''}'
                    : propertyId.isNotEmpty
                        ? 'Property #$propertyId'
                        : 'Not recorded',
              ),
              _DetailRow(
                label: 'Partner',
                value: partnerName.isNotEmpty
                    ? '$partnerName'
                        '${partnerId.isNotEmpty ? '  (#$partnerId)' : ''}'
                    : partnerId.isNotEmpty
                        ? 'Partner #$partnerId'
                        : 'Not assigned',
              ),
            ],
          ),

          const SizedBox(height: 12),

          _DetailSection(
            title: 'Payment',
            icon: Icons.payments_outlined,
            children: [
              _DetailRow(
                label: 'Viewing fee',
                value: _formatFee(viewing),
              ),
              _DetailRow(
                label: 'Payment reference',
                value: _displayText(
                  _text(
                    viewing,
                    'payment_reference',
                  ),
                ),
              ),
              _DetailRow(
                label: 'Booking status',
                value: _statusLabel(
                  _text(
                    viewing,
                    'booking_status',
                  ),
                ),
              ),
              _DetailRow(
                label: 'Operational status',
                value: _statusLabel(
                  _text(
                    viewing,
                    'operational_status',
                  ),
                ),
              ),
            ],
          ),

          const SizedBox(height: 12),

          _DetailSection(
            title: 'Schedule',
            icon: Icons.calendar_month_outlined,
            children: [
              _DetailRow(
                label: 'Requested',
                value: _formatSchedule(
                  _text(
                    viewing,
                    'requested_date',
                  ),
                  _text(
                    viewing,
                    'requested_time',
                  ),
                ),
              ),
              _DetailRow(
                label: 'Proposed',
                value: _formatSchedule(
                  _text(
                    viewing,
                    'proposed_date',
                  ),
                  _text(
                    viewing,
                    'proposed_time',
                  ),
                ),
              ),
              _DetailRow(
                label: 'Confirmed',
                value: _formatSchedule(
                  _text(
                    viewing,
                    'confirmed_date',
                  ),
                  _text(
                    viewing,
                    'confirmed_time',
                  ),
                ),
              ),
              _DetailRow(
                label: 'Partner responded',
                value: _formatDateTime(
                  _text(
                    viewing,
                    'partner_responded_at',
                  ),
                ),
              ),
            ],
          ),

          const SizedBox(height: 12),

          _DetailSection(
            title: 'Live Operations',
            icon: Icons.route_outlined,
            children: [
              _DetailRow(
                label: 'Partner departed',
                value: _formatDateTime(
                  _text(
                    viewing,
                    'partner_departed_at',
                  ),
                ),
              ),
              _DetailRow(
                label: 'Partner arrived',
                value: _formatDateTime(
                  _text(
                    viewing,
                    'partner_arrived_at',
                  ),
                ),
              ),
              _DetailRow(
                label: 'Viewing started',
                value: _formatDateTime(
                  _text(
                    viewing,
                    'viewing_started_at',
                  ),
                ),
              ),
              _DetailRow(
                label: 'Completed',
                value: _formatDateTime(
                  _text(
                    viewing,
                    'completed_at',
                  ),
                ),
              ),
            ],
          ),

          if (_text(
                viewing,
                'customer_message',
              ).isNotEmpty ||
              _text(
                viewing,
                'partner_response_message',
              ).isNotEmpty ||
              _text(
                viewing,
                'completion_notes',
              ).isNotEmpty) ...[
            const SizedBox(height: 12),
            _DetailSection(
              title: 'Notes',
              icon: Icons.notes_outlined,
              children: [
                if (_text(
                  viewing,
                  'customer_message',
                ).isNotEmpty)
                  _DetailRow(
                    label: 'Customer',
                    value: _text(
                      viewing,
                      'customer_message',
                    ),
                  ),
                if (_text(
                  viewing,
                  'partner_response_message',
                ).isNotEmpty)
                  _DetailRow(
                    label: 'Partner',
                    value: _text(
                      viewing,
                      'partner_response_message',
                    ),
                  ),
                if (_text(
                  viewing,
                  'completion_notes',
                ).isNotEmpty)
                  _DetailRow(
                    label: 'Completion',
                    value: _text(
                      viewing,
                      'completion_notes',
                    ),
                  ),
              ],
            ),
          ],

          const SizedBox(height: 12),

          _DetailSection(
            title: 'Deal',
            icon: Icons.handshake_outlined,
            children: [
              _DetailRow(
                label: 'Linked deal',
                value: dealId.isEmpty
                    ? 'No deal linked'
                    : 'Deal #$dealId',
              ),
              _DetailRow(
                label: 'Partner outcome',
                value: partnerOutcomeSubmitted
                    ? 'Submitted'
                    : 'Not submitted',
              ),
            ],
          ),

          const SizedBox(height: 12),

          _buildTimeline(),

          const SizedBox(height: 12),

          _DetailSection(
            title: 'Record',
            icon: Icons.history_outlined,
            children: [
              _DetailRow(
                label: 'Created',
                value: _formatDateTime(
                  _text(
                    viewing,
                    'created_at',
                  ),
                ),
              ),
              _DetailRow(
                label: 'Last updated',
                value: _formatDateTime(
                  _text(
                    viewing,
                    'updated_at',
                  ),
                ),
              ),
            ],
          ),

          const SizedBox(height: 24),
        ],
      ),
    );
  }

  Widget _buildTimeline() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment:
              CrossAxisAlignment.start,
          children: [
            const Row(
              children: [
                Icon(
                  Icons.timeline_outlined,
                  color: Color(0xFF14532D),
                ),
                SizedBox(width: 8),
                Text(
                  'Viewing Timeline',
                  style: TextStyle(
                    fontSize: 18,
                    fontWeight:
                        FontWeight.bold,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),

            if (_events.isEmpty)
              const Text(
                'No operational events have been recorded yet.',
                style: TextStyle(
                  color: Colors.black54,
                ),
              )
            else
              ..._events.map(
                (event) => _TimelineEvent(
                  label: _displayText(
                    _text(
                      event,
                      'event_label',
                    ),
                    fallback: 'Viewing event',
                  ),
                  actor: _displayText(
                    _text(
                      event,
                      'actor_name',
                    ),
                    fallback: 'System',
                  ),
                  notes: _text(
                    event,
                    'notes',
                  ),
                  timestamp: _formatDateTime(
                    _text(
                      event,
                      'created_at',
                    ),
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _DetailSection extends StatelessWidget {
  const _DetailSection({
    required this.title,
    required this.icon,
    required this.children,
  });

  final String title;
  final IconData icon;
  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment:
              CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  icon,
                  color: const Color(0xFF14532D),
                ),
                const SizedBox(width: 8),
                Text(
                  title,
                  style: const TextStyle(
                    fontSize: 18,
                    fontWeight:
                        FontWeight.bold,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 14),
            ...children,
          ],
        ),
      ),
    );
  }
}

class _DetailRow extends StatelessWidget {
  const _DetailRow({
    required this.label,
    required this.value,
  });

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(
        bottom: 12,
      ),
      child: Row(
        crossAxisAlignment:
            CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 125,
            child: Text(
              label,
              style: const TextStyle(
                color: Colors.black54,
                fontWeight: FontWeight.w500,
              ),
            ),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              value,
              style: const TextStyle(
                fontWeight: FontWeight.w500,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _TimelineEvent extends StatelessWidget {
  const _TimelineEvent({
    required this.label,
    required this.actor,
    required this.notes,
    required this.timestamp,
  });

  final String label;
  final String actor;
  final String notes;
  final String timestamp;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(
        bottom: 18,
      ),
      child: Row(
        crossAxisAlignment:
            CrossAxisAlignment.start,
        children: [
          Container(
            width: 12,
            height: 12,
            margin: const EdgeInsets.only(
              top: 5,
            ),
            decoration: const BoxDecoration(
              color: Color(0xFF14532D),
              shape: BoxShape.circle,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment:
                  CrossAxisAlignment.start,
              children: [
                Text(
                  label,
                  style: const TextStyle(
                    fontWeight:
                        FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 3),
                Text(
                  '$actor • $timestamp',
                  style: const TextStyle(
                    color: Colors.black54,
                    fontSize: 13,
                  ),
                ),
                if (notes.isNotEmpty) ...[
                  const SizedBox(height: 5),
                  Text(notes),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }
}