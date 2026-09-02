import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'package:mobile/services/property_service.dart';
import 'package:mobile/services/staff_deal_admin_service.dart';

class StaffDealDetailScreen extends StatefulWidget {
  const StaffDealDetailScreen({super.key, required this.dealId});

  final int dealId;

  @override
  State<StaffDealDetailScreen> createState() {
    return _StaffDealDetailScreenState();
  }
}

class _StaffDealDetailScreenState extends State<StaffDealDetailScreen> {
  bool _isLoading = true;
  String? _errorMessage;
  bool _isIssuingOwnerConfirmation = false;
  Map<String, dynamic>? _ownerConfirmationResult;
  Map<String, dynamic>? _deal;
  List<Map<String, dynamic>> _timeline = [];
  Map<String, dynamic>? _ownerGovernance;

  @override
  void initState() {
    super.initState();
    _loadDeal();
  }

  Future<void> _loadDeal() async {
    if (!mounted) {
      return;
    }

    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final results = await Future.wait([
        StaffDealAdminService.instance.fetchDeal(widget.dealId),
        StaffDealAdminService.instance.fetchTimeline(widget.dealId),
        StaffDealAdminService.instance.fetchOwnerConfirmationStatus(
          widget.dealId,
        ),
      ]);

      final deal = results[0];
      final timelineResponse = results[1];
      final ownerGovernance = results[2];

      final rawTimeline = timelineResponse['timeline'];

      final timeline = <Map<String, dynamic>>[];

      if (rawTimeline is List) {
        for (final item in rawTimeline) {
          if (item is Map) {
            timeline.add(Map<String, dynamic>.from(item));
          }
        }
      }

      if (!mounted) {
        return;
      }

      setState(() {
        _deal = deal;
        _timeline = timeline;
        _ownerGovernance = ownerGovernance;
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

  Future<void> _issueOwnerConfirmation() async {
    final deal = _deal;

    if (deal == null) {
      return;
    }

    if (deal['owner_confirmed'] == true) {
      return;
    }

    final isReissue = _ownerConfirmationResult != null;

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) {
        return AlertDialog(
          title: Text(
            isReissue
                ? 'Reissue owner confirmation?'
                : 'Issue owner confirmation?',
          ),
          content: Text(
            isReissue
                ? 'The current unused link will be revoked and replaced '
                    'with a new single-use owner confirmation link.'
                : 'A new single-use owner confirmation link will be issued. '
                    'Copy it and send it only to the verified property owner.',
          ),
          actions: [
            TextButton(
              onPressed: () {
                Navigator.of(dialogContext).pop(false);
              },
              child: const Text('Cancel'),
            ),
            FilledButton(
              onPressed: () {
                Navigator.of(dialogContext).pop(true);
              },
              child: Text(isReissue ? 'Reissue' : 'Issue'),
            ),
          ],
        );
      },
    );

    if (confirmed != true || !mounted) {
      return;
    }

    setState(() {
      _isIssuingOwnerConfirmation = true;
    });

    try {
      final result = await StaffDealAdminService.instance
          .issueOwnerConfirmation(widget.dealId);

      if (!mounted) {
        return;
      }

      setState(() {
        _ownerConfirmationResult = result;
        _isIssuingOwnerConfirmation = false;
      });

      await _loadDeal();
    } catch (error) {
      if (!mounted) {
        return;
      }

      setState(() {
        _isIssuingOwnerConfirmation = false;
      });

      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(_cleanError(error))));
    }
  }

  String _ownerConfirmationUrl(
    Map<String, dynamic> confirmation,
  ) {
    final token = _text(confirmation, 'token');

    if (token.isEmpty) {
      return '';
    }

    final baseUrl = PropertyService.baseUrl.replaceFirst(
      RegExp(r'/+$'),
      '',
    );

    return '$baseUrl/owner-confirmation/'
        '${Uri.encodeComponent(token)}/';
  }

  Future<void> _copyOwnerConfirmationLink(
    String url,
  ) async {
    await Clipboard.setData(
      ClipboardData(text: url),
    );

    if (!mounted) {
      return;
    }

    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text(
          'Owner confirmation link copied.',
        ),
      ),
    );
  }

  String _cleanError(Object error) {
    return error.toString().replaceFirst(RegExp(r'^Exception:\s*'), '').trim();
  }

  String _text(Map<String, dynamic> data, String key) {
    final value = data[key];

    if (value == null) {
      return '';
    }

    return value.toString().trim();
  }

  String _displayText(String value, {String fallback = 'Not recorded'}) {
    return value.trim().isEmpty ? fallback : value.trim();
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
        return 'Terms agreed';

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
            .where((word) => word.isNotEmpty)
            .map(
              (word) =>
                  '${word[0].toUpperCase()}'
                  '${word.substring(1)}',
            )
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

  String _formatMoney(dynamic value) {
    if (value == null) {
      return 'Not set';
    }

    final amount = double.tryParse(value.toString());

    if (amount == null) {
      return 'Not set';
    }

    final formatted = amount.round().toString().replaceAllMapped(
      RegExp(r'\B(?=(\d{3})+(?!\d))'),
      (match) => ',',
    );

    return 'KES $formatted';
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

    final minute = local.minute.toString().padLeft(2, '0');

    return '$year-$month-$day  $hour:$minute';
  }

  String _transactionType(Map<String, dynamic> deal) {
    final monthlyRent = deal['monthly_rent'];

    final salePrice = deal['sale_price'];

    if (monthlyRent != null) {
      return 'Rental';
    }

    if (salePrice != null) {
      return 'Sale';
    }

    final listingType = _text(deal, 'listing_type');

    if (listingType == 'rent') {
      return 'Rental';
    }

    if (listingType == 'sale') {
      return 'Sale';
    }

    return 'Not set';
  }

  String _transactionValue(Map<String, dynamic> deal) {
    if (deal['monthly_rent'] != null) {
      return _formatMoney(deal['monthly_rent']);
    }

    if (deal['sale_price'] != null) {
      return _formatMoney(deal['sale_price']);
    }

    return 'Not set';
  }

  Widget _buildOwnerConfirmationOperations(Map<String, dynamic> deal) {
    final governance = _ownerGovernance;

    if (governance == null) {
      return const Card(
        child: Padding(
          padding: EdgeInsets.all(18),
          child: Text('Owner confirmation governance is unavailable.'),
        ),
      );
    }

    final state = _text(governance, 'state');

    final message = _text(governance, 'message');

    final eligible = governance['eligible'] == true;

    Color stateColor;

    IconData stateIcon;

    String stateTitle;

    switch (state) {
      case 'ready':
        stateColor = const Color(0xFF15803D);
        stateIcon = Icons.check_circle_outline;
        stateTitle = 'Ready for owner confirmation';

      case 'blocked':
        stateColor = const Color(0xFFB45309);
        stateIcon = Icons.policy_outlined;
        stateTitle = 'Blocked by governance';

      case 'confirmed':
        stateColor = const Color(0xFF15803D);
        stateIcon = Icons.verified_outlined;
        stateTitle = 'Owner confirmed';

      case 'not_applicable':
        stateColor = Colors.blueGrey;
        stateIcon = Icons.info_outline;
        stateTitle = 'Owner confirmation not required';

      default:
        stateColor = Colors.blueGrey;
        stateIcon = Icons.info_outline;
        stateTitle = 'Owner confirmation status';
    }

    final result = _ownerConfirmationResult;

    final ownerRaw = result?['owner'];

    final confirmationRaw = result?['confirmation'];

    final owner = ownerRaw is Map
        ? Map<String, dynamic>.from(ownerRaw)
        : <String, dynamic>{};

    final confirmation = confirmationRaw is Map
        ? Map<String, dynamic>.from(confirmationRaw)
        : <String, dynamic>{};

    final ownerName = _text(owner, 'legal_name');

    final ownerPhone = _text(owner, 'phone_number');

    final ownerEmail = _text(owner, 'email');

    final expiresAt = _text(confirmation, 'expires_at');

    final confirmationUrl = _ownerConfirmationUrl(confirmation);

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Row(
              children: [
                Icon(Icons.verified_user_outlined, color: Color(0xFF14532D)),
                SizedBox(width: 8),
                Text(
                  'Owner Confirmation Operations',
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                ),
              ],
            ),

            const SizedBox(height: 14),

            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: stateColor.withValues(alpha: 0.10),
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: stateColor.withValues(alpha: 0.30)),
              ),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Icon(stateIcon, color: stateColor),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          stateTitle,
                          style: TextStyle(
                            color: stateColor,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        if (message.isNotEmpty) ...[
                          const SizedBox(height: 4),
                          Text(
                            message,
                            style: const TextStyle(color: Colors.black87),
                          ),
                        ],
                      ],
                    ),
                  ),
                ],
              ),
            ),

            if (state == 'blocked') ...[
              const SizedBox(height: 12),
              const Text(
                'This is a governance safeguard, not an application error.',
                style: TextStyle(color: Colors.black54, fontSize: 13),
              ),
            ],

            if (eligible) ...[
              const SizedBox(height: 14),
              SizedBox(
                width: double.infinity,
                child: FilledButton.icon(
                  onPressed: _isIssuingOwnerConfirmation
                      ? null
                      : _issueOwnerConfirmation,
                  icon: _isIssuingOwnerConfirmation
                      ? const SizedBox(
                          width: 18,
                          height: 18,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Icon(Icons.outgoing_mail),
                  label: Text(
                    _isIssuingOwnerConfirmation
                        ? 'Issuing...'
                        : result == null
                        ? 'Issue Owner Confirmation'
                        : 'Reissue Owner Confirmation',
                  ),
                ),
              ),
            ],

            if (result != null) ...[
              const SizedBox(height: 16),
              const Divider(),
              const SizedBox(height: 10),

              const Text(
                'Confirmation issued',
                style: TextStyle(fontWeight: FontWeight.bold),
              ),

              if (ownerName.isNotEmpty) ...[
                const SizedBox(height: 8),
                _DealRow(label: 'Owner', value: ownerName),
              ],

              if (ownerPhone.isNotEmpty)
                _DealRow(label: 'Phone', value: ownerPhone),

              if (ownerEmail.isNotEmpty)
                _DealRow(label: 'Email', value: ownerEmail),

              if (expiresAt.isNotEmpty)
                _DealRow(label: 'Expires', value: _formatDateTime(expiresAt)),

              if (confirmationUrl.isNotEmpty) ...[
                const SizedBox(height: 14),
                const Text(
                  'Copy this secure link now and send it only to the '
                  'verified owner. Only the latest issued link works.',
                  style: TextStyle(
                    color: Colors.black54,
                    fontSize: 13,
                  ),
                ),
                const SizedBox(height: 10),
                SizedBox(
                  width: double.infinity,
                  child: OutlinedButton.icon(
                    onPressed: () =>
                        _copyOwnerConfirmationLink(confirmationUrl),
                    icon: const Icon(Icons.copy_outlined),
                    label: const Text(
                      'Copy Owner Confirmation Link',
                    ),
                  ),
                ),
              ],
            ],
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF6F8F6),
      appBar: AppBar(
        title: Text('Deal #${widget.dealId}'),
        backgroundColor: const Color(0xFF14532D),
        foregroundColor: Colors.white,
        actions: [
          IconButton(
            tooltip: 'Refresh',
            onPressed: _isLoading ? null : _loadDeal,
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      body: _buildBody(),
    );
  }

  Widget _buildBody() {
    if (_isLoading && _deal == null) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_errorMessage != null && _deal == null) {
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
                onPressed: _loadDeal,
                icon: const Icon(Icons.refresh),
                label: const Text('Try Again'),
              ),
            ],
          ),
        ),
      );
    }

    final deal = _deal;

    if (deal == null) {
      return const Center(child: Text('Deal information is unavailable.'));
    }

    final status = _text(deal, 'status');

    final propertyTitle = _text(deal, 'property_title');

    final customerName = _text(deal, 'customer_name');

    final partnerName = _text(deal, 'partner_name');

    final outcomesRaw = deal['outcomes'];

    final outcomes = <Map<String, dynamic>>[];

    if (outcomesRaw is List) {
      for (final item in outcomesRaw) {
        if (item is Map) {
          outcomes.add(Map<String, dynamic>.from(item));
        }
      }
    }

    return RefreshIndicator(
      onRefresh: _loadDeal,
      child: ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(16),
        children: [
          if (_isLoading)
            const Padding(
              padding: EdgeInsets.only(bottom: 12),
              child: LinearProgressIndicator(),
            ),

          Card(
            child: Padding(
              padding: const EdgeInsets.all(18),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Expanded(
                        child: Text(
                          propertyTitle.isEmpty ? 'Deal' : propertyTitle,
                          style: const TextStyle(
                            fontSize: 22,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ),
                      const SizedBox(width: 10),
                      Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 10,
                          vertical: 6,
                        ),
                        decoration: BoxDecoration(
                          color: _statusColor(status).withValues(alpha: 0.12),
                          borderRadius: BorderRadius.circular(20),
                        ),
                        child: Text(
                          _statusLabel(status),
                          style: TextStyle(
                            color: _statusColor(status),
                            fontWeight: FontWeight.w600,
                            fontSize: 12,
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Text(
                    _displayText(
                      _text(deal, 'deal_number'),
                      fallback: 'Deal #${widget.dealId}',
                    ),
                    style: const TextStyle(color: Colors.black54),
                  ),
                  const SizedBox(height: 14),
                  Text(
                    _transactionValue(deal),
                    style: const TextStyle(
                      fontSize: 20,
                      fontWeight: FontWeight.bold,
                      color: Color(0xFF14532D),
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    _transactionType(deal),
                    style: const TextStyle(color: Colors.black54),
                  ),
                ],
              ),
            ),
          ),

          const SizedBox(height: 12),

          _DealSection(
            title: 'Participants',
            icon: Icons.people_outline,
            children: [
              _DealRow(label: 'Customer', value: _displayText(customerName)),
              _DealRow(label: 'Partner', value: _displayText(partnerName)),
              _DealRow(label: 'Property', value: _displayText(propertyTitle)),
              _DealRow(
                label: 'Viewing',
                value: _text(deal, 'viewing').isEmpty
                    ? 'Not recorded'
                    : 'Viewing #${_text(deal, 'viewing')}',
              ),
            ],
          ),

          const SizedBox(height: 12),

          _DealSection(
            title: 'Transaction',
            icon: Icons.handshake_outlined,
            children: [
              _DealRow(label: 'Type', value: _transactionType(deal)),
              _DealRow(label: 'Value', value: _transactionValue(deal)),
              _DealRow(
                label: 'Commission',
                value: _formatMoney(deal['commission_amount']),
              ),
              _DealRow(
                label: 'Viewing status',
                value: _statusLabel(_text(deal, 'viewing_status')),
              ),
            ],
          ),

          const SizedBox(height: 12),

          _buildConfirmations(deal),

          const SizedBox(height: 12),

          _buildOwnerConfirmationOperations(deal),

          const SizedBox(height: 12),

          _buildOutcomes(outcomes),

          const SizedBox(height: 12),

          _buildTimeline(),

          const SizedBox(height: 12),

          _DealSection(
            title: 'Record',
            icon: Icons.history_outlined,
            children: [
              _DealRow(
                label: 'Created',
                value: _formatDateTime(_text(deal, 'created_at')),
              ),
              _DealRow(
                label: 'Updated',
                value: _formatDateTime(_text(deal, 'updated_at')),
              ),
              _DealRow(
                label: 'Agreed',
                value: _formatDateTime(_text(deal, 'agreed_at')),
              ),
              _DealRow(
                label: 'Completed',
                value: _formatDateTime(_text(deal, 'completed_at')),
              ),
              if (_text(deal, 'cancellation_reason').isNotEmpty)
                _DealRow(
                  label: 'Cancellation',
                  value: _text(deal, 'cancellation_reason'),
                ),
            ],
          ),

          const SizedBox(height: 24),
        ],
      ),
    );
  }

  Widget _buildConfirmations(Map<String, dynamic> deal) {
    final customerConfirmed = deal['customer_confirmed'] == true;

    final partnerConfirmed = deal['partner_confirmed'] == true;

    final ownerConfirmed = deal['owner_confirmed'] == true;

    final allConfirmed =
        customerConfirmed && partnerConfirmed && ownerConfirmed;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Row(
              children: [
                Icon(Icons.verified_user_outlined, color: Color(0xFF14532D)),
                SizedBox(width: 8),
                Text(
                  'Confirmations',
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                ),
              ],
            ),
            const SizedBox(height: 16),

            _ConfirmationRow(
              label: 'Customer',
              confirmed: customerConfirmed,
              timestamp: _formatDateTime(_text(deal, 'customer_confirmed_at')),
            ),

            _ConfirmationRow(
              label: 'Partner',
              confirmed: partnerConfirmed,
              timestamp: _formatDateTime(_text(deal, 'partner_confirmed_at')),
            ),

            _ConfirmationRow(
              label: 'Owner',
              confirmed: ownerConfirmed,
              timestamp: _formatDateTime(_text(deal, 'owner_confirmed_at')),
            ),

            if (allConfirmed) ...[
              const SizedBox(height: 8),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: const Color(0xFFF0FDF4),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: const Color(0xFFBBF7D0)),
                ),
                child: const Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Icon(Icons.verified, color: Color(0xFF15803D)),
                    SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        'Verified transaction. '
                        'Customer, partner and owner '
                        'have all confirmed the deal.',
                        style: TextStyle(color: Color(0xFF14532D)),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildOutcomes(List<Map<String, dynamic>> outcomes) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Row(
              children: [
                Icon(Icons.fact_check_outlined, color: Color(0xFF14532D)),
                SizedBox(width: 8),
                Text(
                  'Reported Outcomes',
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                ),
              ],
            ),
            const SizedBox(height: 16),

            if (outcomes.isEmpty)
              const Text(
                'No outcomes have been submitted yet.',
                style: TextStyle(color: Colors.black54),
              )
            else
              ...outcomes.map(
                (outcome) => _OutcomeCard(
                  reporter: _displayText(
                    _text(outcome, 'reporter_label'),
                    fallback: 'Reporter',
                  ),
                  outcome: _displayText(
                    _text(outcome, 'outcome_label'),
                    fallback: 'Outcome recorded',
                  ),
                  notes: _text(outcome, 'notes'),
                  timestamp: _formatDateTime(_text(outcome, 'created_at')),
                ),
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildTimeline() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Row(
              children: [
                Icon(Icons.timeline_outlined, color: Color(0xFF14532D)),
                SizedBox(width: 8),
                Text(
                  'Transaction Timeline',
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                ),
              ],
            ),
            const SizedBox(height: 16),

            if (_timeline.isEmpty)
              const Text(
                'No timeline events have been recorded yet.',
                style: TextStyle(color: Colors.black54),
              )
            else
              ..._timeline.map(
                (event) => _TimelineItem(
                  title: _displayText(
                    _text(event, 'title'),
                    fallback: 'Transaction event',
                  ),
                  description: _text(event, 'description'),
                  actor: _displayText(
                    _text(event, 'actor'),
                    fallback: 'System',
                  ),
                  source: _statusLabel(_text(event, 'source')),
                  timestamp: _formatDateTime(_text(event, 'timestamp')),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _DealSection extends StatelessWidget {
  const _DealSection({
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
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(icon, color: const Color(0xFF14532D)),
                const SizedBox(width: 8),
                Text(
                  title,
                  style: const TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
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

class _DealRow extends StatelessWidget {
  const _DealRow({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 120,
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
              style: const TextStyle(fontWeight: FontWeight.w500),
            ),
          ),
        ],
      ),
    );
  }
}

class _ConfirmationRow extends StatelessWidget {
  const _ConfirmationRow({
    required this.label,
    required this.confirmed,
    required this.timestamp,
  });

  final String label;
  final bool confirmed;
  final String timestamp;

  @override
  Widget build(BuildContext context) {
    final color = confirmed ? const Color(0xFF15803D) : const Color(0xFFB45309);

    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Row(
        children: [
          Icon(
            confirmed ? Icons.check_circle_outline : Icons.schedule_outlined,
            color: color,
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '$label ${confirmed ? 'confirmed' : 'waiting'}',
                  style: TextStyle(color: color, fontWeight: FontWeight.w600),
                ),
                if (confirmed && timestamp != 'Not recorded')
                  Padding(
                    padding: const EdgeInsets.only(top: 2),
                    child: Text(
                      timestamp,
                      style: const TextStyle(
                        fontSize: 12,
                        color: Colors.black54,
                      ),
                    ),
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _OutcomeCard extends StatelessWidget {
  const _OutcomeCard({
    required this.reporter,
    required this.outcome,
    required this.notes,
    required this.timestamp,
  });

  final String reporter;
  final String outcome;
  final String notes;
  final String timestamp;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: const Color(0xFFF9FAFB),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: const Color(0xFFE5E7EB)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(reporter, style: const TextStyle(fontWeight: FontWeight.bold)),
          const SizedBox(height: 4),
          Text(outcome),
          if (notes.isNotEmpty) ...[
            const SizedBox(height: 7),
            Text(notes, style: const TextStyle(color: Colors.black87)),
          ],
          const SizedBox(height: 7),
          Text(
            timestamp,
            style: const TextStyle(color: Colors.black54, fontSize: 12),
          ),
        ],
      ),
    );
  }
}

class _TimelineItem extends StatelessWidget {
  const _TimelineItem({
    required this.title,
    required this.description,
    required this.actor,
    required this.source,
    required this.timestamp,
  });

  final String title;
  final String description;
  final String actor;
  final String source;
  final String timestamp;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 18),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 12,
            height: 12,
            margin: const EdgeInsets.only(top: 5),
            decoration: const BoxDecoration(
              color: Color(0xFF14532D),
              shape: BoxShape.circle,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: const TextStyle(fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 3),
                Text(
                  '$actor • $timestamp',
                  style: const TextStyle(color: Colors.black54, fontSize: 12),
                ),
                const SizedBox(height: 3),
                Text(
                  source,
                  style: const TextStyle(
                    color: Color(0xFF14532D),
                    fontSize: 11,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                if (description.isNotEmpty) ...[
                  const SizedBox(height: 5),
                  Text(description),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }
}
