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
  bool _isUpdatingAccess = false;
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

  Map<String, dynamic> get _governance {
    final value = _partner?['governance'];

    if (value is Map) {
      return Map<String, dynamic>.from(value);
    }

    return <String, dynamic>{};
  }

  List<Map<String, dynamic>> get _policyOptions {
    final value = _governance['policy_options'];

    if (value is! List) {
      return const [];
    }

    return value
        .whereType<Map>()
        .map((item) => Map<String, dynamic>.from(item))
        .toList(growable: false);
  }

  bool get _isPermanentlyBanned {
    return _governance['permanently_banned'] == true;
  }

  Future<_PartnerRestrictionDecision?> _showRestrictionDialog({
    required bool permanent,
  }) async {
    final availablePolicies = permanent
        ? _policyOptions.where((policy) {
            return policy['recommended_action'] == 'permanent_ban';
          }).toList(growable: false)
        : _policyOptions.where((policy) {
            return policy['recommended_action'] != 'permanent_ban';
          }).toList(growable: false);

    final policies = availablePolicies.isEmpty
        ? _policyOptions
        : availablePolicies;

    if (policies.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text(
            'No active partner policies are configured.',
          ),
        ),
      );
      return null;
    }

    final reasonController = TextEditingController();
    var selectedPolicyCode = policies.first['code']?.toString() ?? '';
    var durationDays = 7;
    String? validationMessage;

    try {
      return await showDialog<_PartnerRestrictionDecision>(
        context: context,
        barrierDismissible: false,
        builder: (dialogContext) {
          return StatefulBuilder(
            builder: (context, setDialogState) {
              return AlertDialog(
                title: Text(
                  permanent
                      ? 'Permanently ban partner?'
                      : 'Suspend partner?',
                ),
                content: SingleChildScrollView(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        permanent
                            ? 'This removes operational access but keeps '
                                  'the partner, property, payment, and '
                                  'audit records.'
                            : 'The partner will immediately lose posting '
                                  'and viewing access.',
                      ),
                      const SizedBox(height: 16),
                      DropdownButtonFormField<String>(
                        initialValue: selectedPolicyCode,
                        decoration: const InputDecoration(
                          labelText: 'Policy infringed',
                          border: OutlineInputBorder(),
                        ),
                        isExpanded: true,
                        items: policies.map((policy) {
                          final code = policy['code']?.toString() ?? '';
                          final title = policy['title']?.toString() ?? '';

                          return DropdownMenuItem<String>(
                            value: code,
                            child: Text(
                              '$code — $title',
                              overflow: TextOverflow.ellipsis,
                            ),
                          );
                        }).toList(growable: false),
                        onChanged: (value) {
                          if (value != null) {
                            selectedPolicyCode = value;
                          }
                        },
                      ),
                      if (!permanent) ...[
                        const SizedBox(height: 14),
                        DropdownButtonFormField<int>(
                          initialValue: durationDays,
                          decoration: const InputDecoration(
                            labelText: 'Suspension period',
                            border: OutlineInputBorder(),
                          ),
                          items: const [
                            DropdownMenuItem(
                              value: 7,
                              child: Text('7 days'),
                            ),
                            DropdownMenuItem(
                              value: 30,
                              child: Text('30 days'),
                            ),
                            DropdownMenuItem(
                              value: 90,
                              child: Text('90 days'),
                            ),
                          ],
                          onChanged: (value) {
                            if (value != null) {
                              durationDays = value;
                            }
                          },
                        ),
                      ],
                      const SizedBox(height: 14),
                      TextField(
                        controller: reasonController,
                        minLines: 3,
                        maxLines: 5,
                        decoration: const InputDecoration(
                          labelText: 'Infringement and decision reason',
                          hintText: (
                            'Explain what happened and the evidence reviewed.'
                          ),
                          border: OutlineInputBorder(),
                        ),
                      ),
                      if (validationMessage != null) ...[
                        const SizedBox(height: 10),
                        Text(
                          validationMessage!,
                          style: const TextStyle(
                            color: Color(0xFFB91C1C),
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
                actions: [
                  TextButton(
                    onPressed: () => Navigator.of(dialogContext).pop(),
                    child: const Text('Cancel'),
                  ),
                  FilledButton(
                    style: permanent
                        ? FilledButton.styleFrom(
                            backgroundColor: const Color(0xFFB91C1C),
                          )
                        : null,
                    onPressed: () {
                      final reason = reasonController.text.trim();

                      if (reason.length < 10) {
                        setDialogState(() {
                          validationMessage = (
                            'Please provide a clear reason of at least '
                            '10 characters.'
                          );
                        });
                        return;
                      }

                      Navigator.of(dialogContext).pop(
                        _PartnerRestrictionDecision(
                          policyCode: selectedPolicyCode,
                          actionType: permanent
                              ? 'permanent_ban'
                              : durationDays == 7
                              ? 'short_suspension'
                              : 'long_suspension',
                          durationDays: permanent ? null : durationDays,
                          reason: reason,
                          permanent: permanent,
                        ),
                      );
                    },
                    child: Text(
                      permanent ? 'Permanently Ban' : 'Suspend Partner',
                    ),
                  ),
                ],
              );
            },
          );
        },
      );
    } finally {
      reasonController.dispose();
    }
  }

  Future<void> _restrictPartner({
    required bool permanent,
  }) async {
    final decision = await _showRestrictionDialog(
      permanent: permanent,
    );

    if (decision == null || !mounted) {
      return;
    }

    setState(() {
      _isUpdatingAccess = true;
    });

    try {
      await StaffPartnerAdminService.instance.restrictPartner(
        partnerId: widget.partnerId,
        policyCode: decision.policyCode,
        actionType: decision.actionType,
        reason: decision.reason,
        durationDays: decision.durationDays,
        confirmPermanentBan: decision.permanent,
      );

      if (!mounted) {
        return;
      }

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            permanent
                ? 'Partner permanently banned.'
                : 'Partner suspended.',
          ),
        ),
      );

      await _loadPartner();
    } catch (error) {
      if (!mounted) {
        return;
      }

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(_cleanError(error))),
      );
    } finally {
      if (mounted) {
        setState(() {
          _isUpdatingAccess = false;
        });
      }
    }
  }

  Future<void> _restorePartnerAccess() async {
    final reasonController = TextEditingController();
    String? validationMessage;

    try {
      final reason = await showDialog<String>(
        context: context,
        barrierDismissible: false,
        builder: (dialogContext) {
          return StatefulBuilder(
            builder: (context, setDialogState) {
              return AlertDialog(
                title: Text(
                  _isPermanentlyBanned
                      ? 'Reverse permanent ban?'
                      : 'Restore partner access?',
                ),
                content: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      _isPermanentlyBanned
                          ? 'This is a high-impact reversal and will be '
                                'recorded permanently.'
                          : 'The partner will regain posting and viewing '
                                'access.',
                    ),
                    const SizedBox(height: 14),
                    TextField(
                      controller: reasonController,
                      minLines: 3,
                      maxLines: 5,
                      decoration: const InputDecoration(
                        labelText: 'Reinstatement reason',
                        border: OutlineInputBorder(),
                      ),
                    ),
                    if (validationMessage != null) ...[
                      const SizedBox(height: 10),
                      Text(
                        validationMessage!,
                        style: const TextStyle(
                          color: Color(0xFFB91C1C),
                        ),
                      ),
                    ],
                  ],
                ),
                actions: [
                  TextButton(
                    onPressed: () => Navigator.of(dialogContext).pop(),
                    child: const Text('Cancel'),
                  ),
                  FilledButton(
                    onPressed: () {
                      final value = reasonController.text.trim();

                      if (value.length < 10) {
                        setDialogState(() {
                          validationMessage = (
                            'Please provide a clear reason of at least '
                            '10 characters.'
                          );
                        });
                        return;
                      }

                      Navigator.of(dialogContext).pop(value);
                    },
                    child: Text(
                      _isPermanentlyBanned
                          ? 'Reverse Ban and Restore'
                          : 'Restore Access',
                    ),
                  ),
                ],
              );
            },
          );
        },
      );

      if (reason == null || !mounted) {
        return;
      }

      setState(() {
        _isUpdatingAccess = true;
      });

      try {
        await StaffPartnerAdminService.instance.reinstatePartner(
          partnerId: widget.partnerId,
          reason: reason,
          confirmPermanentBanReversal: _isPermanentlyBanned,
        );

        if (!mounted) {
          return;
        }

        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Partner access restored.'),
          ),
        );

        await _loadPartner();
      } catch (error) {
        if (!mounted) {
          return;
        }

        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(_cleanError(error))),
        );
      } finally {
        if (mounted) {
          setState(() {
            _isUpdatingAccess = false;
          });
        }
      }
    } finally {
      reasonController.dispose();
    }
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
          _PartnerAccessControlCard(
            governance: _governance,
            isActive: _boolean('is_active'),
            isProcessing: _isUpdatingAccess,
            onSuspend: () => _restrictPartner(permanent: false),
            onPermanentBan: () => _restrictPartner(permanent: true),
            onRestore: _restorePartnerAccess,
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

class _PartnerAccessControlCard extends StatelessWidget {
  const _PartnerAccessControlCard({
    required this.governance,
    required this.isActive,
    required this.isProcessing,
    required this.onSuspend,
    required this.onPermanentBan,
    required this.onRestore,
  });

  final Map<String, dynamic> governance;
  final bool isActive;
  final bool isProcessing;
  final VoidCallback onSuspend;
  final VoidCallback onPermanentBan;
  final VoidCallback onRestore;

  @override
  Widget build(BuildContext context) {
    final restricted = governance['restricted'] == true;
    final permanentlyBanned = governance['permanently_banned'] == true;
    final policies = governance['policy_options'];
    final hasPolicies = policies is List && policies.isNotEmpty;
    final rawActions = governance['actions'];
    final actions = rawActions is List
        ? rawActions.whereType<Map>().toList(growable: false)
        : const <Map>[];

    final color = permanentlyBanned
        ? const Color(0xFF991B1B)
        : restricted || !isActive
        ? const Color(0xFFB45309)
        : const Color(0xFF15803D);

    final statusText = permanentlyBanned
        ? 'Permanently banned'
        : restricted
        ? 'Suspended'
        : isActive
        ? 'Access active'
        : 'Access inactive';

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Row(
              children: [
                Icon(
                  Icons.admin_panel_settings_outlined,
                  color: Color(0xFF14532D),
                ),
                SizedBox(width: 9),
                Text(
                  'Partner Access Control',
                  style: TextStyle(
                    fontSize: 17,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.symmetric(
                horizontal: 10,
                vertical: 6,
              ),
              decoration: BoxDecoration(
                color: color.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(20),
              ),
              child: Text(
                statusText,
                style: TextStyle(
                  color: color,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
            if (actions.isNotEmpty) ...[
              const SizedBox(height: 12),
              ...actions.map((action) {
                final label =
                    action['action_type_label']?.toString() ?? 'Restriction';
                final reason = action['reason']?.toString() ?? '';
                final endsAt = action['ends_at']?.toString() ?? '';

                return Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        label,
                        style: const TextStyle(
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      if (reason.trim().isNotEmpty) Text(reason),
                      if (endsAt.trim().isNotEmpty)
                        Text(
                          'Scheduled end: ${_formatAccessDate(endsAt)}',
                          style: const TextStyle(
                            color: Colors.black54,
                          ),
                        ),
                    ],
                  ),
                );
              }),
            ],
            const SizedBox(height: 12),
            if (restricted || !isActive)
              SizedBox(
                width: double.infinity,
                child: FilledButton.icon(
                  onPressed: isProcessing ? null : onRestore,
                  icon: isProcessing
                      ? const SizedBox(
                          width: 18,
                          height: 18,
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                          ),
                        )
                      : const Icon(Icons.lock_open_outlined),
                  label: Text(
                    permanentlyBanned
                        ? 'Review and Restore Access'
                        : 'Restore Partner Access',
                  ),
                ),
              )
            else ...[
              if (!hasPolicies)
                const Padding(
                  padding: EdgeInsets.only(bottom: 10),
                  child: Text(
                    'No active policies are configured. Access actions '
                    'are unavailable until policies are loaded.',
                    style: TextStyle(color: Color(0xFFB45309)),
                  ),
                ),
              Row(
                children: [
                  Expanded(
                    child: OutlinedButton.icon(
                      onPressed: isProcessing || !hasPolicies
                          ? null
                          : onSuspend,
                      icon: const Icon(Icons.pause_circle_outline),
                      label: const Text('Suspend Partner'),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: OutlinedButton.icon(
                      style: OutlinedButton.styleFrom(
                        foregroundColor: const Color(0xFFB91C1C),
                      ),
                      onPressed: isProcessing || !hasPolicies
                          ? null
                          : onPermanentBan,
                      icon: const Icon(Icons.block_outlined),
                      label: const Text('Permanently Ban'),
                    ),
                  ),
                ],
              ),
            ],
            const SizedBox(height: 10),
            const Text(
              'Partner records and transaction history are always retained.',
              style: TextStyle(
                color: Colors.black54,
                fontSize: 12,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _PartnerRestrictionDecision {
  const _PartnerRestrictionDecision({
    required this.policyCode,
    required this.actionType,
    required this.durationDays,
    required this.reason,
    required this.permanent,
  });

  final String policyCode;
  final String actionType;
  final int? durationDays;
  final String reason;
  final bool permanent;
}

String _formatAccessDate(String value) {
  final parsed = DateTime.tryParse(value);

  if (parsed == null) {
    return value;
  }

  final local = parsed.toLocal();
  final month = local.month.toString().padLeft(2, '0');
  final day = local.day.toString().padLeft(2, '0');
  final year = local.year.toString();

  return '$year-$month-$day';
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
