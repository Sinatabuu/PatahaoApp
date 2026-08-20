import 'package:flutter/material.dart';

import '../models/payment.dart';
import '../models/property.dart';
import '../models/viewing.dart';
import '../models/viewing_feedback.dart';
import '../services/payment_service.dart';
import '../services/property_service.dart';
import '../services/viewing_service.dart';
import 'payment_success_screen.dart';
import 'viewing_feedback_screen.dart';


class ViewingDetailsScreen extends StatefulWidget {
  const ViewingDetailsScreen({super.key, required this.viewingId});

  final int viewingId;

  @override
  State<ViewingDetailsScreen> createState() => _ViewingDetailsScreenState();
}

class _ViewingDetailsScreenState extends State<ViewingDetailsScreen> {
  final ViewingService _viewingService = ViewingService();
  final PaymentService _paymentService = PaymentService();
  final PropertyService _propertyService = PropertyService();
  late Future<Property> _propertyFuture;

  late Future<Viewing> _viewingFuture;
  late Future<ViewingFeedback?> _feedbackFuture;
  bool _isLoadingReceipt = false;
  bool _isRespondingToProposal = false;

  @override
  void initState() {
    super.initState();
    _loadViewing();
  }

  void _loadViewing() {
    _viewingFuture = _viewingService.getViewing(widget.viewingId);

    _propertyFuture = _viewingFuture.then(
      (viewing) => _propertyService.fetchProperty(viewing.property),
    );

    _feedbackFuture = _viewingFuture.then((viewing) {
      if (viewing.effectiveBookingStatus != 'completed') {
        return null;
      }

      return _viewingService.getViewingFeedback(viewing.id);
    });
  }

  Future<void> _refreshViewing() async {
    setState(_loadViewing);

    await Future.wait<dynamic>([
      _viewingFuture,
      _propertyFuture,
      _feedbackFuture,
    ]);
  }

  Future<void> _openFeedback(Viewing viewing) async {
    final feedback = await Navigator.of(context).push<ViewingFeedback>(
      MaterialPageRoute<ViewingFeedback>(
        builder: (_) => ViewingFeedbackScreen(viewing: viewing),
      ),
    );

    if (!mounted || feedback == null) {
      return;
    }

    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Thank you. Your viewing feedback was submitted.'),
        backgroundColor: Color(0xFF15803D),
      ),
    );

    await _refreshViewing();
  }

  Future<void> _openReceipt(Viewing viewing) async {
    setState(() {
      _isLoadingReceipt = true;
    });

    try {
      final Payment payment = await _paymentService.getViewingReceipt(
        viewingId: viewing.id,
      );

      if (!mounted) {
        return;
      }

      await Navigator.of(context).push(
        MaterialPageRoute<void>(
          builder: (_) =>
              PaymentSuccessScreen(viewing: viewing, payment: payment),
        ),
      );
    } catch (error) {
      if (!mounted) {
        return;
      }

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(error.toString().replaceFirst('Exception: ', '')),
        ),
      );
    } finally {
      if (mounted) {
        setState(() {
          _isLoadingReceipt = false;
        });
      }
    }
  }

  Future<void> _acceptReschedule(Viewing viewing) async {
    if (_isRespondingToProposal) {
      return;
    }

    setState(() {
      _isRespondingToProposal = true;
    });

    try {
      await _viewingService.acceptReschedule(viewing.id);

      if (!mounted) {
        return;
      }

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('The new viewing date and time have been confirmed.'),
          backgroundColor: Color(0xFF15803D),
        ),
      );

      setState(_loadViewing);
      await _viewingFuture;
    } catch (error) {
      if (!mounted) {
        return;
      }

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(error.toString().replaceFirst('Exception: ', '')),
          backgroundColor: const Color(0xFFB91C1C),
        ),
      );
    } finally {
      if (mounted) {
        setState(() {
          _isRespondingToProposal = false;
        });
      }
    }
  }

  Future<void> _declineReschedule(Viewing viewing) async {
    if (_isRespondingToProposal) {
      return;
    }

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) {
        return AlertDialog(
          title: const Text('Decline proposed schedule?'),
          content: const Text(
            'Declining this proposed date and time will cancel this viewing '
            'request. This action cannot be undone.',
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(dialogContext).pop(false),
              child: const Text('Keep Viewing'),
            ),
            FilledButton(
              style: FilledButton.styleFrom(
                backgroundColor: const Color(0xFFB91C1C),
                foregroundColor: Colors.white,
              ),
              onPressed: () => Navigator.of(dialogContext).pop(true),
              child: const Text('Decline and Cancel'),
            ),
          ],
        );
      },
    );

    if (confirmed != true || !mounted) {
      return;
    }

    setState(() {
      _isRespondingToProposal = true;
    });

    try {
      await _viewingService.declineReschedule(viewing.id);

      if (!mounted) {
        return;
      }

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text(
            'The proposed schedule was declined and the viewing was cancelled.',
          ),
        ),
      );

      setState(_loadViewing);
      await _viewingFuture;
    } catch (error) {
      if (!mounted) {
        return;
      }

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(error.toString().replaceFirst('Exception: ', '')),
          backgroundColor: const Color(0xFFB91C1C),
        ),
      );
    } finally {
      if (mounted) {
        setState(() {
          _isRespondingToProposal = false;
        });
      }
    }
  }

  String _formatDate(String? value) {
    if (value == null || value.trim().isEmpty) {
      return 'Not available';
    }

    final parsed = DateTime.tryParse(value);

    if (parsed == null) {
      return value;
    }

    const months = [
      'January',
      'February',
      'March',
      'April',
      'May',
      'June',
      'July',
      'August',
      'September',
      'October',
      'November',
      'December',
    ];

    return '${parsed.day} '
        '${months[parsed.month - 1]} '
        '${parsed.year}';
  }

  String _formatTime(String? value) {
    if (value == null || value.trim().isEmpty) {
      return 'Not available';
    }

    final parts = value.split(':');

    if (parts.length < 2) {
      return value;
    }

    final hour = int.tryParse(parts[0]);

    if (hour == null) {
      return value;
    }

    final minute = parts[1];
    final period = hour >= 12 ? 'PM' : 'AM';

    final displayHour = hour == 0
        ? 12
        : hour > 12
        ? hour - 12
        : hour;

    return '$displayHour:$minute $period';
  }

  Color _statusColor(String status) {
    switch (status.toLowerCase()) {
      case 'pending_payment':
      case 'payment_processing':
        return const Color(0xFFD97706);

      case 'paid_pending_partner':
      case 'paid_awaiting_partner':
      case 'paid':
        return const Color(0xFF2563EB);

      case 'confirmed':
        return const Color(0xFF15803D);

      case 'completed':
        return const Color(0xFF14532D);

      case 'reschedule_proposed':
      case 'partner_reschedule':
        return const Color(0xFF7C3AED);

      case 'declined':
      case 'cancelled':
      case 'expired':
        return const Color(0xFFB91C1C);

      default:
        return Colors.blueGrey;
    }
  }

  IconData _statusIcon(String status) {
    switch (status.toLowerCase()) {
      case 'pending_payment':
        return Icons.payments_outlined;

      case 'payment_processing':
        return Icons.sync_outlined;

      case 'paid_pending_partner':
      case 'paid_awaiting_partner':
      case 'paid':
        return Icons.hourglass_top_outlined;

      case 'confirmed':
        return Icons.event_available_outlined;

      case 'completed':
        return Icons.check_circle_outline;

      case 'reschedule_proposed':
      case 'partner_reschedule':
        return Icons.update_outlined;

      case 'declined':
      case 'cancelled':
      case 'expired':
        return Icons.cancel_outlined;

      default:
        return Icons.info_outline;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF6F8F6),
      appBar: AppBar(
        title: const Text('Viewing Details'),
        backgroundColor: const Color(0xFF14532D),
        foregroundColor: Colors.white,
      ),
      body: FutureBuilder<Viewing>(
        future: _viewingFuture,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }

          if (snapshot.hasError) {
            return RefreshIndicator(
              onRefresh: _refreshViewing,
              child: ListView(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: const EdgeInsets.all(24),
                children: [
                  const SizedBox(height: 120),
                  const Icon(
                    Icons.cloud_off_outlined,
                    size: 64,
                    color: Colors.black38,
                  ),
                  const SizedBox(height: 16),
                  const Text(
                    'Could not load this viewing',
                    textAlign: TextAlign.center,
                    style: TextStyle(fontSize: 21, fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 10),
                  Text(
                    snapshot.error.toString().replaceFirst('Exception: ', ''),
                    textAlign: TextAlign.center,
                    style: const TextStyle(color: Colors.black54),
                  ),
                  const SizedBox(height: 22),
                  Center(
                    child: FilledButton.icon(
                      onPressed: () {
                        setState(_loadViewing);
                      },
                      icon: const Icon(Icons.refresh),
                      label: const Text('Try Again'),
                    ),
                  ),
                ],
              ),
            );
          }

          final viewing = snapshot.data!;
          debugPrint(
            'FEEDBACK VISIBILITY: '
            'id=${viewing.id}, '
            'status=${viewing.status}, '
            'bookingStatus=${viewing.bookingStatus}, '
            'effectiveStatus=${viewing.effectiveBookingStatus}',
          );

          return RefreshIndicator(
            onRefresh: _refreshViewing,
            child: ListView(
              physics: const AlwaysScrollableScrollPhysics(),
              padding: const EdgeInsets.all(16),
              children: [
                FutureBuilder<Property>(
                  future: _propertyFuture,
                  builder: (context, propertySnapshot) {
                    if (propertySnapshot.connectionState ==
                        ConnectionState.waiting) {
                      return const _PropertyHeroLoadingCard();
                    }

                    if (propertySnapshot.hasError ||
                        !propertySnapshot.hasData) {
                      return _ViewingHeaderCard(
                        viewing: viewing,
                        statusColor: _statusColor(
                          viewing.effectiveBookingStatus,
                        ),
                        statusIcon: _statusIcon(viewing.effectiveBookingStatus),
                      );
                    }

                    return _PropertyHeroCard(
                      property: propertySnapshot.data!,
                      viewing: viewing,
                      statusColor: _statusColor(viewing.effectiveBookingStatus),
                    );
                  },
                ),
                const SizedBox(height: 16),
                _SectionCard(
                  title: 'Requested Schedule',
                  icon: Icons.calendar_month_outlined,
                  children: [
                    _DetailRow(
                      label: 'Date',
                      value: _formatDate(viewing.requestedDate),
                    ),
                    _DetailRow(
                      label: 'Time',
                      value: _formatTime(viewing.requestedTime),
                    ),
                  ],
                ),
                if (viewing.hasProposedSchedule) ...[
                  const SizedBox(height: 16),
                  _RescheduleProposalCard(
                    viewing: viewing,
                    formattedDate: _formatDate(viewing.proposedDate),
                    formattedTime: _formatTime(viewing.proposedTime),
                    isSubmitting: _isRespondingToProposal,
                    onAccept: viewing.canRespondToReschedule
                        ? () => _acceptReschedule(viewing)
                        : null,
                    onDecline: viewing.canRespondToReschedule
                        ? () => _declineReschedule(viewing)
                        : null,
                  ),
                ],
                if (viewing.hasConfirmedSchedule) ...[
                  const SizedBox(height: 16),
                  _SectionCard(
                    title: 'Confirmed Schedule',
                    icon: Icons.event_available_outlined,
                    accentColor: const Color(0xFF15803D),
                    children: [
                      _DetailRow(
                        label: 'Confirmed date',
                        value: _formatDate(viewing.confirmedDate),
                      ),
                      _DetailRow(
                        label: 'Confirmed time',
                        value: _formatTime(viewing.confirmedTime),
                      ),
                    ],
                  ),
                ],
                const SizedBox(height: 16),
                _SectionCard(
                  title: 'Assigned Partner',
                  icon: Icons.person_outline,
                  children: [
                    _DetailRow(
                      label: 'Partner',
                      value: viewing.assignedPartnerName.trim().isEmpty
                          ? 'Awaiting assignment'
                          : viewing.assignedPartnerName,
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                _SectionCard(
                  title: 'Payment',
                  icon: Icons.payments_outlined,
                  children: [
                    _DetailRow(
                      label: 'Viewing fee',
                      value: 'KES ${viewing.feeAmount.toStringAsFixed(0)}',
                    ),
                    _DetailRow(
                      label: 'Reference',
                      value: viewing.paymentReference.trim().isEmpty
                          ? 'Not available'
                          : viewing.paymentReference,
                      selectable: true,
                    ),
                    if (viewing.paymentReference.trim().isNotEmpty) ...[
                      const SizedBox(height: 14),
                      SizedBox(
                        width: double.infinity,
                        child: OutlinedButton.icon(
                          onPressed: _isLoadingReceipt
                              ? null
                              : () => _openReceipt(viewing),
                          icon: _isLoadingReceipt
                              ? const SizedBox(
                                  width: 18,
                                  height: 18,
                                  child: CircularProgressIndicator(
                                    strokeWidth: 2,
                                  ),
                                )
                              : const Icon(Icons.receipt_long_outlined),
                          label: Text(
                            _isLoadingReceipt
                                ? 'Loading receipt...'
                                : 'View Receipt',
                          ),
                        ),
                      ),
                    ],
                  ],
                ),

                if (viewing.effectiveBookingStatus == 'completed') ...[
                  const SizedBox(height: 16),
                  FutureBuilder<ViewingFeedback?>(
                    future: _feedbackFuture,
                    builder: (context, feedbackSnapshot) {
                      if (feedbackSnapshot.connectionState ==
                          ConnectionState.waiting) {
                        return const _FeedbackLoadingCard();
                      }

                      if (feedbackSnapshot.hasError) {
                        return _FeedbackErrorCard(
                          message: feedbackSnapshot.error
                              .toString()
                              .replaceFirst('Exception: ', ''),
                          onRetry: () {
                            setState(_loadViewing);
                          },
                        );
                      }

                      final feedback = feedbackSnapshot.data;

                      if (feedback != null) {
                        return _SubmittedFeedbackCard(feedback: feedback);
                      }

                      return _LeaveFeedbackCard(
                        propertyTitle: viewing.propertyTitle,
                        onPressed: () => _openFeedback(viewing),
                      );
                    },
                  ),
                ],
                if (viewing.customerMessage.trim().isNotEmpty) ...[
                  const SizedBox(height: 16),
                  _SectionCard(
                    title: 'Your Message',
                    icon: Icons.message_outlined,
                    children: [
                      Text(
                        viewing.customerMessage,
                        style: const TextStyle(
                          fontSize: 15,
                          height: 1.5,
                          color: Color(0xFF374151),
                        ),
                      ),
                    ],
                  ),
                ],
                const SizedBox(height: 20),
                Text(
                  'Viewing reference: #${viewing.id}',
                  textAlign: TextAlign.center,
                  style: const TextStyle(fontSize: 12, color: Colors.black45),
                ),
                const SizedBox(height: 24),
              ],
            ),
          );
        },
      ),
    );
  }
}

class _ViewingHeaderCard extends StatelessWidget {
  const _ViewingHeaderCard({
    required this.viewing,
    required this.statusColor,
    required this.statusIcon,
  });

  final Viewing viewing;
  final Color statusColor;
  final IconData statusIcon;

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 1.5,
      color: Colors.white,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              width: 56,
              height: 56,
              decoration: BoxDecoration(
                color: statusColor.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(16),
              ),
              child: Icon(statusIcon, color: statusColor, size: 30),
            ),
            const SizedBox(width: 15),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    viewing.propertyTitle,
                    style: const TextStyle(
                      fontSize: 22,
                      fontWeight: FontWeight.bold,
                      color: Color(0xFF111827),
                    ),
                  ),
                  const SizedBox(height: 8),
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 12,
                      vertical: 6,
                    ),
                    decoration: BoxDecoration(
                      color: statusColor.withValues(alpha: 0.10),
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: Text(
                      viewing.friendlyStatus,
                      style: TextStyle(
                        color: statusColor,
                        fontWeight: FontWeight.bold,
                        fontSize: 13,
                      ),
                    ),
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

class _SectionCard extends StatelessWidget {
  const _SectionCard({
    required this.title,
    required this.icon,
    required this.children,
    this.accentColor = const Color(0xFF14532D),
  });

  final String title;
  final IconData icon;
  final List<Widget> children;
  final Color accentColor;

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 1,
      color: Colors.white,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(icon, color: accentColor, size: 22),
                const SizedBox(width: 10),
                Text(
                  title,
                  style: const TextStyle(
                    fontSize: 17,
                    fontWeight: FontWeight.bold,
                    color: Color(0xFF111827),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
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
    this.selectable = false,
  });

  final String label;
  final String value;
  final bool selectable;

  @override
  Widget build(BuildContext context) {
    final valueStyle = const TextStyle(
      fontWeight: FontWeight.w600,
      color: Color(0xFF111827),
    );

    final Widget valueWidget = selectable
        ? SelectableText(value, textAlign: TextAlign.end, style: valueStyle)
        : Text(value, textAlign: TextAlign.end, style: valueStyle);

    return Padding(
      padding: const EdgeInsets.only(bottom: 13),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            child: Text(label, style: const TextStyle(color: Colors.black54)),
          ),
          const SizedBox(width: 12),
          Flexible(child: valueWidget),
        ],
      ),
    );
  }
}

class _RescheduleProposalCard extends StatelessWidget {
  const _RescheduleProposalCard({
    required this.viewing,
    required this.formattedDate,
    required this.formattedTime,
    required this.isSubmitting,
    required this.onAccept,
    required this.onDecline,
  });

  final Viewing viewing;
  final String formattedDate;
  final String formattedTime;
  final bool isSubmitting;
  final VoidCallback? onAccept;
  final VoidCallback? onDecline;

  @override
  Widget build(BuildContext context) {
    final message = viewing.partnerResponseMessage.trim();

    return Card(
      elevation: 1.5,
      color: const Color(0xFFFAF5FF),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(18),
        side: const BorderSide(color: Color(0xFFD8B4FE)),
      ),
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Row(
              children: [
                Icon(Icons.update_outlined, color: Color(0xFF7C3AED)),
                SizedBox(width: 10),
                Expanded(
                  child: Text(
                    'Partner Proposed a New Schedule',
                    style: TextStyle(
                      fontSize: 17,
                      fontWeight: FontWeight.bold,
                      color: Color(0xFF3B0764),
                    ),
                  ),
                ),
              ],
            ),
            if (message.isNotEmpty) ...[
              const SizedBox(height: 16),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(14),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Message from your partner',
                      style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.bold,
                        color: Color(0xFF7C3AED),
                      ),
                    ),
                    const SizedBox(height: 7),
                    Text(
                      message,
                      style: const TextStyle(
                        fontSize: 15,
                        height: 1.5,
                        color: Color(0xFF374151),
                      ),
                    ),
                  ],
                ),
              ),
            ],
            const SizedBox(height: 16),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: const Color(0xFFF3E8FF),
                borderRadius: BorderRadius.circular(14),
              ),
              child: Column(
                children: [
                  _ProposalScheduleRow(
                    icon: Icons.calendar_today_outlined,
                    label: 'New date',
                    value: formattedDate,
                  ),
                  const SizedBox(height: 12),
                  _ProposalScheduleRow(
                    icon: Icons.schedule_outlined,
                    label: 'New time',
                    value: formattedTime,
                  ),
                ],
              ),
            ),
            if (onAccept != null || onDecline != null) ...[
              const SizedBox(height: 18),
              SizedBox(
                width: double.infinity,
                child: FilledButton.icon(
                  onPressed: isSubmitting ? null : onAccept,
                  style: FilledButton.styleFrom(
                    backgroundColor: const Color(0xFF15803D),
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(vertical: 14),
                  ),
                  icon: isSubmitting
                      ? const SizedBox(
                          width: 18,
                          height: 18,
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                            color: Colors.white,
                          ),
                        )
                      : const Icon(Icons.check_circle_outline),
                  label: Text(
                    isSubmitting ? 'Saving response...' : 'Accept New Time',
                  ),
                ),
              ),
              const SizedBox(height: 10),
              SizedBox(
                width: double.infinity,
                child: OutlinedButton.icon(
                  onPressed: isSubmitting ? null : onDecline,
                  style: OutlinedButton.styleFrom(
                    foregroundColor: const Color(0xFFB91C1C),
                    side: const BorderSide(color: Color(0xFFB91C1C)),
                    padding: const EdgeInsets.symmetric(vertical: 14),
                  ),
                  icon: const Icon(Icons.close),
                  label: const Text('Decline Proposal'),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _ProposalScheduleRow extends StatelessWidget {
  const _ProposalScheduleRow({
    required this.icon,
    required this.label,
    required this.value,
  });

  final IconData icon;
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Icon(icon, size: 20, color: const Color(0xFF7C3AED)),
        const SizedBox(width: 10),
        Expanded(
          child: Text(label, style: const TextStyle(color: Color(0xFF6B21A8))),
        ),
        const SizedBox(width: 12),
        Flexible(
          child: Text(
            value,
            textAlign: TextAlign.end,
            style: const TextStyle(
              fontWeight: FontWeight.bold,
              color: Color(0xFF3B0764),
            ),
          ),
        ),
      ],
    );
  }
}

class _PropertyHeroCard extends StatelessWidget {
  const _PropertyHeroCard({
    required this.property,
    required this.viewing,
    required this.statusColor,
  });

  final Property property;
  final Viewing viewing;
  final Color statusColor;

  @override
  Widget build(BuildContext context) {
    final partner = property.partner;
    final coverPhoto = property.coverPhoto;

    return Card(
      elevation: 2,
      clipBehavior: Clip.antiAlias,
      color: Colors.white,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(22)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            height: 220,
            width: double.infinity,
            child: coverPhoto != null && coverPhoto.image.trim().isNotEmpty
                ? Image.network(
                    coverPhoto.image,
                    fit: BoxFit.cover,
                    errorBuilder: (context, error, stackTrace) {
                      return const _PropertyImagePlaceholder();
                    },
                  )
                : const _PropertyImagePlaceholder(),
          ),
          Padding(
            padding: const EdgeInsets.all(20),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(
                      child: Text(
                        property.title,
                        style: const TextStyle(
                          fontSize: 23,
                          fontWeight: FontWeight.bold,
                          color: Color(0xFF111827),
                        ),
                      ),
                    ),
                    if (property.isVerified)
                      Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 10,
                          vertical: 6,
                        ),
                        decoration: BoxDecoration(
                          color: const Color(0xFFE8F5EC),
                          borderRadius: BorderRadius.circular(20),
                        ),
                        child: const Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(
                              Icons.verified,
                              size: 16,
                              color: Color(0xFF15803D),
                            ),
                            SizedBox(width: 5),
                            Text(
                              'Verified',
                              style: TextStyle(
                                color: Color(0xFF15803D),
                                fontSize: 12,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                          ],
                        ),
                      ),
                  ],
                ),
                const SizedBox(height: 10),
                Row(
                  children: [
                    const Icon(
                      Icons.location_on_outlined,
                      size: 19,
                      color: Colors.black54,
                    ),
                    const SizedBox(width: 6),
                    Expanded(
                      child: Text(
                        property.locationLabel,
                        style: const TextStyle(
                          fontSize: 14,
                          color: Colors.black54,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 14),
                Text(
                  property.formattedPrice,
                  style: const TextStyle(
                    fontSize: 21,
                    fontWeight: FontWeight.bold,
                    color: Color(0xFF14532D),
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  _propertyDescription(property),
                  style: const TextStyle(
                    fontSize: 14,
                    color: Color(0xFF4B5563),
                    fontWeight: FontWeight.w500,
                  ),
                ),
                const SizedBox(height: 16),
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.symmetric(
                    horizontal: 12,
                    vertical: 10,
                  ),
                  decoration: BoxDecoration(
                    color: statusColor.withValues(alpha: 0.10),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Row(
                    children: [
                      Icon(
                        Icons.event_note_outlined,
                        color: statusColor,
                        size: 20,
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          viewing.friendlyStatus,
                          style: TextStyle(
                            color: statusColor,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
                if (partner != null) ...[
                  const SizedBox(height: 18),
                  const Divider(),
                  const SizedBox(height: 12),
                  const Text(
                    'Your Pata Hao Partner',
                    style: TextStyle(
                      fontSize: 13,
                      color: Colors.black54,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      _PartnerAvatar(
                        photoUrl: partner.profilePhoto,
                        name: partner.displayName,
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              partner.displayName,
                              style: const TextStyle(
                                fontSize: 17,
                                fontWeight: FontWeight.bold,
                                color: Color(0xFF111827),
                              ),
                            ),
                            const SizedBox(height: 4),
                            Row(
                              children: [
                                if (partner.isVerified)
                                  const Icon(
                                    Icons.verified,
                                    size: 16,
                                    color: Color(0xFF15803D),
                                  ),
                                if (partner.isVerified)
                                  const SizedBox(width: 5),
                                Text(
                                  partner.verificationLabel,
                                  style: TextStyle(
                                    fontSize: 13,
                                    color: partner.isVerified
                                        ? const Color(0xFF15803D)
                                        : Colors.black54,
                                    fontWeight: FontWeight.w600,
                                  ),
                                ),
                              ],
                            ),
                            if (partner.location.trim().isNotEmpty) ...[
                              const SizedBox(height: 4),
                              Text(
                                partner.location,
                                style: const TextStyle(
                                  fontSize: 12,
                                  color: Colors.black45,
                                ),
                              ),
                            ],
                          ],
                        ),
                      ),
                    ],
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }

  static String _propertyDescription(Property property) {
    final details = <String>[
      property.formattedPropertyType,
      if (property.bedrooms > 0)
        '${property.bedrooms} bedroom${property.bedrooms == 1 ? '' : 's'}',
      if (property.bathrooms > 0)
        '${property.bathrooms} bathroom${property.bathrooms == 1 ? '' : 's'}',
      property.formattedListingType,
    ];

    return details.where((value) => value.trim().isNotEmpty).join(' • ');
  }
}

class _PartnerAvatar extends StatelessWidget {
  const _PartnerAvatar({required this.photoUrl, required this.name});

  final String? photoUrl;
  final String name;

  @override
  Widget build(BuildContext context) {
    final hasPhoto = photoUrl != null && photoUrl!.trim().isNotEmpty;

    return CircleAvatar(
      radius: 27,
      backgroundColor: const Color(0xFFE8F5EC),
      backgroundImage: hasPhoto ? NetworkImage(photoUrl!) : null,
      child: hasPhoto
          ? null
          : Text(
              name.trim().isEmpty ? 'P' : name.trim()[0].toUpperCase(),
              style: const TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.bold,
                color: Color(0xFF14532D),
              ),
            ),
    );
  }
}

class _PropertyImagePlaceholder extends StatelessWidget {
  const _PropertyImagePlaceholder();

  @override
  Widget build(BuildContext context) {
    return Container(
      color: const Color(0xFFE8F5EC),
      child: const Center(
        child: Icon(
          Icons.home_work_outlined,
          size: 72,
          color: Color(0xFF14532D),
        ),
      ),
    );
  }
}

class _LeaveFeedbackCard extends StatelessWidget {
  const _LeaveFeedbackCard({
    required this.propertyTitle,
    required this.onPressed,
  });

  final String propertyTitle;
  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 1.5,
      color: const Color(0xFFFFFBEB),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(18),
        side: const BorderSide(color: Color(0xFFFCD34D)),
      ),
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Row(
              children: [
                Icon(Icons.star_rounded, color: Color(0xFFD97706), size: 28),
                SizedBox(width: 10),
                Expanded(
                  child: Text(
                    'How did your viewing go?',
                    style: TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.bold,
                      color: Color(0xFF78350F),
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 10),
            Text(
              'Share your experience at $propertyTitle. '
              'Your feedback helps improve property accuracy '
              'and partner service.',
              style: const TextStyle(color: Color(0xFF92400E), height: 1.45),
            ),
            const SizedBox(height: 16),
            SizedBox(
              width: double.infinity,
              child: FilledButton.icon(
                onPressed: onPressed,
                style: FilledButton.styleFrom(
                  backgroundColor: const Color(0xFFD97706),
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(vertical: 14),
                ),
                icon: const Icon(Icons.rate_review_outlined),
                label: const Text('Leave Feedback'),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _SubmittedFeedbackCard extends StatelessWidget {
  const _SubmittedFeedbackCard({required this.feedback});

  final ViewingFeedback feedback;

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 1.5,
      color: const Color(0xFFE8F5EC),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(18),
        side: const BorderSide(color: Color(0xFF86EFAC)),
      ),
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Row(
              children: [
                Icon(
                  Icons.check_circle_rounded,
                  color: Color(0xFF15803D),
                  size: 28,
                ),
                SizedBox(width: 10),
                Expanded(
                  child: Text(
                    'Feedback submitted',
                    style: TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.bold,
                      color: Color(0xFF14532D),
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 10),
            const Text(
              'Thank you. Your feedback helps make '
              'Pata Hao safer and more trustworthy.',
              style: TextStyle(color: Color(0xFF166534), height: 1.45),
            ),
            const SizedBox(height: 16),
            _FeedbackSummaryRow(
              label: 'Attended',
              value: feedback.attended ? 'Yes' : 'No',
            ),
            _FeedbackSummaryRow(
              label: 'Property accuracy',
              value: feedback.friendlyPropertyAccuracy,
            ),
            _FeedbackSummaryRow(
              label: 'Partner rating',
              value: '${feedback.partnerRating} / 5',
            ),
            _FeedbackSummaryRow(
              label: 'Property rating',
              value: '${feedback.propertyRating} / 5',
            ),
            if (feedback.comments.trim().isNotEmpty) ...[
              const SizedBox(height: 8),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Text(
                  feedback.comments.trim(),
                  style: const TextStyle(
                    color: Color(0xFF374151),
                    height: 1.45,
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _FeedbackSummaryRow extends StatelessWidget {
  const _FeedbackSummaryRow({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Row(
        children: [
          Expanded(
            child: Text(
              label,
              style: const TextStyle(color: Color(0xFF166534)),
            ),
          ),
          const SizedBox(width: 12),
          Text(
            value,
            style: const TextStyle(
              color: Color(0xFF14532D),
              fontWeight: FontWeight.bold,
            ),
          ),
        ],
      ),
    );
  }
}

class _FeedbackLoadingCard extends StatelessWidget {
  const _FeedbackLoadingCard();

  @override
  Widget build(BuildContext context) {
    return const Card(
      child: Padding(
        padding: EdgeInsets.all(20),
        child: Row(
          children: [
            SizedBox(
              width: 22,
              height: 22,
              child: CircularProgressIndicator(strokeWidth: 2),
            ),
            SizedBox(width: 14),
            Expanded(child: Text('Checking your viewing feedback...')),
          ],
        ),
      ),
    );
  }
}

class _FeedbackErrorCard extends StatelessWidget {
  const _FeedbackErrorCard({required this.message, required this.onRetry});

  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Card(
      color: const Color(0xFFFFF1F2),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(18),
        side: const BorderSide(color: Color(0xFFFDA4AF)),
      ),
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Unable to check feedback',
              style: TextStyle(
                fontSize: 17,
                fontWeight: FontWeight.bold,
                color: Color(0xFF9F1239),
              ),
            ),
            const SizedBox(height: 8),
            Text(message, style: const TextStyle(color: Color(0xFF9F1239))),
            const SizedBox(height: 14),
            OutlinedButton.icon(
              onPressed: onRetry,
              icon: const Icon(Icons.refresh),
              label: const Text('Try Again'),
            ),
          ],
        ),
      ),
    );
  }
}

class _PropertyHeroLoadingCard extends StatelessWidget {
  const _PropertyHeroLoadingCard();

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 1,
      clipBehavior: Clip.antiAlias,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(22)),
      child: const Column(
        children: [
          SizedBox(
            height: 220,
            child: Center(child: CircularProgressIndicator()),
          ),
          Padding(
            padding: EdgeInsets.all(20),
            child: Align(
              alignment: Alignment.centerLeft,
              child: Text(
                'Loading property details...',
                style: TextStyle(color: Colors.black54),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
