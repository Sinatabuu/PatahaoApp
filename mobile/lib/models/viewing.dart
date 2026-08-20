class Viewing {
  const Viewing({
    required this.id,
    required this.customerId,
    required this.customerName,
    required this.propertyId,
    required this.propertyTitle,
    required this.requestedDate,
    required this.requestedTime,
    required this.customerMessage,
    required this.feeAmount,
    required this.status,
    required this.bookingStatus,
    required this.operationalStatus,
    required this.paymentReference,
    required this.partnerResponseMessage,
    required this.completionNotes,
    required this.events,
    required this.createdAt,
    required this.updatedAt,
    this.assignedPartnerId,
    this.assignedPartnerName = '',
    this.proposedDate,
    this.proposedTime,
    this.confirmedDate,
    this.confirmedTime,
    this.partnerRespondedAt,
    this.completedAt,
    this.partnerDepartedAt,
    this.partnerArrivedAt,
    this.viewingStartedAt,
  });

  final int id;

  final int customerId;
  final String customerName;

  final int propertyId;
  final String propertyTitle;

  final int? assignedPartnerId;
  final String assignedPartnerName;

  final String requestedDate;
  final String requestedTime;
  final String customerMessage;

  final double feeAmount;

  final String status;
  final String bookingStatus;
  final String operationalStatus;

  final String paymentReference;
  final String partnerResponseMessage;

  final String? proposedDate;
  final String? proposedTime;

  final String? confirmedDate;
  final String? confirmedTime;

  final String? partnerRespondedAt;
  final String? completedAt;
  final String? partnerDepartedAt;
  final String? partnerArrivedAt;
  final String? viewingStartedAt;

  final String completionNotes;
  final List<ViewingEvent> events;
  final String createdAt;
  final String updatedAt;

  factory Viewing.fromJson(Map<String, dynamic> json) {
    return Viewing(
      id: _parseInt(json['id']),
      customerId: _parseInt(json['customer']),
      customerName: json['customer_name']?.toString() ?? '',
      propertyId: _parseInt(json['property']),
      propertyTitle: json['property_title']?.toString() ?? 'Property',
      assignedPartnerId: _parseNullableInt(json['assigned_partner']),
      assignedPartnerName: json['assigned_partner_name']?.toString() ?? '',
      requestedDate: json['requested_date']?.toString() ?? '',
      requestedTime: json['requested_time']?.toString() ?? '',
      customerMessage: json['customer_message']?.toString() ?? '',
      feeAmount: _parseDouble(json['fee_amount']),
      status: json['status']?.toString() ?? 'pending_payment',
      bookingStatus:
          json['booking_status']?.toString() ??
          json['status']?.toString() ??
          'pending_payment',
      operationalStatus: json['operational_status']?.toString() ?? 'idle',
      paymentReference: json['payment_reference']?.toString() ?? '',
      partnerResponseMessage:
          json['partner_response_message']?.toString() ?? '',
      proposedDate: _parseNullableString(json['proposed_date']),
      proposedTime: _parseNullableString(json['proposed_time']),
      confirmedDate: _parseNullableString(json['confirmed_date']),
      confirmedTime: _parseNullableString(json['confirmed_time']),
      partnerRespondedAt: _parseNullableString(json['partner_responded_at']),
      completedAt: _parseNullableString(json['completed_at']),
      partnerDepartedAt: _parseNullableString(json['partner_departed_at']),
      partnerArrivedAt: _parseNullableString(json['partner_arrived_at']),
      viewingStartedAt: _parseNullableString(json['viewing_started_at']),
      completionNotes: json['completion_notes']?.toString() ?? '',
      events: _parseEvents(json['events']),
      createdAt: json['created_at']?.toString() ?? '',
      updatedAt: json['updated_at']?.toString() ?? '',
    );
  }

  int get property {
    return propertyId;
  }

  String get effectiveBookingStatus {
    if (bookingStatus.trim().isNotEmpty) {
      return bookingStatus;
    }

    return status;
  }

  String get friendlyStatus {
    switch (effectiveBookingStatus) {
      case 'pending_payment':
        return 'Payment required';

      case 'payment_processing':
        return 'Payment processing';

      case 'paid_pending_partner':
      case 'paid_awaiting_partner':
      case 'paid':
        return 'Awaiting partner response';

      case 'confirmed':
        return 'Confirmed';

      case 'partner_reschedule':
      case 'reschedule_proposed':
        return 'New schedule proposed';

      case 'declined':
        return 'Declined';

      case 'cancelled':
        return 'Cancelled';

      case 'completed':
        return 'Completed';

      case 'expired':
        return 'Expired';

      default:
        return _formatStatus(effectiveBookingStatus);
    }
  }

  bool get isPaid {
    return const {
      'paid_pending_partner',
      'paid_awaiting_partner',
      'paid',
      'confirmed',
      'partner_reschedule',
      'reschedule_proposed',
      'completed',
    }.contains(effectiveBookingStatus);
  }

  bool get isPaymentProcessing {
    return effectiveBookingStatus == 'payment_processing';
  }

  bool get hasProposedSchedule {
    return proposedDate != null || proposedTime != null;
  }

  bool get hasConfirmedSchedule {
    return confirmedDate != null || confirmedTime != null;
  }

  static List<ViewingEvent> _parseEvents(dynamic value) {
    if (value is! List) {
      return const <ViewingEvent>[];
    }

    return value
        .whereType<Map>()
        .map((item) => ViewingEvent.fromJson(Map<String, dynamic>.from(item)))
        .toList(growable: false);
  }

  static String _formatStatus(String value) {
    final text = value.trim();

    if (text.isEmpty) {
      return 'Status unavailable';
    }

    return text
        .replaceAll('_', ' ')
        .split(' ')
        .map((word) {
          if (word.isEmpty) {
            return '';
          }

          return '${word[0].toUpperCase()}${word.substring(1)}';
        })
        .join(' ');
  }

  static int _parseInt(dynamic value) {
    if (value is int) {
      return value;
    }

    return int.tryParse(value?.toString() ?? '') ?? 0;
  }

  static int? _parseNullableInt(dynamic value) {
    if (value == null) {
      return null;
    }

    if (value is int) {
      return value;
    }

    return int.tryParse(value.toString());
  }

  static double _parseDouble(dynamic value) {
    if (value is num) {
      return value.toDouble();
    }

    return double.tryParse(value?.toString() ?? '') ?? 0;
  }

  static String? _parseNullableString(dynamic value) {
    if (value == null) {
      return null;
    }

    final text = value.toString().trim();

    return text.isEmpty ? null : text;
  }

  bool get canRespondToReschedule {
    return effectiveBookingStatus == 'reschedule_proposed' ||
        effectiveBookingStatus == 'partner_reschedule';
  }

  List<ViewingEvent> get sortedEvents {
    final result = List<ViewingEvent>.from(events);

    result.sort((first, second) {
      final firstDate = first.createdDateTime;
      final secondDate = second.createdDateTime;

      if (firstDate == null && secondDate == null) {
        return first.id.compareTo(second.id);
      }

      if (firstDate == null) {
        return 1;
      }

      if (secondDate == null) {
        return -1;
      }

      return firstDate.compareTo(secondDate);
    });

    return result;
  }

  bool get hasTimelineEvents {
    return events.isNotEmpty;
  }
}

class ViewingEvent {
  const ViewingEvent({
    required this.id,
    required this.eventType,
    required this.eventLabel,
    required this.actorId,
    required this.actorName,
    required this.notes,
    required this.metadata,
    required this.createdAt,
  });

  final int id;
  final String eventType;
  final String eventLabel;

  final int? actorId;
  final String actorName;

  final String notes;
  final Map<String, dynamic> metadata;

  final String createdAt;

  factory ViewingEvent.fromJson(Map<String, dynamic> json) {
    return ViewingEvent(
      id: _parseInt(json['id']),
      eventType: json['event_type']?.toString() ?? '',
      eventLabel: json['event_label']?.toString() ?? '',
      actorId: _parseNullableInt(json['actor']),
      actorName: json['actor_name']?.toString() ?? '',
      notes: json['notes']?.toString() ?? '',
      metadata: _parseMetadata(json['metadata']),
      createdAt: json['created_at']?.toString() ?? '',
    );
  }

  String get displayLabel {
    if (eventLabel.trim().isNotEmpty) {
      return eventLabel.trim();
    }

    final value = eventType.trim();

    if (value.isEmpty) {
      return 'Viewing update';
    }

    return value
        .replaceAll('_', ' ')
        .split(' ')
        .where((word) => word.isNotEmpty)
        .map(
          (word) =>
              '${word[0].toUpperCase()}'
              '${word.substring(1).toLowerCase()}',
        )
        .join(' ');
  }

  DateTime? get createdDateTime {
    return DateTime.tryParse(createdAt)?.toLocal();
  }

  static int _parseInt(dynamic value) {
    if (value is int) {
      return value;
    }

    if (value is num) {
      return value.toInt();
    }

    return int.tryParse(value?.toString() ?? '') ?? 0;
  }

  static int? _parseNullableInt(dynamic value) {
    if (value == null) {
      return null;
    }

    if (value is int) {
      return value;
    }

    if (value is num) {
      return value.toInt();
    }

    return int.tryParse(value.toString());
  }

  static Map<String, dynamic> _parseMetadata(dynamic value) {
    if (value is Map<String, dynamic>) {
      return value;
    }

    if (value is Map) {
      return Map<String, dynamic>.from(value);
    }

    return const <String, dynamic>{};
  }
}
