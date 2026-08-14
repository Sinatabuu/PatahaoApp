import 'package:flutter/material.dart';

import 'package:mobile/models/partner_dashboard.dart';
import 'package:mobile/services/partner_dashboard_service.dart';
import 'package:mobile/screens/partner_viewing_detail_screen.dart';
import 'package:mobile/screens/property_list_screen.dart';
import 'package:mobile/screens/my_properties_screen.dart';
import 'partner_post_property_screen.dart';
import 'package:mobile/services/deal_service.dart';

class PartnerDashboardScreen extends StatefulWidget {
  const PartnerDashboardScreen({super.key, this.onLogout});

  final Future<void> Function()? onLogout;

  @override
  State<PartnerDashboardScreen> createState() => _PartnerDashboardScreenState();
}

class _PartnerDashboardScreenState extends State<PartnerDashboardScreen> {
  late Future<PartnerDashboard> _dashboardFuture;
  final Set<int> _processingViewingIds = <int>{};

  @override
  void initState() {
    super.initState();
    _loadDashboard();
  }

  void _loadDashboard() {
    _dashboardFuture = PartnerDashboardService.instance.getDashboard();
  }

  Future<void> _refreshDashboard() async {
    setState(_loadDashboard);
    await _dashboardFuture;
  }

  Future<void> _logout() async {
    if (widget.onLogout == null) {
      Navigator.pop(context);
      return;
    }

    await widget.onLogout!();

    if (!mounted) {
      return;
    }

    Navigator.popUntil(context, (route) => route.isFirst);
  }

  Future<void> _openViewingDetails(PartnerDashboardViewing viewing) async {
    final changed = await Navigator.of(context).push<bool>(
      MaterialPageRoute<bool>(
        builder: (context) {
          return PartnerViewingDetailScreen(viewing: viewing);
        },
      ),
    );

    if (changed == true && mounted) {
      await _refreshDashboard();
    }
  }

  void _openBrowseProperties() {
    Navigator.of(
      context,
    ).push(MaterialPageRoute<void>(builder: (_) => const PropertyListScreen()));
  }

  Future<void> _confirmViewing(PartnerDashboardViewing viewing) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) {
        return AlertDialog(
          title: const Text('Confirm viewing'),
          content: Text(
            'Confirm the viewing for ${viewing.propertyTitle} on '
            '${viewing.requestedDate} at ${viewing.requestedTime}?',
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(dialogContext, false),
              child: const Text('Cancel'),
            ),
            ElevatedButton(
              onPressed: () => Navigator.pop(dialogContext, true),
              child: const Text('Confirm'),
            ),
          ],
        );
      },
    );

    if (confirmed != true) {
      return;
    }

    await _runViewingAction(
      viewingId: viewing.id,
      successMessage: 'Viewing confirmed successfully.',
      action: () => PartnerDashboardService.instance.confirmViewing(viewing.id),
    );
  }

  Future<void> _rescheduleViewing(PartnerDashboardViewing viewing) async {
    final initialDate =
        DateTime.tryParse(viewing.requestedDate) ?? DateTime.now();

    final now = DateTime.now();
    final minimumDate = DateTime(now.year, now.month, now.day);

    final selectedDate = await showDatePicker(
      context: context,
      initialDate: initialDate.isBefore(minimumDate)
          ? minimumDate
          : initialDate,
      firstDate: minimumDate,
      lastDate: minimumDate.add(const Duration(days: 180)),
      helpText: 'Select a new viewing date',
    );

    if (selectedDate == null || !mounted) {
      return;
    }

    final selectedTime = await showTimePicker(
      context: context,
      initialTime: _parseTimeOfDay(viewing.requestedTime),
      helpText: 'Select a new viewing time',
    );

    if (selectedTime == null || !mounted) {
      return;
    }

    String note = '';

    final shouldSubmit = await showDialog<bool>(
      context: context,
      barrierDismissible: false,
      builder: (dialogContext) {
        return AlertDialog(
          title: const Text('Suggest new time'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                '${_formatDate(selectedDate)} at '
                '${selectedTime.format(dialogContext)}',
              ),
              const SizedBox(height: 14),
              TextField(
                minLines: 2,
                maxLines: 4,
                onChanged: (value) {
                  note = value;
                },
                decoration: const InputDecoration(
                  labelText: 'Reason or note',
                  hintText: 'Example: I am available after 2:00 PM.',
                  border: OutlineInputBorder(),
                ),
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () {
                Navigator.of(dialogContext).pop(false);
              },
              child: const Text('Cancel'),
            ),
            ElevatedButton(
              onPressed: () {
                Navigator.of(dialogContext).pop(true);
              },
              child: const Text('Send proposal'),
            ),
          ],
        );
      },
    );

    if (shouldSubmit != true || !mounted) {
      return;
    }

    await _runViewingAction(
      viewingId: viewing.id,
      successMessage: 'The new viewing time was sent to the customer.',
      action: () {
        return PartnerDashboardService.instance.rescheduleViewing(
          viewingId: viewing.id,
          proposedDate: _formatDate(selectedDate),
          proposedTime: _formatTime(selectedTime),
          reason: note.trim(),
        );
      },
    );
  }

  Future<void> _declineViewing(PartnerDashboardViewing viewing) async {
    String reason = '';
    String? validationMessage;

    final shouldDecline = await showDialog<bool>(
      context: context,
      barrierDismissible: false,
      builder: (dialogContext) {
        return StatefulBuilder(
          builder: (context, setDialogState) {
            return AlertDialog(
              title: const Text('Decline viewing'),
              content: TextField(
                autofocus: true,
                minLines: 3,
                maxLines: 5,
                onChanged: (value) {
                  reason = value;

                  if (validationMessage != null && value.trim().isNotEmpty) {
                    setDialogState(() {
                      validationMessage = null;
                    });
                  }
                },
                decoration: InputDecoration(
                  labelText: 'Reason',
                  hintText: 'Explain why this viewing cannot proceed.',
                  errorText: validationMessage,
                  border: const OutlineInputBorder(),
                ),
              ),
              actions: [
                TextButton(
                  onPressed: () {
                    Navigator.of(dialogContext).pop(false);
                  },
                  child: const Text('Cancel'),
                ),
                ElevatedButton(
                  onPressed: () {
                    if (reason.trim().isEmpty) {
                      setDialogState(() {
                        validationMessage = 'Please provide a decline reason.';
                      });
                      return;
                    }

                    Navigator.of(dialogContext).pop(true);
                  },
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.red.shade700,
                    foregroundColor: Colors.white,
                  ),
                  child: const Text('Decline'),
                ),
              ],
            );
          },
        );
      },
    );

    if (shouldDecline != true || reason.trim().isEmpty || !mounted) {
      return;
    }

    await _runViewingAction(
      viewingId: viewing.id,
      successMessage: 'Viewing request declined.',
      action: () {
        return PartnerDashboardService.instance.declineViewing(
          viewingId: viewing.id,
          reason: reason.trim(),
        );
      },
    );
  }

  Future<void> _confirmPartnerOutcome(
    PartnerDashboardViewing viewing,
  ) async {
    final dealId = viewing.dealId;

    if (dealId == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text(
            'No deal is linked to this completed viewing.',
          ),
        ),
      );
      return;
    }

    if (viewing.partnerOutcomeSubmitted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text(
            'Your property outcome has already been submitted.',
          ),
        ),
      );
      return;
    }

    final isSale =
        viewing.listingType.trim().toLowerCase() == 'sale';

    final successOutcome =
        isSale ? 'purchased' : 'rented';

    final successLabel = isSale
        ? 'Customer bought this property'
        : 'Customer rented this property';

    String? selectedOutcome;

    final shouldSubmit =
        await showDialog<bool>(
      context: context,
      barrierDismissible: false,
      builder: (dialogContext) {
        return StatefulBuilder(
          builder: (context, setDialogState) {
            return AlertDialog(
              title: const Text(
                'Confirm property outcome',
              ),
              content: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment:
                    CrossAxisAlignment.start,
                children: [
                  Text(
                    viewing.propertyTitle,
                    style: const TextStyle(
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: 14),
                  RadioGroup<String>(
                    groupValue: selectedOutcome,
                    onChanged: (value) {
                      setDialogState(() {
                        selectedOutcome = value;
                      });
                    },
                    child: Column(
                      children: [
                        RadioListTile<String>(
                          value: successOutcome,
                          title: Text(successLabel),
                        ),
                        RadioListTile<String>(
                          value: 'still_deciding',
                          title: const Text(
                            'Customer is still deciding',
                          ),
                        ),
                        RadioListTile<String>(
                          value: 'declined',
                          title: const Text(
                            'Customer did not proceed',
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 8),
                  const Text(
                    'This confirmation becomes part of '
                    'the permanent deal record and '
                    'cannot be changed after submission.',
                    style: TextStyle(
                      fontSize: 13,
                      color: Colors.black54,
                    ),
                  ),
                ],
              ),
              actions: [
                TextButton(
                  onPressed: () {
                    Navigator.pop(
                      dialogContext,
                      false,
                    );
                  },
                  child: const Text('Cancel'),
                ),
                FilledButton(
                  onPressed: selectedOutcome == null
                      ? null
                      : () {
                          Navigator.pop(
                            dialogContext,
                            true,
                          );
                        },
                  child: const Text('Submit'),
                ),
              ],
            );
          },
        );
      },
    );

    if (
        shouldSubmit != true ||
        selectedOutcome == null ||
        !mounted) {
      return;
    }

    await _runViewingAction(
      viewingId: viewing.id,
      successMessage:
          'Property outcome submitted.',
      action: () async {
        await DealService.instance.submitPartnerOutcome(
          dealId: dealId,
          outcome: selectedOutcome!,
        );
      },
    );
  }

  Future<void> _runViewingAction({
    required int viewingId,
    required String successMessage,
    required Future<void> Function() action,
  }) async {
    if (_processingViewingIds.contains(viewingId)) {
      return;
    }

    setState(() {
      _processingViewingIds.add(viewingId);
    });

    try {
      await action();

      if (!mounted) {
        return;
      }

      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(successMessage)));

      await _refreshDashboard();
    } catch (error) {
      if (!mounted) {
        return;
      }

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(_cleanError(error)),
          backgroundColor: Colors.red.shade700,
        ),
      );
    } finally {
      if (mounted) {
        setState(() {
          _processingViewingIds.remove(viewingId);
        });
      }
    }
  }

  TimeOfDay _parseTimeOfDay(String value) {
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
        return TimeOfDay(hour: hour, minute: minute);
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

  DateTime? _viewingDate(PartnerDashboardViewing viewing) {
    final confirmedDate = viewing.confirmedDate?.trim() ?? '';

    if (confirmedDate.isNotEmpty) {
      return DateTime.tryParse(confirmedDate);
    }

    final proposedDate = viewing.proposedDate?.trim() ?? '';

    if (proposedDate.isNotEmpty) {
      return DateTime.tryParse(proposedDate);
    }

    return DateTime.tryParse(viewing.requestedDate.trim());
  }

  DateTime _dateOnly(DateTime value) {
    return DateTime(value.year, value.month, value.day);
  }

  bool _isViewingToday(PartnerDashboardViewing viewing) {
    final viewingDate = _viewingDate(viewing);

    if (viewingDate == null) {
      return false;
    }

    return _dateOnly(viewingDate) == _dateOnly(DateTime.now());
  }

  bool _isFutureViewing(PartnerDashboardViewing viewing) {
    final viewingDate = _viewingDate(viewing);

    if (viewingDate == null) {
      return false;
    }

    return _dateOnly(viewingDate).isAfter(_dateOnly(DateTime.now()));
  }

  bool _isAwaitingPartner(PartnerDashboardViewing viewing) {
    return viewing.status.trim().toLowerCase() == 'paid_pending_partner';
  }

  bool _isCompletedViewing(PartnerDashboardViewing viewing) {
    return viewing.status.trim().toLowerCase() == 'completed';
  }

  bool _isActiveViewing(PartnerDashboardViewing viewing) {
    const activeStatuses = <String>{'confirmed', 'reschedule_proposed'};

    return activeStatuses.contains(viewing.status.trim().toLowerCase());
  }

  List<PartnerDashboardViewing> _sortedViewings(
    Iterable<PartnerDashboardViewing> viewings,
  ) {
    final result = viewings.toList();

    result.sort((first, second) {
      final firstDate = _viewingDate(first);
      final secondDate = _viewingDate(second);

      if (firstDate == null && secondDate == null) {
        return second.id.compareTo(first.id);
      }

      if (firstDate == null) {
        return 1;
      }

      if (secondDate == null) {
        return -1;
      }

      final dateComparison = firstDate.compareTo(secondDate);

      if (dateComparison != 0) {
        return dateComparison;
      }

      return first.requestedTime.compareTo(second.requestedTime);
    });

    return result;
  }

  Widget _buildViewingSection({
    required String title,
    required String emptyMessage,
    required IconData emptyIcon,
    required List<PartnerDashboardViewing> viewings,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _SectionHeader(title: title, count: viewings.length),
        const SizedBox(height: 10),
        if (viewings.isEmpty)
          _EmptyCard(icon: emptyIcon, message: emptyMessage)
        else
          ...viewings.map(
            (viewing) => Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: _ViewingCard(
                viewing: viewing,
                isProcessing: _processingViewingIds.contains(viewing.id),
                onOpen: () => _openViewingDetails(viewing),
                onConfirm: () => _confirmViewing(viewing),
                onReschedule: () => _rescheduleViewing(viewing),
                onDecline: () => _declineViewing(viewing),
                onConfirmOutcome: () => _confirmPartnerOutcome(viewing),
              ),
            ),
          ),
      ],
    );
  }

  Future<void> _openMyProperties() async {
    await Navigator.of(context).push<void>(
      MaterialPageRoute<void>(builder: (_) => const MyPropertiesScreen()),
    );

    if (mounted) {
      await _refreshDashboard();
    }
  }
  Future<void> _openPostProperty() async {
    final changed = await Navigator.of(context).push<bool>(
      MaterialPageRoute<bool>(
        builder: (_) => const PartnerPostPropertyScreen(),
      ),
    );

    if (changed == true && mounted) {
      await _refreshDashboard();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF6F8F6),
      appBar: AppBar(
        title: const Text('Partner Command Center'),
        backgroundColor: Colors.white,
        actions: [
          IconButton(
            tooltip: 'Browse Properties',
            onPressed: _openBrowseProperties,
            icon: const Icon(Icons.search),
          ),
          IconButton(
            tooltip: 'Refresh',
            onPressed: _refreshDashboard,
            icon: const Icon(Icons.refresh),
          ),
          if (widget.onLogout != null)
            IconButton(
              tooltip: 'Logout',
              onPressed: _logout,
              icon: const Icon(Icons.logout),
            ),
        ],
      ),
      body: FutureBuilder<PartnerDashboard>(
        future: _dashboardFuture,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }

          if (snapshot.hasError) {
            return _ErrorView(
              message: _cleanError(snapshot.error),
              onRetry: _refreshDashboard,
            );
          }

          final dashboard = snapshot.data;

          if (dashboard == null) {
            return _ErrorView(
              message: 'The partner dashboard returned no data.',
              onRetry: _refreshDashboard,
            );
          }

          final allViewings = dashboard.viewingRequests;

          final awaitingResponse = _sortedViewings(
            allViewings.where(_isAwaitingPartner),
          );

          final todaysViewings = _sortedViewings(
            allViewings.where(
              (viewing) =>
                  _isActiveViewing(viewing) && _isViewingToday(viewing),
            ),
          );

          final upcomingViewings = _sortedViewings(
            allViewings.where(
              (viewing) =>
                  _isActiveViewing(viewing) && _isFutureViewing(viewing),
            ),
          );

          final completedViewings =
              allViewings.where(_isCompletedViewing).toList()
                ..sort((first, second) => second.id.compareTo(first.id));

          return RefreshIndicator(
            onRefresh: _refreshDashboard,
            child: ListView(
              physics: const AlwaysScrollableScrollPhysics(),
              padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
              children: [
                _PartnerHeader(partner: dashboard.partner),
                const SizedBox(height: 16),
                _SummarySection(summary: dashboard.summary),
                const SizedBox(height: 24),
                _QuickActionsSection(
                  propertyCount: dashboard.properties.length,
                  viewingCount: allViewings.length,
                  onMyProperties: _openMyProperties,
                  onPostProperty: _openPostProperty,
                  onBrowseProperties: _openBrowseProperties,
                ),
                
                const SizedBox(height: 28),
                _buildViewingSection(
                  title: 'Awaiting Your Response',
                  emptyMessage:
                      'No paid viewing requests are '
                      'waiting for your response.',
                  emptyIcon: Icons.mark_email_read_outlined,
                  viewings: awaitingResponse,
                ),
                const SizedBox(height: 24),
                _buildViewingSection(
                  title: "Today's Viewings",
                  emptyMessage:
                      'You have no confirmed viewings '
                      'scheduled for today.',
                  emptyIcon: Icons.today_outlined,
                  viewings: todaysViewings,
                ),
                const SizedBox(height: 24),
                _buildViewingSection(
                  title: 'Upcoming Viewings',
                  emptyMessage:
                      'There are no upcoming confirmed '
                      'or proposed viewings.',
                  emptyIcon: Icons.event_available_outlined,
                  viewings: upcomingViewings,
                ),
                const SizedBox(height: 24),
                _buildViewingSection(
                  title: 'Completed Viewings',
                  emptyMessage: 'Completed viewings will appear here.',
                  emptyIcon: Icons.task_alt_outlined,
                  viewings: completedViewings,
                ),
              ],
            ),
          );
        },
      ),
    );
  }

  String _cleanError(Object? error) {
    return error.toString().replaceFirst('Exception: ', '').trim();
  }
}

class _PartnerHeader extends StatelessWidget {
  const _PartnerHeader({required this.partner});

  final PartnerDashboardProfile partner;

  @override
  Widget build(BuildContext context) {
    final displayName = _firstAvailable([
      partner.displayName,
      partner.businessName,
      partner.name,
      'Partner',
    ]);

    final location = [
      partner.town,
      partner.county,
    ].where((value) => value.trim().isNotEmpty).join(', ');

    return Card(
      elevation: 0,
      color: Colors.white,
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            CircleAvatar(
              radius: 34,
              backgroundColor: const Color(0xFFE4F3E2),
              backgroundImage: partner.profilePhoto != null
                  ? NetworkImage(partner.profilePhoto!)
                  : null,
              child: partner.profilePhoto == null
                  ? const Icon(
                      Icons.business,
                      size: 34,
                      color: Color(0xFF2E8B28),
                    )
                  : null,
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    displayName,
                    style: const TextStyle(
                      fontSize: 21,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  if (partner.businessName.isNotEmpty &&
                      partner.businessName != displayName)
                    Padding(
                      padding: const EdgeInsets.only(top: 3),
                      child: Text(
                        partner.businessName,
                        style: const TextStyle(color: Colors.black54),
                      ),
                    ),
                  if (partner.partnerType.isNotEmpty)
                    Padding(
                      padding: const EdgeInsets.only(top: 8),
                      child: _StatusBadge(
                        text: partner.partnerType,
                        backgroundColor: const Color(0xFFE8F2FF),
                        foregroundColor: const Color(0xFF1C5D99),
                      ),
                    ),
                  if (location.isNotEmpty)
                    Padding(
                      padding: const EdgeInsets.only(top: 10),
                      child: Row(
                        children: [
                          const Icon(
                            Icons.location_on_outlined,
                            size: 18,
                            color: Colors.black54,
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
                    ),
                  const SizedBox(height: 10),
                  Row(
                    children: [
                      Icon(
                        partner.acceptsViewingRequests
                            ? Icons.check_circle
                            : Icons.cancel,
                        size: 18,
                        color: partner.acceptsViewingRequests
                            ? Colors.green
                            : Colors.red,
                      ),
                      const SizedBox(width: 6),
                      Expanded(
                        child: Text(
                          partner.acceptsViewingRequests
                              ? 'Accepting viewing requests'
                              : 'Not accepting viewing requests',
                          style: TextStyle(
                            color: partner.acceptsViewingRequests
                                ? Colors.green.shade800
                                : Colors.red.shade800,
                            fontWeight: FontWeight.w600,
                          ),
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

class _QuickActionsSection extends StatelessWidget {
  const _QuickActionsSection({
    required this.propertyCount,
    required this.viewingCount,
    required this.onMyProperties,
    required this.onPostProperty,
    required this.onBrowseProperties,
  });

  final int propertyCount;
  final int viewingCount;
  final VoidCallback onMyProperties;
  final VoidCallback onBrowseProperties;
  final VoidCallback onPostProperty;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Quick Actions',
          style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 10),
        _DashboardActionCard(
          icon: Icons.home_work_outlined,
          title: 'My Properties',
          subtitle: propertyCount == 1
              ? 'Manage 1 assigned property.'
              : 'Manage $propertyCount assigned properties.',
          actionLabel: 'Open properties',
          onPressed: onMyProperties,
        ),
        const SizedBox(height: 12),
        _DashboardActionCard(
          icon: Icons.add_home_work_outlined,
          title: 'Post Property',
          subtitle: 'Add a property or join an existing nearby property.',
          actionLabel: 'Start posting',
          onPressed: onPostProperty,
        ),
        const SizedBox(height: 12),
        _DashboardActionCard(
          icon: Icons.search,
          title: 'Browse Properties',
          subtitle: 'Open the public property marketplace.',
          actionLabel: 'Browse marketplace',
          onPressed: onBrowseProperties,
        ),
        const SizedBox(height: 12),
        _DashboardActionCard(
          icon: Icons.calendar_month_outlined,
          title: 'Viewing Requests',
          subtitle: viewingCount == 1
              ? '1 viewing request is shown below.'
              : '$viewingCount viewing requests are shown below.',
          actionLabel: 'View requests',
          onPressed: () {
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(
                content: Text('Scroll down to manage viewing requests.'),
              ),
            );
          },
        ),
      ],
    );
  }
}

class _DashboardActionCard extends StatelessWidget {
  const _DashboardActionCard({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.actionLabel,
    required this.onPressed,
  });

  final IconData icon;
  final String title;
  final String subtitle;
  final String actionLabel;
  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 0,
      color: Colors.white,
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: onPressed,
        child: Padding(
          padding: const EdgeInsets.all(18),
          child: Row(
            children: [
              Container(
                width: 50,
                height: 50,
                decoration: BoxDecoration(
                  color: const Color(0xFFE4F3E2),
                  borderRadius: BorderRadius.circular(14),
                ),
                child: Icon(icon, color: const Color(0xFF2E8B28)),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      title,
                      style: const TextStyle(
                        fontSize: 17,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      subtitle,
                      style: const TextStyle(color: Colors.black54),
                    ),
                    const SizedBox(height: 10),
                    Text(
                      actionLabel,
                      style: const TextStyle(
                        color: Color(0xFF2E8B28),
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ],
                ),
              ),
              const Icon(Icons.chevron_right),
            ],
          ),
        ),
      ),
    );
  }
}

class _SummarySection extends StatelessWidget {
  const _SummarySection({required this.summary});

  final PartnerDashboardSummary summary;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Summary',
          style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 10),
        GridView.count(
          crossAxisCount: 2,
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          crossAxisSpacing: 12,
          mainAxisSpacing: 12,
          childAspectRatio: 1.65,
          children: [
            _SummaryCard(
              label: 'Properties',
              value: summary.properties.total,
              icon: Icons.home_work_outlined,
            ),
            _SummaryCard(
              label: 'Published',
              value: summary.properties.published,
              icon: Icons.public,
            ),
            _SummaryCard(
              label: 'Viewing Requests',
              value: summary.viewings.total,
              icon: Icons.calendar_month_outlined,
            ),
            _SummaryCard(
              label: 'Awaiting Response',
              value: summary.viewings.paidPendingPartner,
              icon: Icons.notifications_active_outlined,
            ),
          ],
        ),
      ],
    );
  }
}

class _SummaryCard extends StatelessWidget {
  const _SummaryCard({
    required this.label,
    required this.value,
    required this.icon,
  });

  final String label;
  final int value;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 0,
      color: Colors.white,
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Row(
          children: [
            Container(
              width: 42,
              height: 42,
              decoration: BoxDecoration(
                color: const Color(0xFFE4F3E2),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Icon(icon, color: const Color(0xFF2E8B28)),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    value.toString(),
                    style: const TextStyle(
                      fontSize: 22,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  Text(
                    label,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontSize: 12, color: Colors.black54),
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

class _SectionHeader extends StatelessWidget {
  const _SectionHeader({required this.title, required this.count});

  final String title;
  final int count;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Expanded(
          child: Text(
            title,
            style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
          ),
        ),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
          decoration: BoxDecoration(
            color: const Color(0xFFE4F3E2),
            borderRadius: BorderRadius.circular(20),
          ),
          child: Text(
            count.toString(),
            style: const TextStyle(
              color: Color(0xFF2E8B28),
              fontWeight: FontWeight.bold,
            ),
          ),
        ),
      ],
    );
  }
}

class _ViewingCard extends StatelessWidget {
  const _ViewingCard({
    required this.viewing,
    required this.isProcessing,
    required this.onOpen,
    required this.onConfirm,
    required this.onReschedule,
    required this.onDecline,
    required this.onConfirmOutcome,
  });

  final PartnerDashboardViewing viewing;
  final bool isProcessing;

  final VoidCallback onOpen;
  final Future<void> Function() onConfirm;
  final Future<void> Function() onReschedule;
  final Future<void> Function() onDecline;
  final Future<void> Function() onConfirmOutcome;

  @override
  Widget build(BuildContext context) {
    final customerName = viewing.customerName.isEmpty
        ? viewing.customerEmail
        : viewing.customerName;
    debugPrint(
      'PARTNER VIEWING: '
      'id=${viewing.id} '
      'property=${viewing.propertyTitle} '
      'status=${viewing.status} '
      'dealId=${viewing.dealId} '
      'outcomeSubmitted=${viewing.partnerOutcomeSubmitted}',
    );

    return Card(
      elevation: 0,
      color: Colors.white,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const CircleAvatar(
                  backgroundColor: Color(0xFFE4F3E2),
                  child: Icon(Icons.person_outline, color: Color(0xFF2E8B28)),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        viewing.propertyTitle,
                        style: const TextStyle(
                          fontSize: 17,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      const SizedBox(height: 3),
                      Text(
                        customerName.isEmpty ? 'Customer' : customerName,
                        style: const TextStyle(color: Colors.black54),
                      ),
                    ],
                  ),
                ),
                _StatusBadge(
                  text: viewing.status,
                  backgroundColor: _statusBackground(viewing.status),
                  foregroundColor: _statusForeground(viewing.status),
                ),
              ],
            ),
            const Divider(height: 26),
            _InformationRow(
              icon: Icons.calendar_today_outlined,
              label: 'Requested date',
              value: viewing.requestedDate,
            ),
            const SizedBox(height: 8),
            _InformationRow(
              icon: Icons.access_time,
              label: 'Requested time',
              value: viewing.requestedTime,
            ),
            const SizedBox(height: 8),
            const _InformationRow(
              icon: Icons.verified_outlined,
              label: 'Viewing clearance',
              value: 'Payment verified',
            ),
            const SizedBox(height: 12),
            const _PartnerClearanceNotice(),
            if (viewing.paymentReference.isNotEmpty) ...[
              const SizedBox(height: 8),
              _InformationRow(
                icon: Icons.receipt_long_outlined,
                label: 'Payment reference',
                value: viewing.paymentReference,
              ),
            ],
            if (viewing.customerMessage.isNotEmpty) ...[
              const SizedBox(height: 12),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: const Color(0xFFF6F8F6),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Customer message',
                      style: TextStyle(fontWeight: FontWeight.w600),
                    ),
                    const SizedBox(height: 4),
                    Text(viewing.customerMessage),
                  ],
                ),
              ),
            ],

            if (viewing.partnerResponseMessage.isNotEmpty) ...[
              const SizedBox(height: 12),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: const Color(0xFFE8F5E9),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: Colors.green.shade200),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Partner response',
                      style: TextStyle(
                        fontWeight: FontWeight.bold,
                        color: Colors.green,
                      ),
                    ),
                    const SizedBox(height: 6),
                    Text(viewing.partnerResponseMessage),

                    if (viewing.proposedDate != null) ...[
                      const SizedBox(height: 10),
                      Row(
                        children: [
                          const Icon(
                            Icons.calendar_today,
                            size: 16,
                            color: Colors.green,
                          ),
                          const SizedBox(width: 6),
                          Expanded(
                            child: Text(
                              'New Date: ${viewing.proposedDate}',
                              style: const TextStyle(
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ],

                    if (viewing.proposedTime != null) ...[
                      const SizedBox(height: 6),
                      Row(
                        children: [
                          const Icon(
                            Icons.access_time,
                            size: 16,
                            color: Colors.green,
                          ),
                          const SizedBox(width: 6),
                          Expanded(
                            child: Text(
                              'New Time: ${viewing.proposedTime}',
                              style: const TextStyle(
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ],
                  ],
                ),
              ),
            ],

            if (viewing.status == 'paid_pending_partner') ...[
              const SizedBox(height: 16),
              if (isProcessing)
                const Center(
                  child: Padding(
                    padding: EdgeInsets.symmetric(vertical: 8),
                    child: CircularProgressIndicator(),
                  ),
                )
              else ...[
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton.icon(
                    onPressed: onConfirm,
                    icon: const Icon(Icons.check_circle_outline),
                    label: const Text('Confirm Viewing'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFF2E8B28),
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(vertical: 13),
                    ),
                  ),
                ),
                const SizedBox(height: 8),
                Row(
                  children: [
                    Expanded(
                      child: OutlinedButton.icon(
                        onPressed: onReschedule,
                        icon: const Icon(Icons.schedule),
                        label: const Text('New Time'),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: OutlinedButton.icon(
                        onPressed: onDecline,
                        icon: const Icon(Icons.close),
                        label: const Text('Decline'),
                        style: OutlinedButton.styleFrom(
                          foregroundColor: Colors.red.shade700,
                          side: BorderSide(color: Colors.red.shade300),
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            ],
            if (viewing.status == 'completed') ...[
              const SizedBox(height: 16),

              if (isProcessing)
                const Center(
                  child: Padding(
                    padding: EdgeInsets.symmetric(vertical: 8),
                    child: CircularProgressIndicator(),
                  ),
                )
              else if (viewing.partnerOutcomeSubmitted)
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: Colors.green.shade50,
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: const Row(
                    children: [
                      Icon(
                        Icons.check_circle_outline,
                        color: Colors.green,
                      ),
                      SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          'Property outcome submitted.',
                          style: TextStyle(
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ),
                    ],
                  ),
                )
              else if (viewing.dealId != null)
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton.icon(
                    onPressed: onConfirmOutcome,
                    icon: const Icon(Icons.check_circle_outline),
                    label: const Text('Confirm Outcome'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFF2E8B28),
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(vertical: 13),
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

class _InformationRow extends StatelessWidget {
  const _InformationRow({
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
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(icon, size: 19, color: Colors.black54),
        const SizedBox(width: 8),
        SizedBox(
          width: 116,
          child: Text(label, style: const TextStyle(color: Colors.black54)),
        ),
        Expanded(
          child: Text(
            value.isEmpty ? 'Not provided' : value,
            style: const TextStyle(fontWeight: FontWeight.w600),
          ),
        ),
      ],
    );
  }
}

class _StatusBadge extends StatelessWidget {
  const _StatusBadge({
    required this.text,
    required this.backgroundColor,
    required this.foregroundColor,
  });

  final String text;
  final Color backgroundColor;
  final Color foregroundColor;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 5),
      decoration: BoxDecoration(
        color: backgroundColor,
        borderRadius: BorderRadius.circular(20),
      ),
      child: Text(
        _humanize(text),
        style: TextStyle(
          color: foregroundColor,
          fontSize: 11,
          fontWeight: FontWeight.bold,
        ),
      ),
    );
  }
}

class _EmptyCard extends StatelessWidget {
  const _EmptyCard({required this.icon, required this.message});

  final IconData icon;
  final String message;

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 0,
      color: Colors.white,
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 28),
        child: Column(
          children: [
            Icon(icon, size: 42, color: Colors.black38),
            const SizedBox(height: 10),
            Text(
              message,
              textAlign: TextAlign.center,
              style: const TextStyle(color: Colors.black54),
            ),
          ],
        ),
      ),
    );
  }
}

class _ErrorView extends StatelessWidget {
  const _ErrorView({required this.message, required this.onRetry});

  final String message;
  final Future<void> Function() onRetry;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.error_outline, size: 54, color: Colors.redAccent),
            const SizedBox(height: 14),
            const Text(
              'Unable to load dashboard',
              style: TextStyle(fontSize: 19, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            Text(
              message,
              textAlign: TextAlign.center,
              style: const TextStyle(color: Colors.black54),
            ),
            const SizedBox(height: 18),
            ElevatedButton.icon(
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

String _firstAvailable(List<String> values) {
  for (final value in values) {
    if (value.trim().isNotEmpty) {
      return value.trim();
    }
  }

  return 'Partner';
}

String _humanize(String value) {
  if (value.trim().isEmpty) {
    return 'Unknown';
  }

  return value
      .trim()
      .replaceAll('_', ' ')
      .split(' ')
      .where((word) => word.isNotEmpty)
      .map(
        (word) => '${word[0].toUpperCase()}${word.substring(1).toLowerCase()}',
      )
      .join(' ');
}

Color _statusBackground(String status) {
  switch (status.toLowerCase()) {
    case 'published':
    case 'confirmed':
    case 'paid':
      return const Color(0xFFE3F4E2);

    case 'paid_pending_partner':
    case 'pending':
    case 'pending_payment':
      return const Color(0xFFFFF1CC);

    case 'reserved':
    case 'reschedule_proposed':
      return const Color(0xFFE8F2FF);

    case 'rented':
    case 'sold':
      return const Color(0xFFE9E4F7);

    case 'cancelled':
    case 'rejected':
      return const Color(0xFFFFE3E3);

    default:
      return const Color(0xFFF0F2F0);
  }
}

Color _statusForeground(String status) {
  switch (status.toLowerCase()) {
    case 'published':
    case 'confirmed':
    case 'paid':
      return const Color(0xFF287A22);

    case 'paid_pending_partner':
    case 'pending':
    case 'pending_payment':
      return const Color(0xFF8A6500);

    case 'reserved':
    case 'reschedule_proposed':
      return const Color(0xFF1C5D99);

    case 'rented':
    case 'sold':
      return const Color(0xFF5B3B91);

    case 'cancelled':
    case 'rejected':
      return const Color(0xFF9C2424);

    default:
      return Colors.black54;
  }
}

class _PartnerClearanceNotice extends StatelessWidget {
  const _PartnerClearanceNotice();

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFFE8F5EC),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFF86EFAC)),
      ),
      child: const Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(Icons.verified_outlined, color: Color(0xFF15803D), size: 20),
          SizedBox(width: 10),
          Expanded(
            child: Text(
              'Customer payment has been verified by Pata Hao. '
              'Proceed with the viewing and do not collect cash.',
              style: TextStyle(
                color: Color(0xFF14532D),
                height: 1.4,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
