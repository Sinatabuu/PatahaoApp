import 'package:flutter/material.dart';

import '../models/viewing.dart';

class CustomerViewingActionAlert extends StatelessWidget {
  const CustomerViewingActionAlert({
    super.key,
    required this.viewing,
    required this.totalActions,
    required this.onReview,
  });

  final Viewing viewing;
  final int totalActions;
  final VoidCallback onReview;

  @override
  Widget build(BuildContext context) {
    final isScheduleChange = viewing.canRespondToReschedule;
    final additionalActions = totalActions > 1 ? totalActions - 1 : 0;

    return Container(
      margin: const EdgeInsets.fromLTRB(16, 14, 16, 4),
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: const Color(0xFFFFFBEB),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: const Color(0xFFF59E0B), width: 1.5),
        boxShadow: const [
          BoxShadow(
            color: Color(0x1AD97706),
            blurRadius: 12,
            offset: Offset(0, 5),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Row(
            children: [
              Icon(Icons.notifications_active, color: Color(0xFFB45309)),
              SizedBox(width: 9),
              Expanded(
                child: Text(
                  'Action required',
                  style: TextStyle(
                    color: Color(0xFF92400E),
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 11),
          Text(
            isScheduleChange
                ? 'Viewing time changed for ${viewing.propertyTitle}'
                : 'Protect your viewing fee for ${viewing.propertyTitle}',
            style: const TextStyle(
              color: Color(0xFF111827),
              fontSize: 16,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            isScheduleChange
                ? 'New time: ${customerViewingDate(viewing.proposedDate)} at '
                      '${customerViewingTime(viewing.proposedTime)}. '
                      'Please accept or decline it. Your payment remains '
                      'protected.'
                : 'Scheduling could not be completed. Choose Pata Hao '
                      'credit or a full refund. Your payment remains protected.',
            style: const TextStyle(color: Color(0xFF4B5563), height: 1.4),
          ),
          if (additionalActions > 0) ...[
            const SizedBox(height: 7),
            Text(
              '$additionalActions more viewing '
              '${additionalActions == 1 ? 'needs' : 'need'} your attention.',
              style: const TextStyle(
                color: Color(0xFF92400E),
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
          const SizedBox(height: 14),
          SizedBox(
            width: double.infinity,
            child: FilledButton.icon(
              onPressed: onReview,
              style: FilledButton.styleFrom(
                backgroundColor: const Color(0xFFB45309),
                foregroundColor: Colors.white,
              ),
              icon: const Icon(Icons.arrow_forward_rounded),
              label: Text(
                isScheduleChange
                    ? 'Review New Time'
                    : 'Choose Credit or Refund',
              ),
            ),
          ),
        ],
      ),
    );
  }
}

Future<bool> showCustomerViewingActionDialog(
  BuildContext context, {
  required Viewing viewing,
}) async {
  final isScheduleChange = viewing.canRespondToReschedule;

  final shouldReview = await showDialog<bool>(
    context: context,
    builder: (dialogContext) {
      return AlertDialog(
        icon: const Icon(
          Icons.notifications_active,
          color: Color(0xFFB45309),
          size: 38,
        ),
        title: Text(
          isScheduleChange
              ? 'Your viewing time changed'
              : 'Your viewing fee needs a choice',
        ),
        content: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                viewing.propertyTitle,
                style: const TextStyle(
                  fontSize: 17,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 12),
              if (isScheduleChange) ...[
                _ScheduleLine(
                  label: 'Original time',
                  value:
                      '${customerViewingDate(viewing.requestedDate)} at '
                      '${customerViewingTime(viewing.requestedTime)}',
                ),
                const SizedBox(height: 9),
                _ScheduleLine(
                  label: 'Proposed time',
                  value:
                      '${customerViewingDate(viewing.proposedDate)} at '
                      '${customerViewingTime(viewing.proposedTime)}',
                  emphasize: true,
                ),
                if (viewing.partnerResponseMessage.trim().isNotEmpty) ...[
                  const SizedBox(height: 12),
                  Text(
                    'Partner message: ${viewing.partnerResponseMessage}',
                    style: const TextStyle(height: 1.4),
                  ),
                ],
                const SizedBox(height: 12),
                Text(
                  viewing.remainingRescheduleProposals <= 1
                      ? 'This is the final revised-time proposal. If it does '
                            'not work, you can choose Pata Hao credit or a full '
                            'refund. Your payment remains protected.'
                      : 'Please accept or decline the new time. Your paid '
                            'viewing remains protected.',
                  style: const TextStyle(height: 1.4),
                ),
              ] else ...[
                Text(
                  'Scheduling could not be completed. Your KES '
                  '${viewing.feeAmount.toStringAsFixed(2)} payment remains '
                  'protected. Choose Pata Hao credit or a full refund.',
                  style: const TextStyle(height: 1.4),
                ),
              ],
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(false),
            child: const Text('Later'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(dialogContext).pop(true),
            child: const Text('Review Now'),
          ),
        ],
      );
    },
  );

  return shouldReview == true;
}

class _ScheduleLine extends StatelessWidget {
  const _ScheduleLine({
    required this.label,
    required this.value,
    this.emphasize = false,
  });

  final String label;
  final String value;
  final bool emphasize;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: emphasize ? const Color(0xFFFFF3CD) : const Color(0xFFF3F4F6),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: const TextStyle(fontSize: 12, color: Color(0xFF6B7280)),
          ),
          const SizedBox(height: 3),
          Text(
            value,
            style: TextStyle(
              fontWeight: emphasize ? FontWeight.bold : FontWeight.w600,
              color: const Color(0xFF111827),
            ),
          ),
        ],
      ),
    );
  }
}

String customerViewingDate(String? value) {
  final text = value?.trim() ?? '';
  final parsed = DateTime.tryParse(text);

  if (parsed == null) {
    return text.isEmpty ? 'Date unavailable' : text;
  }

  const months = <String>[
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

  return '${parsed.day} ${months[parsed.month - 1]} ${parsed.year}';
}

String customerViewingTime(String? value) {
  final text = value?.trim() ?? '';

  if (text.isEmpty) {
    return 'Time unavailable';
  }

  final parts = text.split(':');
  final hour24 = int.tryParse(parts.first);

  if (hour24 == null || hour24 < 0 || hour24 > 23) {
    return text;
  }

  final minute = parts.length > 1 ? parts[1].padLeft(2, '0') : '00';
  final hour12 = hour24 == 0 ? 12 : (hour24 > 12 ? hour24 - 12 : hour24);
  final period = hour24 >= 12 ? 'PM' : 'AM';

  return '$hour12:$minute $period';
}
