class Deal {
  final int id;

  final int customerId;
  final String customerName;

  final int partnerId;
  final String partnerName;

  final int propertyId;
  final String propertyTitle;
  final String listingType;

  final int viewingId;
  final String viewingStatus;
  final String requestedDate;
  final String requestedTime;

  final String monthlyRent;
  final String salePrice;
  final String commissionAmount;

  final String status;

  final bool customerConfirmed;
  final bool customerOutcomeSubmitted;
  final bool partnerConfirmed;
  final bool ownerConfirmed;

  const Deal({
    required this.id,
    required this.customerId,
    required this.customerName,
    required this.partnerId,
    required this.partnerName,
    required this.propertyId,
    required this.propertyTitle,
    required this.listingType,
    required this.viewingId,
    required this.viewingStatus,
    required this.requestedDate,
    required this.requestedTime,
    required this.monthlyRent,
    required this.salePrice,
    required this.commissionAmount,
    required this.status,
    required this.customerOutcomeSubmitted,
    required this.customerConfirmed,
    required this.partnerConfirmed,
    required this.ownerConfirmed,
  });

  factory Deal.fromJson(Map<String, dynamic> json) {
    return Deal(
      id: _toInt(json['id']),
      customerId: _toInt(json['customer']),
      customerName:
          json['customer_name']?.toString() ?? '',
      partnerId: _toInt(json['partner']),
      partnerName:
          json['partner_name']?.toString() ?? '',
      propertyId: _toInt(json['property']),
      propertyTitle:
          json['property_title']?.toString() ??
          'Property',
      listingType:
          json['listing_type']?.toString() ?? '',
      viewingId: _toInt(json['viewing']),
      viewingStatus:
          json['viewing_status']?.toString() ?? '',
      requestedDate:
          json['requested_date']?.toString() ?? '',
      requestedTime:
          json['requested_time']?.toString() ?? '',
      monthlyRent:
          json['monthly_rent']?.toString() ?? '',
      salePrice:
          json['sale_price']?.toString() ?? '',
      commissionAmount:
          json['commission_amount']?.toString() ?? '',
      status: json['status']?.toString() ?? '',
      customerConfirmed:
          json['customer_confirmed'] == true,
      customerOutcomeSubmitted:
          json['customer_outcome_submitted'] == true,    
      partnerConfirmed:
          json['partner_confirmed'] == true,
      ownerConfirmed:
          json['owner_confirmed'] == true,
    );
  }

  bool get isSale {
    return listingType.toLowerCase() == 'sale';
  }

  bool get isRental {
    return !isSale;
  }

  String get customerSuccessLabel {
    return isSale
        ? 'Yes, I bought this property'
        : 'Yes, I rented this property';
  }

  String get partnerSuccessLabel {
    return isSale
        ? 'Customer bought this property'
        : 'Customer rented this property';
  }

  static int _toInt(dynamic value) {
    if (value is int) {
      return value;
    }

    return int.tryParse(
          value?.toString() ?? '',
        ) ??
        0;
  }
}