import 'package:flutter/material.dart';

import 'package:mobile/services/staff_governance_service.dart';

class StaffGovernanceCaseDetailScreen extends StatefulWidget {
  const StaffGovernanceCaseDetailScreen({
    super.key,
    required this.governanceCase,
  });

  final Map<String, dynamic> governanceCase;

  @override
  State<StaffGovernanceCaseDetailScreen> createState() {
    return _StaffGovernanceCaseDetailScreenState();
  }
}

class _StaffGovernanceCaseDetailScreenState
    extends State<StaffGovernanceCaseDetailScreen> {
  bool _isSubmitting = false;

  String _text(String key) {
    return widget.governanceCase[key]?.toString().trim() ?? '';
  }

  int _integer(String key) {
    final value = widget.governanceCase[key];

    if (value is int) {
      return value;
    }

    if (value is num) {
      return value.toInt();
    }

    return int.tryParse(value?.toString() ?? '') ?? 0;
  }

  String _cleanError(Object error) {
    return error.toString().replaceFirst(RegExp(r'^Exception:\s*'), '').trim();
  }

  Future<String?> _askForNotes({
    required String title,
    required String message,
    required String actionLabel,
  }) async {
    var notes = '';

    return showDialog<String>(
      context: context,
      builder: (dialogContext) {
        return AlertDialog(
          title: Text(title),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(message, style: const TextStyle(height: 1.4)),
              const SizedBox(height: 16),
              TextField(
                maxLines: 4,
                maxLength: 2000,
                onChanged: (value) {
                  notes = value;
                },
                decoration: const InputDecoration(
                  labelText: 'Staff notes',
                  hintText: 'Record the reason for this decision.',
                  border: OutlineInputBorder(),
                ),
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () {
                Navigator.of(dialogContext).pop();
              },
              child: const Text('Cancel'),
            ),
            FilledButton(
              onPressed: () {
                Navigator.of(dialogContext).pop(notes.trim());
              },
              child: Text(actionLabel),
            ),
          ],
        );
      },
    );
  }

  Future<void> _submitDecision({
    required String decision,
    required String title,
    required String message,
    required String actionLabel,
  }) async {
    if (_isSubmitting) {
      return;
    }

    final notes = await _askForNotes(
      title: title,
      message: message,
      actionLabel: actionLabel,
    );

    if (notes == null || !mounted) {
      return;
    }

    setState(() {
      _isSubmitting = true;
    });

    try {
      final result = await StaffGovernanceService.instance.decideCase(
        caseId: _integer('id'),
        decision: decision,
        notes: notes,
      );

      if (!mounted) {
        return;
      }

      final responsibleRole = result['responsible_role']?.toString() ?? '';

      final status = result['status']?.toString() ?? '';

      String successMessage;

      if (decision == 'return_to_partner') {
        successMessage =
            'Case returned to the partner. '
            'The ball is now in the partner’s court.';
      } else if (decision == 'keep_blocked') {
        successMessage =
            'Governance review recorded. '
            'The deal remains blocked in Pata Hao’s court.';
      } else if (status == 'resolved') {
        successMessage = 'Governance case resolved successfully.';
      } else {
        successMessage = 'Governance decision recorded.';
      }

      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(successMessage)));

      if (responsibleRole != 'staff' || status != 'open') {
        Navigator.of(context).pop(true);
      }
    } catch (error) {
      if (!mounted) {
        return;
      }

      showDialog<void>(
        context: context,
        builder: (dialogContext) {
          return AlertDialog(
            title: const Text('Decision could not be completed'),
            content: Text(
              _cleanError(error),
              style: const TextStyle(height: 1.4),
            ),
            actions: [
              FilledButton(
                onPressed: () {
                  Navigator.of(dialogContext).pop();
                },
                child: const Text('OK'),
              ),
            ],
          );
        },
      );
    } finally {
      if (mounted) {
        setState(() {
          _isSubmitting = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final propertyTitle = _text('property_title');
    final dealNumber = _text('deal_number');
    final partnerName = _text('partner_name');
    final title = _text('title');
    final message = _text('message');
    final reasonCode = _text('reason_code');
    final responsibleRole = _text('responsible_role');
    final status = _text('status');

    final isStaffOwned = responsibleRole.toLowerCase() == 'staff';

    final isOpen = status.toLowerCase() == 'open';

    return Scaffold(
      backgroundColor: const Color(0xFFF6F8F6),
      appBar: AppBar(
        title: const Text('Governance Case'),
        backgroundColor: const Color(0xFF14532D),
        foregroundColor: Colors.white,
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Card(
            elevation: 0,
            child: Padding(
              padding: const EdgeInsets.all(18),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    propertyTitle.isEmpty ? 'Property' : propertyTitle,
                    style: const TextStyle(
                      fontSize: 22,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  if (dealNumber.isNotEmpty) ...[
                    const SizedBox(height: 4),
                    Text(
                      dealNumber,
                      style: const TextStyle(color: Colors.black54),
                    ),
                  ],
                  if (partnerName.isNotEmpty) ...[
                    const SizedBox(height: 12),
                    Text(
                      'Partner: $partnerName',
                      style: const TextStyle(fontWeight: FontWeight.w600),
                    ),
                  ],
                ],
              ),
            ),
          ),

          Card(
            elevation: 0,
            color: const Color(0xFFEFF6FF),
            child: Padding(
              padding: const EdgeInsets.all(18),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Row(
                    children: [
                      Icon(
                        Icons.account_tree_outlined,
                        color: Color(0xFF1D4ED8),
                      ),
                      SizedBox(width: 8),
                      Text(
                        'Current State',
                        style: TextStyle(
                          fontSize: 17,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 14),

                  _GovernanceStateRow(
                    label: 'Responsibility',
                    value: isStaffOwned
                        ? 'Pata Hao'
                        : responsibleRole.isEmpty
                        ? 'Unknown'
                        : responsibleRole,
                  ),

                  const SizedBox(height: 10),

                  _GovernanceStateRow(
                    label: 'Case status',
                    value: isOpen
                        ? 'Open'
                        : status.isEmpty
                        ? 'Unknown'
                        : status,
                  ),

                  const SizedBox(height: 10),

                  _GovernanceStateRow(label: 'Deal state', value: 'Blocked'),

                  const SizedBox(height: 10),

                  _GovernanceStateRow(
                    label: 'Resolution allowed',
                    value: 'Backend verification required',
                  ),
                ],
              ),
            ),
          ),

          const SizedBox(height: 14),

          Card(
            elevation: 0,
            color: const Color(0xFFFFF7ED),
            child: Padding(
              padding: const EdgeInsets.all(18),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Row(
                    children: [
                      Icon(Icons.gpp_maybe_outlined, color: Color(0xFFC2410C)),
                      SizedBox(width: 8),
                      Text(
                        'Why this deal is blocked',
                        style: TextStyle(
                          fontSize: 17,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 14),
                  Text(
                    title.isEmpty ? 'Governance review required' : title,
                    style: const TextStyle(fontWeight: FontWeight.w700),
                  ),
                  const SizedBox(height: 8),
                  Text(message, style: const TextStyle(height: 1.5)),
                  if (reasonCode.isNotEmpty) ...[
                    const SizedBox(height: 12),
                    Text(
                      'Reason code: $reasonCode',
                      style: const TextStyle(
                        color: Colors.black54,
                        fontSize: 12,
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ),

          const SizedBox(height: 20),

          const Text(
            'Staff Decision',
            style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
          ),

          const SizedBox(height: 12),

          OutlinedButton.icon(
            onPressed: _isSubmitting
                ? null
                : () {
                    _submitDecision(
                      decision: 'keep_blocked',
                      title: 'Keep deal blocked?',
                      message:
                          'Record that Pata Hao reviewed the case '
                          'and the governance requirement remains '
                          'unsatisfied.',
                      actionLabel: 'Keep blocked',
                    );
                  },
            icon: const Icon(Icons.lock_outline),
            label: const Text('Keep Blocked'),
          ),

          const SizedBox(height: 10),

          FilledButton.tonalIcon(
            onPressed: _isSubmitting
                ? null
                : () {
                    _submitDecision(
                      decision: 'return_to_partner',
                      title: 'Return case to partner?',
                      message:
                          'Responsibility will move back to the '
                          'assigned partner and the partner will '
                          'receive a new Action Required notice.',
                      actionLabel: 'Return to partner',
                    );
                  },
            icon: const Icon(Icons.reply_outlined),
            label: const Text('Return to Partner'),
          ),

          const SizedBox(height: 10),

          FilledButton.icon(
            onPressed: _isSubmitting
                ? null
                : () {
                    _submitDecision(
                      decision: 'resolve',
                      title: 'Resolve governance case?',
                      message:
                          'Resolution will succeed only if the '
                          'backend confirms that the original '
                          'governance requirement is now genuinely '
                          'satisfied.',
                      actionLabel: 'Attempt resolution',
                    );
                  },
            icon: const Icon(Icons.verified_outlined),
            label: const Text('Resolve Case'),
          ),

          if (_isSubmitting) ...[
            const SizedBox(height: 20),
            const Center(child: CircularProgressIndicator()),
          ],
        ],
      ),
    );
  }
}

class _GovernanceStateRow extends StatelessWidget {
  const _GovernanceStateRow({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(
          width: 125,
          child: Text(
            label,
            style: const TextStyle(
              color: Colors.black54,
              fontWeight: FontWeight.w600,
            ),
          ),
        ),
        Expanded(
          child: Text(
            value,
            style: const TextStyle(fontWeight: FontWeight.w700),
          ),
        ),
      ],
    );
  }
}
