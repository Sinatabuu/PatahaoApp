import 'package:flutter/material.dart';

import '../models/deal.dart';
import '../models/payment.dart';
import '../models/viewing.dart';
import '../services/deal_service.dart';
import '../services/payment_service.dart';
import '../services/viewing_service.dart';
import 'customer_deal_confirmation_screen.dart';
import 'payment_success_screen.dart';
import 'viewing_details_screen.dart';

class MyViewingsScreen extends StatefulWidget {
  const MyViewingsScreen({super.key});

  @override
  State<MyViewingsScreen> createState() => _MyViewingsScreenState();
}

class _MyViewingsScreenState extends State<MyViewingsScreen> {
  final ViewingService _viewingService = ViewingService();
  final PaymentService _paymentService = PaymentService();

  late Future<_MyViewingsData> _future;

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  void _loadData() {
    _future = _fetchData();
  }

  Future<_MyViewingsData> _fetchData() async {
    final results = await Future.wait<dynamic>([
      _viewingService.getMyViewings(),
      DealService.instance.fetchDeals(),
      _paymentService.fetchPayments(),
    ]);

    return _MyViewingsData(
      viewings: results[0] as List<Viewing>,
      deals: results[1] as List<Deal>,
      payments: results[2] as List<Payment>,
    );
  }

  Future<void> _refresh() async {
    setState(_loadData);
    await _future;
  }

  Deal? _dealForViewing(Viewing viewing, List<Deal> deals) {
    for (final deal in deals) {
      if (deal.viewingId == viewing.id) {
        return deal;
      }
    }
    return null;
  }

  Payment? _paymentForViewing(Viewing viewing, List<Payment> payments) {
    final viewingReference = viewing.paymentReference.trim();

    if (viewingReference.isEmpty) {
      return null;
    }

    for (final payment in payments) {
      if (payment.paymentReference.trim() == viewingReference) {
        return payment;
      }
    }
    return null;
  }

  Future<void> _openConfirmation(Deal deal) async {
    final updatedDeal = await Navigator.of(context).push<Deal>(
      MaterialPageRoute<Deal>(
        builder: (_) => CustomerDealConfirmationScreen(deal: deal),
      ),
    );

    if (!mounted || updatedDeal == null) {
      return;
    }

    await _refresh();
  }

  String _formatStatus(String status) {
    switch (status.trim().toLowerCase()) {
      case 'pending_payment':
      case 'payment_pending':
        return 'Pending payment';
      case 'payment_processing':
        return 'Payment in progress';
      case 'paid_pending_partner':
      case 'paid_awaiting_partner':
      case 'paid':
        return 'Paid - awaiting partner';
      case 'reschedule_proposed':
      case 'partner_reschedule':
        return 'New time proposed';
      case 'confirmed':
        return 'Confirmed';
      case 'partner_en_route':
        return 'Partner en route';
      case 'partner_arrived':
        return 'Partner arrived';
      case 'viewing_in_progress':
      case 'viewing_started':
        return 'Viewing in progress';
      case 'completed':
        return 'Completed';
      case 'cancelled':
        return 'Cancelled';
      case 'declined':
        return 'Declined';
      case 'expired':
        return 'Expired';
      case 'payment_failed':
        return 'Payment failed';
      case 'refunded':
        return 'Refunded';
      case 'disputed':
        return 'Under review';
      default:
        return status
            .replaceAll('_', ' ')
            .split(' ')
            .map(
              (word) => word.isEmpty
                  ? ''
                  : '${word[0].toUpperCase()}${word.substring(1)}',
            )
            .join(' ');
    }
  }

  Color _statusColor(String status) {
    switch (status.trim().toLowerCase()) {
      case 'pending_payment':
      case 'payment_pending':
      case 'payment_processing':
        return const Color(0xFFD97706);
      case 'paid_pending_partner':
      case 'paid_awaiting_partner':
      case 'paid':
        return const Color(0xFF2563EB);
      case 'reschedule_proposed':
      case 'partner_reschedule':
        return const Color(0xFF7C3AED);
      case 'confirmed':
      case 'partner_en_route':
      case 'partner_arrived':
      case 'viewing_in_progress':
      case 'viewing_started':
        return const Color(0xFF15803D);
      case 'completed':
        return const Color(0xFF14532D);
      case 'cancelled':
      case 'declined':
      case 'expired':
      case 'payment_failed':
        return const Color(0xFFB91C1C);
      case 'refunded':
        return const Color(0xFF0369A1);
      case 'disputed':
        return const Color(0xFFB45309);
      default:
        return Colors.blueGrey;
    }
  }

  IconData _statusIcon(String status) {
    switch (status.trim().toLowerCase()) {
      case 'pending_payment':
      case 'payment_pending':
        return Icons.payments_outlined;
      case 'payment_processing':
        return Icons.hourglass_top_outlined;
      case 'paid_pending_partner':
      case 'paid_awaiting_partner':
      case 'paid':
        return Icons.verified_outlined;
      case 'reschedule_proposed':
      case 'partner_reschedule':
        return Icons.update_outlined;
      case 'confirmed':
        return Icons.event_available_outlined;
      case 'partner_en_route':
        return Icons.directions_car_outlined;
      case 'partner_arrived':
        return Icons.location_on_outlined;
      case 'viewing_in_progress':
      case 'viewing_started':
        return Icons.meeting_room_outlined;
      case 'completed':
        return Icons.check_circle_outline;
      case 'cancelled':
      case 'declined':
      case 'expired':
        return Icons.cancel_outlined;
      case 'payment_failed':
        return Icons.error_outline;
      case 'refunded':
        return Icons.currency_exchange_outlined;
      case 'disputed':
        return Icons.report_problem_outlined;
      default:
        return Icons.info_outline;
    }
  }

  String _formatDate(String value) {
    final parsed = DateTime.tryParse(value);

    if (parsed == null) {
      return value;
    }

    const months = <String>[
      'Jan',
      'Feb',
      'Mar',
      'Apr',
      'May',
      'Jun',
      'Jul',
      'Aug',
      'Sep',
      'Oct',
      'Nov',
      'Dec',
    ];

    return '${parsed.day} ${months[parsed.month - 1]} ${parsed.year}';
  }

  String _formatTime(String value) {
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

  bool _needsCustomerAction(Viewing viewing, Deal? deal) {
    final status = viewing.status.trim().toLowerCase();

    if (status == 'pending_payment' ||
        status == 'payment_pending' ||
        status == 'payment_processing' ||
        status == 'reschedule_proposed' ||
        status == 'partner_reschedule' ||
        status == 'payment_failed') {
      return true;
    }

    if (status == 'completed' &&
        deal != null &&
        !deal.customerOutcomeSubmitted) {
      return true;
    }

    return false;
  }

  bool _isPastViewing(Viewing viewing, Deal? deal) {
    if (_needsCustomerAction(viewing, deal)) {
      return false;
    }

    final status = viewing.status.trim().toLowerCase();

    return status == 'completed' ||
        status == 'cancelled' ||
        status == 'declined' ||
        status == 'expired' ||
        status == 'refunded';
  }

  Widget _buildViewingSection({
    required String title,
    required List<Viewing> viewings,
    required List<Deal> deals,
    required List<Payment> payments,
  }) {
    if (viewings.isEmpty) {
      return const SizedBox.shrink();
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(4, 6, 4, 12),
          child: Row(
            children: [
              Expanded(
                child: Text(
                  title,
                  style: const TextStyle(
                    fontSize: 19,
                    fontWeight: FontWeight.bold,
                    color: Color(0xFF111827),
                  ),
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 10,
                  vertical: 5,
                ),
                decoration: BoxDecoration(
                  color: const Color(0xFFE8F5E9),
                  borderRadius: BorderRadius.circular(20),
                ),
                child: Text(
                  '${viewings.length}',
                  style: const TextStyle(
                    color: Color(0xFF14532D),
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
            ],
          ),
        ),
        ...viewings.map((viewing) {
          final deal = _dealForViewing(viewing, deals);
          final payment = _paymentForViewing(viewing, payments);

          return Padding(
            padding: const EdgeInsets.only(bottom: 14),
            child: _ViewingCard(
              viewing: viewing,
              deal: deal,
              payment: payment,
              formattedStatus: _formatStatus(viewing.status),
              statusColor: _statusColor(viewing.status),
              statusIcon: _statusIcon(viewing.status),
              formattedDate: _formatDate(viewing.requestedDate),
              formattedTime: _formatTime(viewing.requestedTime),
              onConfirmOutcome: deal == null
                  ? null
                  : () => _openConfirmation(deal),
            ),
          );
        }),
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF6F8F6),
      appBar: AppBar(
        title: const Text('My Viewings'),
        backgroundColor: const Color(0xFF14532D),
        foregroundColor: Colors.white,
      ),
      body: FutureBuilder<_MyViewingsData>(
        future: _future,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }

          if (snapshot.hasError) {
            return RefreshIndicator(
              onRefresh: _refresh,
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
                    'Could not load your viewings',
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
                        setState(_loadData);
                      },
                      icon: const Icon(Icons.refresh),
                      label: const Text('Try Again'),
                    ),
                  ),
                ],
              ),
            );
          }

          final data =
              snapshot.data ??
              const _MyViewingsData(
                viewings: <Viewing>[],
                deals: <Deal>[],
                payments: <Payment>[],
              );

          final viewings = data.viewings;
          final deals = data.deals;
          final payments = data.payments;

          if (viewings.isEmpty) {
            return RefreshIndicator(
              onRefresh: _refresh,
              child: ListView(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: const EdgeInsets.all(24),
                children: const [
                  SizedBox(height: 120),
                  Icon(
                    Icons.calendar_month_outlined,
                    size: 72,
                    color: Colors.black38,
                  ),
                  SizedBox(height: 18),
                  Text(
                    'No viewing requests yet',
                    textAlign: TextAlign.center,
                    style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold),
                  ),
                  SizedBox(height: 8),
                  Text(
                    'Request a viewing from a property page and it will appear here.',
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      fontSize: 15,
                      height: 1.5,
                      color: Colors.black54,
                    ),
                  ),
                ],
              ),
            );
          }

          final needsAction = <Viewing>[];
          final upcoming = <Viewing>[];
          final past = <Viewing>[];

          for (final viewing in viewings) {
            final deal = _dealForViewing(viewing, deals);

            if (_needsCustomerAction(viewing, deal)) {
              needsAction.add(viewing);
            } else if (_isPastViewing(viewing, deal)) {
              past.add(viewing);
            } else {
              upcoming.add(viewing);
            }
          }

          return RefreshIndicator(
            onRefresh: _refresh,
            child: ListView(
              physics: const AlwaysScrollableScrollPhysics(),
              padding: const EdgeInsets.fromLTRB(16, 18, 16, 32),
              children: [
                if (needsAction.isNotEmpty) ...[
                  _buildViewingSection(
                    title: 'Needs Action',
                    viewings: needsAction,
                    deals: deals,
                    payments: payments,
                  ),
                  const SizedBox(height: 12),
                ],
                if (upcoming.isNotEmpty) ...[
                  _buildViewingSection(
                    title: 'Upcoming',
                    viewings: upcoming,
                    deals: deals,
                    payments: payments,
                  ),
                  const SizedBox(height: 12),
                ],
                if (past.isNotEmpty)
                  _buildViewingSection(
                    title: 'Past',
                    viewings: past,
                    deals: deals,
                    payments: payments,
                  ),
              ],
            ),
          );
        },
      ),
    );
  }
}

class _MyViewingsData {
  const _MyViewingsData({
    required this.viewings,
    required this.deals,
    required this.payments,
  });

  final List<Viewing> viewings;
  final List<Deal> deals;
  final List<Payment> payments;
}

class _ViewingCard extends StatefulWidget {
  const _ViewingCard({
    required this.viewing,
    required this.deal,
    required this.payment,
    required this.formattedStatus,
    required this.statusColor,
    required this.statusIcon,
    required this.formattedDate,
    required this.formattedTime,
    required this.onConfirmOutcome,
  });

  final Viewing viewing;
  final Deal? deal;
  final Payment? payment;
  final String formattedStatus;
  final Color statusColor;
  final IconData statusIcon;
  final String formattedDate;
  final String formattedTime;
  final Future<void> Function()? onConfirmOutcome;

  @override
  State<_ViewingCard> createState() => _ViewingCardState();
}

class _ViewingCardState extends State<_ViewingCard> {
  final PaymentService _paymentService = PaymentService();

  bool _isLoadingReceipt = false;
  bool _isOpeningConfirmation = false;

  Future<void> _openReceipt() async {
    final knownPayment = widget.payment;

    if (knownPayment == null || !knownPayment.isSuccessful) {
      return;
    }

    setState(() {
      _isLoadingReceipt = true;
    });

    try {
      final payment = await _paymentService.getViewingReceipt(
        viewingId: widget.viewing.id,
      );

      if (!mounted) {
        return;
      }

      await Navigator.of(context).push(
        MaterialPageRoute<void>(
          builder: (_) =>
              PaymentSuccessScreen(viewing: widget.viewing, payment: payment),
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

  Future<void> _openConfirmation() async {
    final action = widget.onConfirmOutcome;

    if (action == null || _isOpeningConfirmation) {
      return;
    }

    setState(() {
      _isOpeningConfirmation = true;
    });

    try {
      await action();
    } finally {
      if (mounted) {
        setState(() {
          _isOpeningConfirmation = false;
        });
      }
    }
  }

  Future<void> _openDetails() async {
    await Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) => ViewingDetailsScreen(viewingId: widget.viewing.id),
      ),
    );
  }

  String _nextActionText() {
    final status = widget.viewing.status.trim().toLowerCase();

    switch (status) {
      case 'pending_payment':
      case 'payment_pending':
        return 'Next: Complete payment to continue your viewing request.';
      case 'payment_processing':
        return 'Next: Complete or check your M-Pesa payment.';
      case 'payment_failed':
        return 'Next: Your payment did not complete. Review the viewing before trying again.';
      case 'paid_pending_partner':
      case 'paid_awaiting_partner':
      case 'paid':
        return 'Next: Wait for the property partner to respond.';
      case 'reschedule_proposed':
      case 'partner_reschedule':
        return 'Next: Review the new viewing date and time.';
      case 'confirmed':
        return 'Next: Attend your viewing at the confirmed date and time.';
      case 'partner_en_route':
        return 'The property partner is on the way.';
      case 'partner_arrived':
        return 'The property partner has arrived at the viewing location.';
      case 'viewing_in_progress':
      case 'viewing_started':
        return 'Your property viewing is in progress.';
      case 'completed':
        final deal = widget.deal;
        if (deal != null && !deal.customerOutcomeSubmitted) {
          return 'Next: Tell Pata Hao what happened after the viewing.';
        }
        return 'Viewing completed. No action is required right now.';
      case 'declined':
        return 'This viewing request was declined. You can browse another property.';
      case 'cancelled':
        return 'This viewing was cancelled. You can request another viewing.';
      case 'expired':
        return 'This viewing request expired. You can submit a new request.';
      case 'refunded':
        return 'This viewing payment was refunded.';
      case 'disputed':
        return 'This viewing is under review by Pata Hao.';
      default:
        return 'Open viewing details for the latest information.';
    }
  }

  @override
  Widget build(BuildContext context) {
    final hasPaymentReference = widget.viewing.paymentReference
        .trim()
        .isNotEmpty;

    final hasSuccessfulReceipt =
        widget.payment != null && widget.payment!.isSuccessful;

    final deal = widget.deal;
    final status = widget.viewing.status.trim().toLowerCase();
    final isCompleted = status == 'completed';

    final needsOutcome =
        isCompleted && deal != null && !deal.customerOutcomeSubmitted;

    final outcomeSubmitted =
        isCompleted && deal != null && deal.customerOutcomeSubmitted;

    return Card(
      margin: EdgeInsets.zero,
      elevation: 1.5,
      color: Colors.white,
      clipBehavior: Clip.antiAlias,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: InkWell(
        onTap: _openDetails,
        child: Padding(
          padding: const EdgeInsets.all(18),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Container(
                    width: 48,
                    height: 48,
                    decoration: BoxDecoration(
                      color: widget.statusColor.withValues(alpha: 0.12),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Icon(widget.statusIcon, color: widget.statusColor),
                  ),
                  const SizedBox(width: 13),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          widget.viewing.propertyTitle,
                          style: const TextStyle(
                            fontSize: 18,
                            fontWeight: FontWeight.bold,
                            color: Color(0xFF111827),
                          ),
                        ),
                        const SizedBox(height: 6),
                        Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 10,
                            vertical: 5,
                          ),
                          decoration: BoxDecoration(
                            color: widget.statusColor.withValues(alpha: 0.10),
                            borderRadius: BorderRadius.circular(20),
                          ),
                          child: Text(
                            widget.formattedStatus,
                            style: TextStyle(
                              color: widget.statusColor,
                              fontSize: 12,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                  const Padding(
                    padding: EdgeInsets.only(top: 4),
                    child: Icon(
                      Icons.chevron_right_rounded,
                      color: Colors.black38,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 18),
              const Divider(height: 1),
              const SizedBox(height: 16),
              _ViewingDetailRow(
                icon: Icons.calendar_today_outlined,
                label: 'Date',
                value: widget.formattedDate,
              ),
              const SizedBox(height: 12),
              _ViewingDetailRow(
                icon: Icons.schedule_outlined,
                label: 'Time',
                value: widget.formattedTime,
              ),
              const SizedBox(height: 12),
              _ViewingDetailRow(
                icon: Icons.payments_outlined,
                label: 'Viewing fee',
                value: 'KES ${widget.viewing.feeAmount.toStringAsFixed(0)}',
              ),
              if (hasPaymentReference) ...[
                const SizedBox(height: 12),
                _ViewingDetailRow(
                  icon: Icons.receipt_long_outlined,
                  label: 'Reference',
                  value: widget.viewing.paymentReference,
                  selectable: true,
                ),
              ],
              const SizedBox(height: 16),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: const Color(0xFFF3F4F6),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Icon(
                      Icons.arrow_circle_right_outlined,
                      size: 21,
                      color: Color(0xFF14532D),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Text(
                        _nextActionText(),
                        style: const TextStyle(
                          fontSize: 14,
                          height: 1.4,
                          fontWeight: FontWeight.w600,
                          color: Color(0xFF374151),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              if (hasSuccessfulReceipt) ...[
                const SizedBox(height: 18),
                SizedBox(
                  width: double.infinity,
                  child: OutlinedButton.icon(
                    onPressed: _isLoadingReceipt ? null : _openReceipt,
                    icon: _isLoadingReceipt
                        ? const SizedBox(
                            width: 18,
                            height: 18,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Icon(Icons.receipt_long_outlined),
                    label: Text(
                      _isLoadingReceipt ? 'Loading receipt...' : 'View Receipt',
                    ),
                  ),
                ),
              ],
              if (needsOutcome) ...[
                const SizedBox(height: 18),
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: const Color(0xFFFFF7ED),
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(color: const Color(0xFFFED7AA)),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Row(
                        children: [
                          Icon(
                            Icons.help_outline_rounded,
                            color: Color(0xFFC2410C),
                          ),
                          SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              'Did you take this property?',
                              style: TextStyle(
                                fontSize: 17,
                                fontWeight: FontWeight.bold,
                                color: Color(0xFF9A3412),
                              ),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      const Text(
                        'Tell Pata Hao what happened after your viewing.',
                        style: TextStyle(color: Color(0xFF7C2D12), height: 1.4),
                      ),
                      const SizedBox(height: 14),
                      SizedBox(
                        width: double.infinity,
                        child: FilledButton.icon(
                          onPressed: _isOpeningConfirmation
                              ? null
                              : _openConfirmation,
                          icon: _isOpeningConfirmation
                              ? const SizedBox(
                                  width: 18,
                                  height: 18,
                                  child: CircularProgressIndicator(
                                    strokeWidth: 2,
                                  ),
                                )
                              : const Icon(Icons.fact_check_outlined),
                          label: Text(
                            _isOpeningConfirmation
                                ? 'Opening...'
                                : 'Answer now',
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
              if (outcomeSubmitted) ...[
                const SizedBox(height: 18),
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: const Color(0xFFF0FDF4),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: const Color(0xFFBBF7D0)),
                  ),
                  child: const Row(
                    children: [
                      Icon(
                        Icons.check_circle_outline,
                        color: Color(0xFF15803D),
                      ),
                      SizedBox(width: 10),
                      Expanded(
                        child: Text(
                          'Your property outcome has been submitted.',
                          style: TextStyle(
                            color: Color(0xFF166534),
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
              const SizedBox(height: 14),
              Text(
                'Viewing ID: ${widget.viewing.id}',
                style: const TextStyle(fontSize: 12, color: Colors.black45),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _ViewingDetailRow extends StatelessWidget {
  const _ViewingDetailRow({
    required this.icon,
    required this.label,
    required this.value,
    this.selectable = false,
  });

  final IconData icon;
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

    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(icon, size: 19, color: const Color(0xFF14532D)),
        const SizedBox(width: 10),
        Expanded(
          child: Text(label, style: const TextStyle(color: Colors.black54)),
        ),
        const SizedBox(width: 10),
        Flexible(child: valueWidget),
      ],
    );
  }
}
