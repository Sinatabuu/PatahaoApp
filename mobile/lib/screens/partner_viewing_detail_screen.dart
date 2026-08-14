import 'package:flutter/material.dart';

import 'package:mobile/models/partner_dashboard.dart';
import 'package:mobile/services/partner_dashboard_service.dart';

class PartnerViewingDetailScreen extends StatefulWidget {
  const PartnerViewingDetailScreen({
    super.key,
    required this.viewing,
  });

  final PartnerDashboardViewing viewing;

  @override
  State<PartnerViewingDetailScreen> createState() =>
      _PartnerViewingDetailScreenState();
}

class _PartnerViewingDetailScreenState
    extends State<PartnerViewingDetailScreen> {
  late PartnerDashboardViewing _viewing;

  bool _isLoading = false;
  bool _hasChanged = false;

  @override
  void initState() {
    super.initState();
    _viewing = widget.viewing;
  }

  Future<void> _refresh() async {
    if (_isLoading) {
      return;
    }

    setState(() {
      _isLoading = true;
    });

    try {
      final refreshed = await PartnerDashboardService.instance.getViewing(
        _viewing.id,
      );

      if (!mounted) {
        return;
      }

      setState(() {
        _viewing = refreshed;
      });
    } catch (error) {
      if (!mounted) {
        return;
      }

      _showError(_cleanError(error));
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  Future<void> _runAction({
    required String confirmationTitle,
    required String confirmationMessage,
    required String successMessage,
    required Future<void> Function() action,
    bool dangerous = false,
  }) async {
    if (_isLoading) {
      return;
    }

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) {
        return AlertDialog(
          title: Text(confirmationTitle),
          content: Text(confirmationMessage),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(dialogContext, false),
              child: const Text('Cancel'),
            ),
            ElevatedButton(
              onPressed: () => Navigator.pop(dialogContext, true),
              style: dangerous
                  ? ElevatedButton.styleFrom(
                      backgroundColor: Colors.red.shade700,
                      foregroundColor: Colors.white,
                    )
                  : null,
              child: const Text('Continue'),
            ),
          ],
        );
      },
    );

    if (confirmed != true || !mounted) {
      return;
    }

    setState(() {
      _isLoading = true;
    });

    try {
      await action();

      final refreshed = await PartnerDashboardService.instance.getViewing(
        _viewing.id,
      );

      if (!mounted) {
        return;
      }

      setState(() {
        _viewing = refreshed;
        _hasChanged = true;
      });

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(successMessage),
        ),
      );
    } catch (error) {
      if (!mounted) {
        return;
      }

      _showError(_cleanError(error));
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  Future<void> _confirmViewing() async {
    await _runAction(
      confirmationTitle: 'Confirm viewing',
      confirmationMessage:
          'Confirm the viewing for ${_viewing.propertyTitle} on '
          '${_viewing.requestedDate} at ${_viewing.requestedTime}?',
      successMessage: 'Viewing confirmed successfully.',
      action: () {
        return PartnerDashboardService.instance.confirmViewing(
          _viewing.id,
        );
      },
    );
  }

  Future<void> _rescheduleViewing() async {
    if (_isLoading) {
      return;
    }

    final requestedDate =
        DateTime.tryParse(_viewing.requestedDate) ?? DateTime.now();

    final today = DateTime.now();
    final minimumDate = DateTime(today.year, today.month, today.day);

    final selectedDate = await showDatePicker(
      context: context,
      initialDate: requestedDate.isBefore(minimumDate)
          ? minimumDate
          : requestedDate,
      firstDate: minimumDate,
      lastDate: minimumDate.add(const Duration(days: 180)),
      helpText: 'Select a new viewing date',
    );

    if (selectedDate == null || !mounted) {
      return;
    }

    final selectedTime = await showTimePicker(
      context: context,
      initialTime: _parseTime(_viewing.requestedTime),
      helpText: 'Select a new viewing time',
    );

    if (selectedTime == null || !mounted) {
      return;
    }

    final reason = await _requestText(
      title: 'Reason for rescheduling',
      label: 'Reason',
      hint: 'Explain why another date or time is being proposed.',
      confirmLabel: 'Send proposal',
      required: true,
    );

    if (reason == null || !mounted) {
      return;
    }

    setState(() {
      _isLoading = true;
    });

    try {
      await PartnerDashboardService.instance.rescheduleViewing(
        viewingId: _viewing.id,
        proposedDate: _formatDate(selectedDate),
        proposedTime: _formatTime(selectedTime),
        reason: reason,
      );

      final refreshed = await PartnerDashboardService.instance.getViewing(
        _viewing.id,
      );

      if (!mounted) {
        return;
      }

      setState(() {
        _viewing = refreshed;
        _hasChanged = true;
      });

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('The new schedule was sent to the customer.'),
        ),
      );
    } catch (error) {
      if (!mounted) {
        return;
      }

      _showError(_cleanError(error));
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  Future<void> _declineViewing() async {
    final reason = await _requestText(
      title: 'Decline viewing',
      label: 'Reason',
      hint: 'Explain why this viewing cannot proceed.',
      confirmLabel: 'Decline viewing',
      required: true,
      dangerous: true,
    );

    if (reason == null || !mounted) {
      return;
    }

    await _runAction(
      confirmationTitle: 'Decline this viewing?',
      confirmationMessage:
          'The customer will be informed that the viewing cannot proceed.',
      successMessage: 'Viewing declined.',
      dangerous: true,
      action: () {
        return PartnerDashboardService.instance.declineViewing(
          viewingId: _viewing.id,
          reason: reason,
        );
      },
    );
  }

  Future<void> _markEnRoute() async {
    await _runAction(
      confirmationTitle: 'Start journey',
      confirmationMessage:
          'Confirm that you are now travelling to the property.',
      successMessage: 'Customer can now see that you are en route.',
      action: () {
        return PartnerDashboardService.instance.markEnRoute(
          viewingId: _viewing.id,
        );
      },
    );
  }

  Future<void> _markArrived() async {
    await _runAction(
      confirmationTitle: 'Confirm arrival',
      confirmationMessage:
          'Confirm that you have arrived at the viewing location.',
      successMessage: 'Arrival recorded successfully.',
      action: () {
        return PartnerDashboardService.instance.markArrived(
          viewingId: _viewing.id,
        );
      },
    );
  }

  Future<void> _startViewing() async {
    await _runAction(
      confirmationTitle: 'Start viewing',
      confirmationMessage:
          'Confirm that the customer is present and the property viewing '
          'is beginning.',
      successMessage: 'Viewing started.',
      action: () {
        return PartnerDashboardService.instance.startViewing(
          viewingId: _viewing.id,
        );
      },
    );
  }

  Future<void> _completeViewing() async {
    final notes = await _requestText(
      title: 'Complete viewing',
      label: 'Completion notes',
      hint: 'Example: Customer attended and viewed the property.',
      confirmLabel: 'Complete viewing',
      required: false,
    );

    if (notes == null || !mounted) {
      return;
    }

    await _runAction(
      confirmationTitle: 'Complete this viewing?',
      confirmationMessage:
          'This confirms that the physical property viewing has finished.',
      successMessage: 'Viewing completed successfully.',
      action: () {
        return PartnerDashboardService.instance.completeViewing(
          viewingId: _viewing.id,
          completionNotes: notes,
        );
      },
    );
  }

  Future<String?> _requestText({
    required String title,
    required String label,
    required String hint,
    required String confirmLabel,
    required bool required,
    bool dangerous = false,
  }) async {
    String enteredValue = '';
    String? validationMessage;

    final result = await showDialog<String>(
      context: context,
      barrierDismissible: false,
      builder: (dialogContext) {
        return StatefulBuilder(
          builder: (context, setDialogState) {
            return AlertDialog(
              title: Text(title),
              content: TextField(
                autofocus: true,
                minLines: 3,
                maxLines: 6,
                maxLength: 2000,
                onChanged: (value) {
                  enteredValue = value;

                  if (validationMessage != null && value.trim().isNotEmpty) {
                    setDialogState(() {
                      validationMessage = null;
                    });
                  }
                },
                decoration: InputDecoration(
                  labelText: label,
                  hintText: hint,
                  errorText: validationMessage,
                  border: const OutlineInputBorder(),
                ),
              ),
              actions: [
                TextButton(
                  onPressed: () {
                    Navigator.of(dialogContext).pop();
                  },
                  child: const Text('Cancel'),
                ),
                ElevatedButton(
                  onPressed: () {
                    final value = enteredValue.trim();

                    if (required && value.isEmpty) {
                      setDialogState(() {
                        validationMessage = 'This information is required.';
                      });
                      return;
                    }

                    Navigator.of(dialogContext).pop(value);
                  },
                  style: dangerous
                      ? ElevatedButton.styleFrom(
                          backgroundColor: Colors.red.shade700,
                          foregroundColor: Colors.white,
                        )
                      : null,
                  child: Text(confirmLabel),
                ),
              ],
            );
          },
        );
      },
    );

    return result;
  }
  @override
  Widget build(BuildContext context) {
    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (didPop, result) {
        if (!didPop) {
          Navigator.pop(context, _hasChanged);
        }
      },
      child: Scaffold(
        backgroundColor: const Color(0xFFF6F8F6),
        appBar: AppBar(
          backgroundColor: Colors.white,
          title: Text('Viewing #${_viewing.id}'),
          leading: IconButton(
            tooltip: 'Back',
            onPressed: () => Navigator.pop(context, _hasChanged),
            icon: const Icon(Icons.arrow_back),
          ),
          actions: [
            IconButton(
              tooltip: 'Refresh viewing',
              onPressed: _isLoading ? null : _refresh,
              icon: const Icon(Icons.refresh),
            ),
          ],
        ),
        body: Stack(
          children: [
            RefreshIndicator(
              onRefresh: _refresh,
              child: ListView(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: const EdgeInsets.all(16),
                children: [
                  _StatusHeader(viewing: _viewing),
                  const SizedBox(height: 16),
                  _CustomerCard(viewing: _viewing),
                  const SizedBox(height: 16),
                  _ScheduleCard(viewing: _viewing),
                  const SizedBox(height: 16),
                  _PaymentCard(viewing: _viewing),
                  if (_viewing.customerMessage.isNotEmpty) ...[
                    const SizedBox(height: 16),
                    _MessageCard(
                      title: 'Customer message',
                      message: _viewing.customerMessage,
                      icon: Icons.chat_bubble_outline,
                    ),
                  ],
                  if (_viewing.partnerResponseMessage.isNotEmpty) ...[
                    const SizedBox(height: 16),
                    _MessageCard(
                      title: 'Partner response',
                      message: _viewing.partnerResponseMessage,
                      icon: Icons.assignment_turned_in_outlined,
                    ),
                  ],
                  const SizedBox(height: 16),
                  _ProgressCard(viewing: _viewing),
                  const SizedBox(height: 16),
                  _ActionCard(
                    viewing: _viewing,
                    isLoading: _isLoading,
                    onConfirm: _confirmViewing,
                    onReschedule: _rescheduleViewing,
                    onDecline: _declineViewing,
                    onEnRoute: _markEnRoute,
                    onArrived: _markArrived,
                    onStart: _startViewing,
                    onComplete: _completeViewing,
                  ),
                  const SizedBox(height: 30),
                ],
              ),
            ),
            if (_isLoading)
              Positioned.fill(
                child: ColoredBox(
                  color: Colors.black12,
                  child: const Center(
                    child: CircularProgressIndicator(),
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }

  void _showError(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: Colors.red.shade700,
      ),
    );
  }

  TimeOfDay _parseTime(String value) {
    final parts = value.split(':');

    if (parts.length >= 2) {
      final hour = int.tryParse(parts[0]);
      final minute = int.tryParse(parts[1]);

      if (hour != null &&
          minute != null &&
          hour >= 0 &&
          hour <= 23 &&
          minute >= 0 &&
          minute <= 59) {
        return TimeOfDay(
          hour: hour,
          minute: minute,
        );
      }
    }

    return TimeOfDay.now();
  }

  String _formatDate(DateTime value) {
    final month = value.month.toString().padLeft(2, '0');
    final day = value.day.toString().padLeft(2, '0');

    return '${value.year}-$month-$day';
  }

  String _formatTime(TimeOfDay value) {
    final hour = value.hour.toString().padLeft(2, '0');
    final minute = value.minute.toString().padLeft(2, '0');

    return '$hour:$minute:00';
  }

  String _cleanError(Object error) {
    return error.toString().replaceFirst('Exception: ', '').trim();
  }
}

class _StatusHeader extends StatelessWidget {
  const _StatusHeader({
    required this.viewing,
  });

  final PartnerDashboardViewing viewing;

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 0,
      color: Colors.white,
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Row(
          children: [
            Container(
              width: 52,
              height: 52,
              decoration: BoxDecoration(
                color: const Color(0xFFE4F3E2),
                borderRadius: BorderRadius.circular(14),
              ),
              child: const Icon(
                Icons.home_work_outlined,
                color: Color(0xFF2E8B28),
                size: 29,
              ),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    viewing.propertyTitle,
                    style: const TextStyle(
                      fontSize: 19,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: 7),
                  Wrap(
                    spacing: 8,
                    runSpacing: 6,
                    children: [
                      _StatusChip(
                        text: viewing.status,
                        color: _bookingStatusColor(viewing.status),
                      ),
                      _StatusChip(
                        text: viewing.operationalStatus,
                        color: _operationalStatusColor(
                          viewing.operationalStatus,
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
    );
  }
}

class _CustomerCard extends StatelessWidget {
  const _CustomerCard({
    required this.viewing,
  });

  final PartnerDashboardViewing viewing;

  @override
  Widget build(BuildContext context) {
    final customerName = viewing.customerName.trim().isNotEmpty
        ? viewing.customerName
        : viewing.customerEmail;

    return _SectionCard(
      title: 'Customer',
      icon: Icons.person_outline,
      children: [
        _DetailRow(
          label: 'Name',
          value: customerName.isEmpty ? 'Customer' : customerName,
        ),
        if (viewing.customerEmail.isNotEmpty)
          _DetailRow(
            label: 'Email',
            value: viewing.customerEmail,
          ),
      ],
    );
  }
}

class _ScheduleCard extends StatelessWidget {
  const _ScheduleCard({
    required this.viewing,
  });

  final PartnerDashboardViewing viewing;

  @override
  Widget build(BuildContext context) {
    return _SectionCard(
      title: 'Viewing schedule',
      icon: Icons.calendar_month_outlined,
      children: [
        _DetailRow(
          label: 'Requested date',
          value: viewing.requestedDate,
        ),
        _DetailRow(
          label: 'Requested time',
          value: viewing.requestedTime,
        ),
        if (viewing.proposedDate != null)
          _DetailRow(
            label: 'Proposed date',
            value: viewing.proposedDate!,
          ),
        if (viewing.proposedTime != null)
          _DetailRow(
            label: 'Proposed time',
            value: viewing.proposedTime!,
          ),
        if (viewing.confirmedDate != null)
          _DetailRow(
            label: 'Confirmed date',
            value: viewing.confirmedDate!,
          ),
        if (viewing.confirmedTime != null)
          _DetailRow(
            label: 'Confirmed time',
            value: viewing.confirmedTime!,
          ),
      ],
    );
  }
}

class _PaymentCard extends StatelessWidget {
  const _PaymentCard({
    required this.viewing,
  });

  final PartnerDashboardViewing viewing;

  @override
  Widget build(BuildContext context) {
    return _SectionCard(
      title: 'Payment',
      icon: Icons.payments_outlined,
      children: [
        _DetailRow(
          label: 'Viewing fee',
          value: 'KES ${viewing.feeAmount}',
        ),
        _DetailRow(
          label: 'Payment status',
          value: viewing.paymentReference.isEmpty
              ? 'Payment reference unavailable'
              : 'Paid',
        ),
        if (viewing.paymentReference.isNotEmpty)
          _DetailRow(
            label: 'Reference',
            value: viewing.paymentReference,
          ),
      ],
    );
  }
}

class _MessageCard extends StatelessWidget {
  const _MessageCard({
    required this.title,
    required this.message,
    required this.icon,
  });

  final String title;
  final String message;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return _SectionCard(
      title: title,
      icon: icon,
      children: [
        Text(
          message,
          style: const TextStyle(
            height: 1.45,
          ),
        ),
      ],
    );
  }
}

class _ProgressCard extends StatelessWidget {
  const _ProgressCard({
    required this.viewing,
  });

  final PartnerDashboardViewing viewing;

  @override
  Widget build(BuildContext context) {
    final confirmed =
        viewing.effectiveBookingStatus == 'confirmed' ||
        viewing.effectiveBookingStatus == 'completed';

    final completed =
        viewing.effectiveBookingStatus == 'completed' ||
        viewing.status == 'completed';

    return _SectionCard(
      title: 'Viewing progress',
      icon: Icons.route_outlined,
      children: [
        _SimpleProgressItem(
          label: 'Viewing confirmed',
          isComplete: confirmed,
          isCurrent: !confirmed,
        ),
        _SimpleProgressItem(
          label: 'Viewing completed',
          isComplete: completed,
          isCurrent: confirmed && !completed,
          isLast: true,
        ),
      ],
    );
  }
}

class _SimpleProgressItem extends StatelessWidget {
  const _SimpleProgressItem({
    required this.label,
    required this.isComplete,
    required this.isCurrent,
    this.isLast = false,
  });

  final String label;
  final bool isComplete;
  final bool isCurrent;
  final bool isLast;

  @override
  Widget build(BuildContext context) {
    final color = isComplete
        ? const Color(0xFF2E8B28)
        : isCurrent
            ? Colors.orange.shade800
            : Colors.black26;

    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(
          width: 34,
          child: Column(
            children: [
              Icon(
                isComplete
                    ? Icons.check_circle
                    : isCurrent
                        ? Icons.radio_button_checked
                        : Icons.radio_button_unchecked,
                color: color,
                size: 22,
              ),
              if (!isLast)
                Container(
                  width: 2,
                  height: 30,
                  color: isComplete ? const Color(0xFF2E8B28) : Colors.black12,
                ),
            ],
          ),
        ),
        Expanded(
          child: Padding(
            padding: const EdgeInsets.only(top: 2),
            child: Text(
              label,
              style: TextStyle(
                fontWeight:
                    isComplete || isCurrent ? FontWeight.w700 : FontWeight.normal,
                color:
                    isComplete || isCurrent ? Colors.black87 : Colors.black45,
              ),
            ),
          ),
        ),
      ],
    );
  }
}

class _ActionCard extends StatelessWidget {
  const _ActionCard({
    required this.viewing,
    required this.isLoading,
    required this.onConfirm,
    required this.onReschedule,
    required this.onDecline,
    required this.onEnRoute,
    required this.onArrived,
    required this.onStart,
    required this.onComplete,
  });

  final PartnerDashboardViewing viewing;
  final bool isLoading;

  final VoidCallback onConfirm;
  final VoidCallback onReschedule;
  final VoidCallback onDecline;
  final VoidCallback onEnRoute;
  final VoidCallback onArrived;
  final VoidCallback onStart;
  final VoidCallback onComplete;

  @override
  Widget build(BuildContext context) {
    final status = viewing.effectiveBookingStatus;

    final awaitingPartner = status == 'paid_pending_partner' ||
        status == 'paid_awaiting_partner' ||
        status == 'reschedule_proposed';

    final confirmed = status == 'confirmed';
    final completed = status == 'completed';
    final cancelled = status == 'cancelled' || status == 'declined';

    return _SectionCard(
      title: 'Available actions',
      icon: Icons.touch_app_outlined,
      children: [
        if (completed)
          const _FinishedMessage(
            icon: Icons.task_alt,
            message: 'This viewing has been completed.',
            color: Color(0xFF2E8B28),
          )
        else if (cancelled)
          const _FinishedMessage(
            icon: Icons.cancel_outlined,
            message: 'This viewing is no longer active.',
            color: Colors.red,
          )
        else if (awaitingPartner) ...[
          _PrimaryActionButton(
            label: 'Confirm Viewing',
            icon: Icons.check_circle_outline,
            onPressed: isLoading ? null : onConfirm,
          ),
          const SizedBox(height: 10),
          Row(
            children: [
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: isLoading ? null : onReschedule,
                  icon: const Icon(Icons.schedule),
                  label: const Text('New Time'),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: isLoading ? null : onDecline,
                  icon: const Icon(Icons.close),
                  label: const Text('Decline'),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: Colors.red,
                  ),
                ),
              ),
            ],
          ),
        ] else if (confirmed) ...[
          const Text(
            'After showing the property to the customer, tap the button below.',
            style: TextStyle(
              color: Colors.black54,
              height: 1.4,
            ),
          ),
          const SizedBox(height: 14),
          _PrimaryActionButton(
            label: 'Complete Viewing',
            icon: Icons.task_alt,
            onPressed: isLoading ? null : onComplete,
          ),
        ] else
          const _FinishedMessage(
            icon: Icons.info_outline,
            message: 'No action is currently available for this viewing.',
            color: Colors.blueGrey,
          ),
      ],
    );
  }
}

class _SectionCard extends StatelessWidget {
  const _SectionCard({
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
      elevation: 0,
      color: Colors.white,
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  icon,
                  color: const Color(0xFF2E8B28),
                ),
                const SizedBox(width: 9),
                Text(
                  title,
                  style: const TextStyle(
                    fontSize: 17,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
            const Divider(height: 26),
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
      padding: const EdgeInsets.only(bottom: 11),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 126,
            child: Text(
              label,
              style: const TextStyle(
                color: Colors.black54,
              ),
            ),
          ),
          Expanded(
            child: Text(
              value.isEmpty ? 'Not provided' : value,
              style: const TextStyle(
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _StatusChip extends StatelessWidget {
  const _StatusChip({
    required this.text,
    required this.color,
  });

  final String text;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: 10,
        vertical: 6,
      ),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Text(
        _humanize(text),
        style: TextStyle(
          color: color,
          fontSize: 12,
          fontWeight: FontWeight.bold,
        ),
      ),
    );
  }
}

class _PrimaryActionButton extends StatelessWidget {
  const _PrimaryActionButton({
    required this.label,
    required this.icon,
    required this.onPressed,
  });

  final String label;
  final IconData icon;
  final VoidCallback? onPressed;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: double.infinity,
      child: ElevatedButton.icon(
        onPressed: onPressed,
        icon: Icon(icon),
        label: Text(label),
        style: ElevatedButton.styleFrom(
          backgroundColor: const Color(0xFF2E8B28),
          foregroundColor: Colors.white,
          padding: const EdgeInsets.symmetric(
            vertical: 14,
          ),
        ),
      ),
    );
  }
}

class _FinishedMessage extends StatelessWidget {
  const _FinishedMessage({
    required this.icon,
    required this.message,
    required this.color,
  });

  final IconData icon;
  final String message;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Icon(icon, color: color),
        const SizedBox(width: 10),
        Expanded(
          child: Text(
            message,
            style: TextStyle(
              color: color,
              fontWeight: FontWeight.w600,
            ),
          ),
        ),
      ],
    );
  }
}


Color _bookingStatusColor(String status) {
  switch (status) {
    case 'completed':
      return Colors.green.shade800;

    case 'confirmed':
      return Colors.blue.shade800;

    case 'paid_pending_partner':
    case 'paid_awaiting_partner':
      return Colors.orange.shade800;

    case 'reschedule_proposed':
      return Colors.deepPurple.shade700;

    case 'cancelled':
    case 'declined':
      return Colors.red.shade700;

    default:
      return Colors.blueGrey.shade700;
  }
}

Color _operationalStatusColor(String status) {
  switch (status) {
    case 'viewing_in_progress':
    case 'viewing_started':
      return Colors.deepPurple.shade700;

    case 'partner_arrived':
      return Colors.green.shade700;

    case 'partner_en_route':
      return Colors.orange.shade800;

    case 'idle':
      return Colors.blueGrey.shade700;

    default:
      return Colors.blueGrey.shade700;
  }
}

String _humanize(String value) {
  final cleaned = value.trim().replaceAll('_', ' ');

  if (cleaned.isEmpty) {
    return 'Status unavailable';
  }

  return cleaned
      .split(' ')
      .map((word) {
        if (word.isEmpty) {
          return '';
        }

        return '${word[0].toUpperCase()}${word.substring(1)}';
      })
      .join(' ');
}