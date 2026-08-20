import 'package:flutter/material.dart';

import '../models/viewing.dart';

class ViewingTimeline extends StatelessWidget {
  const ViewingTimeline({super.key, required this.viewing});

  final Viewing viewing;

  @override
  Widget build(BuildContext context) {
    final entries = _buildTimelineEntries(viewing);

    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: const Color(0xFFE5E7EB)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Row(
            children: [
              Icon(Icons.route_outlined, color: Color(0xFF14532D)),
              SizedBox(width: 10),
              Text(
                'Viewing Journey',
                style: TextStyle(
                  fontSize: 19,
                  fontWeight: FontWeight.bold,
                  color: Color(0xFF111827),
                ),
              ),
            ],
          ),
          const SizedBox(height: 6),
          const Text(
            'Follow every step of your property viewing.',
            style: TextStyle(color: Colors.black54, height: 1.4),
          ),
          const SizedBox(height: 20),
          ...List.generate(entries.length, (index) {
            final entry = entries[index];

            return _TimelineEntryWidget(
              entry: entry,
              isLast: index == entries.length - 1,
            );
          }),
        ],
      ),
    );
  }

  List<_TimelineEntry> _buildTimelineEntries(Viewing viewing) {
    final eventMap = <String, ViewingEvent>{};

    for (final event in viewing.sortedEvents) {
      eventMap[event.eventType] = event;
    }

    final requestEvent = eventMap['viewing_requested'];

    final paymentEvent = eventMap['payment_received'];

    final confirmedEvent = eventMap['partner_confirmed'];

    final rescheduleEvent = eventMap['reschedule_proposed'];

    final enRouteEvent = eventMap['partner_en_route'];

    final arrivedEvent = eventMap['partner_arrived'];

    final startedEvent = eventMap['viewing_started'];

    final completedEvent = eventMap['viewing_completed'];

    final isPaid = viewing.isPaid || viewing.paymentReference.trim().isNotEmpty;

    final isConfirmed = const {
      'confirmed',
      'completed',
    }.contains(viewing.effectiveBookingStatus);

    final isCompleted =
        viewing.effectiveBookingStatus == 'completed' || completedEvent != null;

    return [
      _TimelineEntry(
        title: 'Viewing requested',
        description: 'Your viewing request was created.',
        icon: Icons.calendar_month_outlined,
        isComplete: true,
        timestamp: requestEvent?.createdAt ?? viewing.createdAt,
        notes: requestEvent?.notes ?? '',
      ),
      _TimelineEntry(
        title: 'Payment received',
        description: isPaid
            ? 'Your viewing fee was received.'
            : 'Complete payment to continue.',
        icon: Icons.payments_outlined,
        isComplete: isPaid,
        timestamp: paymentEvent?.createdAt,
        notes: paymentEvent?.notes ?? '',
      ),
      _TimelineEntry(
        title: rescheduleEvent != null
            ? 'New schedule proposed'
            : 'Partner confirmed',
        description: rescheduleEvent != null
            ? 'The partner proposed another date or time.'
            : isConfirmed
            ? 'The partner accepted your viewing.'
            : 'Waiting for the partner to respond.',
        icon: rescheduleEvent != null
            ? Icons.update_rounded
            : Icons.verified_outlined,
        isComplete:
            confirmedEvent != null || rescheduleEvent != null || isConfirmed,
        timestamp:
            rescheduleEvent?.createdAt ??
            confirmedEvent?.createdAt ??
            viewing.partnerRespondedAt,
        notes:
            rescheduleEvent?.notes ??
            confirmedEvent?.notes ??
            viewing.partnerResponseMessage,
      ),
      _TimelineEntry(
        title: 'Partner en route',
        description: enRouteEvent != null
            ? 'The partner is travelling to the property.'
            : 'You will be notified when the partner leaves.',
        icon: Icons.directions_car_outlined,
        isComplete: enRouteEvent != null,
        timestamp: enRouteEvent?.createdAt ?? viewing.partnerDepartedAt,
        notes: enRouteEvent?.notes ?? '',
      ),
      _TimelineEntry(
        title: 'Partner arrived',
        description: arrivedEvent != null
            ? 'The partner arrived at the property.'
            : 'The partner has not marked arrival yet.',
        icon: Icons.location_on_outlined,
        isComplete: arrivedEvent != null,
        timestamp: arrivedEvent?.createdAt ?? viewing.partnerArrivedAt,
        notes: arrivedEvent?.notes ?? '',
      ),
      _TimelineEntry(
        title: 'Viewing started',
        description: startedEvent != null
            ? 'Your property viewing is in progress.'
            : 'The viewing has not started yet.',
        icon: Icons.meeting_room_outlined,
        isComplete: startedEvent != null,
        timestamp: startedEvent?.createdAt ?? viewing.viewingStartedAt,
        notes: startedEvent?.notes ?? '',
      ),
      _TimelineEntry(
        title: 'Viewing completed',
        description: isCompleted
            ? 'The property viewing was completed.'
            : 'This step will be completed after the visit.',
        icon: Icons.task_alt_outlined,
        isComplete: isCompleted,
        timestamp: completedEvent?.createdAt ?? viewing.completedAt,
        notes: completedEvent?.notes ?? viewing.completionNotes,
      ),
    ];
  }
}

class _TimelineEntry {
  const _TimelineEntry({
    required this.title,
    required this.description,
    required this.icon,
    required this.isComplete,
    this.timestamp,
    this.notes = '',
  });

  final String title;
  final String description;
  final IconData icon;
  final bool isComplete;
  final String? timestamp;
  final String notes;
}

class _TimelineEntryWidget extends StatelessWidget {
  const _TimelineEntryWidget({required this.entry, required this.isLast});

  final _TimelineEntry entry;
  final bool isLast;

  @override
  Widget build(BuildContext context) {
    final activeColor = entry.isComplete
        ? const Color(0xFF15803D)
        : const Color(0xFF9CA3AF);

    final backgroundColor = entry.isComplete
        ? const Color(0xFFDCFCE7)
        : const Color(0xFFF3F4F6);

    return IntrinsicHeight(
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 44,
            child: Column(
              children: [
                Container(
                  width: 38,
                  height: 38,
                  decoration: BoxDecoration(
                    color: backgroundColor,
                    shape: BoxShape.circle,
                    border: Border.all(color: activeColor, width: 2),
                  ),
                  child: Icon(
                    entry.isComplete ? Icons.check_rounded : entry.icon,
                    size: 20,
                    color: activeColor,
                  ),
                ),
                if (!isLast)
                  Expanded(
                    child: Container(
                      width: 2,
                      margin: const EdgeInsets.symmetric(vertical: 5),
                      color: entry.isComplete
                          ? const Color(0xFF86EFAC)
                          : const Color(0xFFD1D5DB),
                    ),
                  ),
              ],
            ),
          ),
          const SizedBox(width: 13),
          Expanded(
            child: Padding(
              padding: EdgeInsets.only(bottom: isLast ? 0 : 22),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    entry.title,
                    style: TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.bold,
                      color: entry.isComplete
                          ? const Color(0xFF111827)
                          : Colors.black54,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    entry.description,
                    style: const TextStyle(color: Colors.black54, height: 1.4),
                  ),
                  if (entry.timestamp != null &&
                      entry.timestamp!.trim().isNotEmpty) ...[
                    const SizedBox(height: 6),
                    Text(
                      _formatTimestamp(entry.timestamp!),
                      style: TextStyle(
                        fontSize: 12,
                        color: activeColor,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                  if (entry.notes.trim().isNotEmpty) ...[
                    const SizedBox(height: 8),
                    Container(
                      width: double.infinity,
                      padding: const EdgeInsets.all(10),
                      decoration: BoxDecoration(
                        color: const Color(0xFFF9FAFB),
                        borderRadius: BorderRadius.circular(10),
                        border: Border.all(color: const Color(0xFFE5E7EB)),
                      ),
                      child: Text(
                        entry.notes.trim(),
                        style: const TextStyle(
                          fontSize: 13,
                          color: Colors.black54,
                          height: 1.4,
                        ),
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  String _formatTimestamp(String value) {
    final parsed = DateTime.tryParse(value);

    if (parsed == null) {
      return value;
    }

    final local = parsed.toLocal();

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

    final hour = local.hour == 0
        ? 12
        : local.hour > 12
        ? local.hour - 12
        : local.hour;

    final minute = local.minute.toString().padLeft(2, '0');

    final period = local.hour >= 12 ? 'PM' : 'AM';

    return '${local.day} '
        '${months[local.month - 1]} '
        '${local.year} at '
        '$hour:$minute $period';
  }
}
