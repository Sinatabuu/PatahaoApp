class PartnerDashboard {
  const PartnerDashboard({
    required this.partner,
    required this.summary,
    required this.properties,
    required this.viewingRequests,
    required this.todayViewings,
  });

  final PartnerDashboardProfile partner;
  final PartnerDashboardSummary summary;
  final List<PartnerDashboardProperty> properties;
  final List<PartnerDashboardViewing> viewingRequests;
  final List<PartnerDashboardViewing> todayViewings;

  factory PartnerDashboard.fromJson(Map<String, dynamic> json) {
    return PartnerDashboard(
      partner: PartnerDashboardProfile.fromJson(
        _asMap(json['partner']),
      ),
      summary: PartnerDashboardSummary.fromJson(
        _asMap(json['summary']),
      ),
      properties: _parseProperties(json['properties']),
      viewingRequests: _parseViewings(
        json['viewing_requests'],
      ),
      todayViewings: _parseViewings(
        json['today_viewings'],
      ),
    );
  }

  static List<PartnerDashboardProperty> _parseProperties(
    dynamic value,
  ) {
    if (value is! List) {
      return const <PartnerDashboardProperty>[];
    }

    return value
        .whereType<Map>()
        .map(
          (item) => PartnerDashboardProperty.fromJson(
            Map<String, dynamic>.from(item),
          ),
        )
        .toList();
  }

  static List<PartnerDashboardViewing> _parseViewings(
    dynamic value,
  ) {
    if (value is! List) {
      return const <PartnerDashboardViewing>[];
    }

    return value
        .whereType<Map>()
        .map(
          (item) => PartnerDashboardViewing.fromJson(
            Map<String, dynamic>.from(item),
          ),
        )
        .toList();
  }
}

class PartnerDashboardProfile {
  const PartnerDashboardProfile({
    required this.id,
    required this.name,
    required this.businessName,
    required this.displayName,
    required this.partnerType,
    required this.partnerCode,
    required this.profilePhoto,
    required this.bio,
    required this.county,
    required this.town,
    required this.serviceArea,
    required this.publicPhoneNumber,
    required this.verificationStatus,
    required this.isVerified,
    required this.commissionRate,
    required this.acceptsViewingRequests,
  });

  final int id;
  final String name;
  final String businessName;
  final String displayName;
  final String partnerType;
  final String partnerCode;
  final String? profilePhoto;
  final String bio;
  final String county;
  final String town;
  final String serviceArea;
  final String publicPhoneNumber;
  final String verificationStatus;
  final bool isVerified;
  final double commissionRate;
  final bool acceptsViewingRequests;

  factory PartnerDashboardProfile.fromJson(
    Map<String, dynamic> json,
  ) {
    return PartnerDashboardProfile(
      id: _asInt(json['id']),
      name: _asString(json['name']),
      businessName: _asString(json['business_name']),
      displayName: _asString(json['display_name']),
      partnerType: _asString(json['partner_type']),
      partnerCode: _asString(json['partner_code']),
      profilePhoto: _asNullableString(
        json['profile_photo'],
      ),
      bio: _asString(json['bio']),
      county: _asString(json['county']),
      town: _asString(json['town']),
      serviceArea: _asString(json['service_area']),
      publicPhoneNumber: _asString(
        json['public_phone_number'],
      ),
      verificationStatus: _asString(
        json['verification_status'],
      ),
      isVerified: _asBool(json['is_verified']),
      commissionRate: _asDouble(
        json['commission_rate'],
      ),
      acceptsViewingRequests: _asBool(
        json['accepts_viewing_requests'],
      ),
    );
  }

  String get effectiveName {
    if (name.trim().isNotEmpty) {
      return name.trim();
    }

    if (displayName.trim().isNotEmpty) {
      return displayName.trim();
    }

    if (businessName.trim().isNotEmpty) {
      return businessName.trim();
    }

    return 'Partner';
  }

  String get location {
    final parts = <String>[
      serviceArea,
      town,
      county,
    ].where((part) => part.trim().isNotEmpty).toList();

    return parts.join(', ');
  }

  String get friendlyVerificationStatus {
    return _formatStatus(verificationStatus);
  }
}

class PartnerDashboardSummary {
  const PartnerDashboardSummary({
    required this.activeProperties,
    required this.todayViewings,
    required this.pendingRequests,
    required this.confirmedViewings,
    required this.completedToday,
    required this.properties,
    required this.viewings,
    required this.viewingFeesProcessed,
    required this.currency,
  });

  final int activeProperties;
  final int todayViewings;
  final int pendingRequests;
  final int confirmedViewings;
  final int completedToday;

  final PartnerPropertySummary properties;
  final PartnerViewingSummary viewings;

  final double viewingFeesProcessed;
  final String currency;

  factory PartnerDashboardSummary.fromJson(
    Map<String, dynamic> json,
  ) {
    final properties = PartnerPropertySummary.fromJson(
      _asMap(json['properties']),
    );

    final viewings = PartnerViewingSummary.fromJson(
      _asMap(json['viewings']),
    );

    return PartnerDashboardSummary(
      activeProperties: _asIntWithFallback(
        json['active_properties'],
        properties.published,
      ),
      todayViewings: _asInt(
        json['today_viewings'],
      ),
      pendingRequests: _asIntWithFallback(
        json['pending_requests'],
        viewings.paidPendingPartner,
      ),
      confirmedViewings: _asIntWithFallback(
        json['confirmed_viewings'],
        viewings.confirmed,
      ),
      completedToday: _asInt(
        json['completed_today'],
      ),
      properties: properties,
      viewings: viewings,
      viewingFeesProcessed: _asDouble(
        json['viewing_fees_processed'],
      ),
      currency: _asString(json['currency']).trim().isEmpty
          ? 'KES'
          : _asString(json['currency']),
    );
  }

  String get formattedViewingFees {
    return '$currency ${viewingFeesProcessed.toStringAsFixed(2)}';
  }
}

class PartnerPropertySummary {
  const PartnerPropertySummary({
    required this.total,
    required this.published,
    required this.pending,
    required this.reserved,
    required this.rented,
    required this.sold,
  });

  final int total;
  final int published;
  final int pending;
  final int reserved;
  final int rented;
  final int sold;

  factory PartnerPropertySummary.fromJson(
    Map<String, dynamic> json,
  ) {
    return PartnerPropertySummary(
      total: _asInt(json['total']),
      published: _asInt(json['published']),
      pending: _asInt(json['pending']),
      reserved: _asInt(json['reserved']),
      rented: _asInt(json['rented']),
      sold: _asInt(json['sold']),
    );
  }
}

class PartnerViewingSummary {
  const PartnerViewingSummary({
    required this.total,
    required this.pendingPayment,
    required this.paymentProcessing,
    required this.paidPendingPartner,
    required this.rescheduleProposed,
    required this.confirmed,
    required this.completed,
    required this.cancelled,
  });

  final int total;
  final int pendingPayment;
  final int paymentProcessing;
  final int paidPendingPartner;
  final int rescheduleProposed;
  final int confirmed;
  final int completed;
  final int cancelled;

  factory PartnerViewingSummary.fromJson(
    Map<String, dynamic> json,
  ) {
    return PartnerViewingSummary(
      total: _asInt(json['total']),
      pendingPayment: _asInt(
        json['pending_payment'],
      ),
      paymentProcessing: _asInt(
        json['payment_processing'],
      ),
      paidPendingPartner: _asInt(
        json['paid_pending_partner'],
      ),
      rescheduleProposed: _asInt(
        json['reschedule_proposed'],
      ),
      confirmed: _asInt(json['confirmed']),
      completed: _asInt(json['completed']),
      cancelled: _asInt(json['cancelled']),
    );
  }
}

class PartnerDashboardProperty {
  const PartnerDashboardProperty({
    required this.id,
    required this.title,
    required this.propertyType,
    required this.listingType,
    required this.county,
    required this.town,
    required this.estate,
    required this.status,
    required this.trustBadge,
    required this.createdAt,
    required this.updatedAt,
  });

  final int id;
  final String title;
  final String propertyType;
  final String listingType;
  final String county;
  final String town;
  final String estate;
  final String status;
  final String trustBadge;
  final String createdAt;
  final String updatedAt;

  factory PartnerDashboardProperty.fromJson(
    Map<String, dynamic> json,
  ) {
    return PartnerDashboardProperty(
      id: _asInt(json['id']),
      title: _asString(json['title']),
      propertyType: _asString(
        json['property_type'],
      ),
      listingType: _asString(
        json['listing_type'],
      ),
      county: _asString(json['county']),
      town: _asString(json['town']),
      estate: _asString(json['estate']),
      status: _asString(json['status']),
      trustBadge: _asString(json['trust_badge']),
      createdAt: _asString(json['created_at']),
      updatedAt: _asString(json['updated_at']),
    );
  }

  String get location {
    final parts = <String>[
      estate,
      town,
      county,
    ].where((part) => part.trim().isNotEmpty).toList();

    return parts.join(', ');
  }

  String get friendlyStatus {
    return _formatStatus(status);
  }

  String get friendlyPropertyType {
    return _formatStatus(propertyType);
  }

  String get friendlyListingType {
    return _formatStatus(listingType);
  }
}

class PartnerDashboardViewing {
  const PartnerDashboardViewing({
    required this.id,
    required this.customerId,
    required this.customerName,
    required this.customerEmail,
    required this.customerPhoneNumber,
    required this.propertyId,
    required this.propertyTitle,
    required this.listingType,
    required this.requestedDate,
    required this.requestedTime,
    required this.customerMessage,
    required this.feeAmount,
    required this.status,
    required this.bookingStatus,
    required this.operationalStatus,
    required this.paymentReference,
    required this.partnerResponseMessage,
    required this.dealId,
    required this.partnerOutcomeSubmitted,
    required this.completionNotes,
    required this.nextAction,
    required this.canOperateToday,
    required this.createdAt,
    required this.updatedAt,
    
    this.proposedDate,
    this.proposedTime,
    this.confirmedDate,
    this.confirmedTime,
    this.scheduledDate,
    this.scheduledTime,
    this.partnerRespondedAt,
    this.completedAt,
    this.partnerDepartedAt,
    this.partnerArrivedAt,
    this.viewingStartedAt,
  });

  final int id;

  final int customerId;
  final String customerName;
  final String customerEmail;
  final String customerPhoneNumber;

  final int propertyId;
  final String propertyTitle;
  final String listingType;
  final String requestedDate;
  final String requestedTime;
  final String customerMessage;

  final double feeAmount;

  final String status;
  final String bookingStatus;
  final String operationalStatus;

  final String paymentReference;
  final String partnerResponseMessage;
  final String completionNotes;

  final String? proposedDate;
  final String? proposedTime;

  final String? confirmedDate;
  final String? confirmedTime;

  final String? scheduledDate;
  final String? scheduledTime;

  final String? partnerRespondedAt;
  final String? completedAt;
  final String? partnerDepartedAt;
  final String? partnerArrivedAt;
  final String? viewingStartedAt;

  final String? nextAction;
  final bool canOperateToday;

  final String createdAt;
  final String updatedAt;

  final int? dealId;
  final bool partnerOutcomeSubmitted;
  

  factory PartnerDashboardViewing.fromJson(
    Map<String, dynamic> json,
  ) {
    return PartnerDashboardViewing(
      id: _asInt(json['id']),
      customerId: _asInt(json['customer']),
      customerName: _asString(
        json['customer_name'],
      ),
      customerEmail: _asString(
        json['customer_email'],
      ),
      customerPhoneNumber: _asString(
        json['customer_phone_number'],
      ),
      propertyId: _asInt(json['property']),
      propertyTitle: _asString(
        json['property_title'],
      ),
      listingType: _asString(
        json['listing_type'],
      ),
      requestedDate: _asString(
        json['requested_date'],
      ),
      requestedTime: _asString(
        json['requested_time'],
      ),
      customerMessage: _asString(
        json['customer_message'],
      ),
      feeAmount: _asDouble(json['fee_amount']),
      status: _asString(json['status']),
      bookingStatus: _asString(
        json['booking_status'],
      ).trim().isEmpty
          ? _asString(json['status'])
          : _asString(json['booking_status']),
      operationalStatus: _asString(
        json['operational_status'],
      ).trim().isEmpty
          ? 'idle'
          : _asString(json['operational_status']),
      paymentReference: _asString(
        json['payment_reference'],
      ),
      partnerResponseMessage: _asString(
        json['partner_response_message'],
      ),
      completionNotes: _asString(
        json['completion_notes'],
      ),
      proposedDate: _asNullableString(
        json['proposed_date'],
      ),
      dealId: json['deal_id'] == null
          ? null
          : _asInt(json['deal_id']),

      partnerOutcomeSubmitted:
          json['partner_outcome_submitted'] == true,
      proposedTime: _asNullableString(
        json['proposed_time'],
      ),
      confirmedDate: _asNullableString(
        json['confirmed_date'],
      ),
      confirmedTime: _asNullableString(
        json['confirmed_time'],
      ),
      scheduledDate: _asNullableString(
        json['scheduled_date'],
      ),
      scheduledTime: _asNullableString(
        json['scheduled_time'],
      ),
      partnerRespondedAt: _asNullableString(
        json['partner_responded_at'],
      ),
      completedAt: _asNullableString(
        json['completed_at'],
      ),
      partnerDepartedAt: _asNullableString(
        json['partner_departed_at'],
      ),
      partnerArrivedAt: _asNullableString(
        json['partner_arrived_at'],
      ),
      viewingStartedAt: _asNullableString(
        json['viewing_started_at'],
      ),
      nextAction: _asNullableString(
        json['next_action'],
      ),
      canOperateToday: _asBool(
        json['can_operate_today'],
      ),
      createdAt: _asString(json['created_at']),
      updatedAt: _asString(json['updated_at']),
    );
  }

  String get effectiveBookingStatus {
    if (bookingStatus.trim().isNotEmpty) {
      return bookingStatus;
    }

    return status;
  }

  String get effectiveDate {
    return scheduledDate ??
        confirmedDate ??
        proposedDate ??
        requestedDate;
  }

  String get effectiveTime {
    return scheduledTime ??
        confirmedTime ??
        proposedTime ??
        requestedTime;
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

      case 'reschedule_proposed':
      case 'partner_reschedule':
        return 'New schedule proposed';

      case 'confirmed':
        return 'Confirmed';

      case 'completed':
        return 'Completed';

      case 'cancelled':
        return 'Cancelled';

      case 'declined':
        return 'Declined';

      default:
        return _formatStatus(effectiveBookingStatus);
    }
  }

  String get friendlyOperationalStatus {
    switch (operationalStatus) {
      case 'idle':
        return 'Not started';

      case 'partner_en_route':
        return 'Partner en route';

      case 'partner_arrived':
        return 'Partner arrived';

      case 'viewing_in_progress':
        return 'Viewing in progress';

      case 'finished':
        return 'Completed';

      default:
        return _formatStatus(operationalStatus);
    }
  }

  String get formattedFee {
    return 'KES ${feeAmount.toStringAsFixed(2)}';
  }
}

Map<String, dynamic> _asMap(dynamic value) {
  if (value is Map<String, dynamic>) {
    return value;
  }

  if (value is Map) {
    return Map<String, dynamic>.from(value);
  }

  return <String, dynamic>{};
}

String _asString(dynamic value) {
  if (value == null) {
    return '';
  }

  return value.toString();
}

String? _asNullableString(dynamic value) {
  if (value == null) {
    return null;
  }

  final result = value.toString().trim();

  return result.isEmpty ? null : result;
}

int _asInt(dynamic value) {
  if (value is int) {
    return value;
  }

  if (value is num) {
    return value.toInt();
  }

  return int.tryParse(
        value?.toString() ?? '',
      ) ??
      0;
}

int _asIntWithFallback(
  dynamic value,
  int fallback,
) {
  if (value == null) {
    return fallback;
  }

  if (value is int) {
    return value;
  }

  if (value is num) {
    return value.toInt();
  }

  return int.tryParse(value.toString()) ?? fallback;
}

double _asDouble(dynamic value) {
  if (value is double) {
    return value;
  }

  if (value is num) {
    return value.toDouble();
  }

  return double.tryParse(
        value?.toString() ?? '',
      ) ??
      0;
}

bool _asBool(dynamic value) {
  if (value is bool) {
    return value;
  }

  final normalized = value
      ?.toString()
      .trim()
      .toLowerCase();

  return normalized == 'true' ||
      normalized == '1' ||
      normalized == 'yes';
}

String _formatStatus(String value) {
  final text = value.trim();

  if (text.isEmpty) {
    return 'Not available';
  }

  return text
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