class PartnerCommissionSummary {
  const PartnerCommissionSummary({
    required this.partnerId,
    required this.partnerName,
    required this.totalCommission,
    required this.paidToDate,
    required this.outstandingCommission,
    required this.pendingCommission,
    required this.approvedCommission,
    required this.partiallyPaidCommission,
    required this.paidCommission,
    required this.disputedCommission,
    required this.settlementCount,
  });

  final int partnerId;
  final String partnerName;

  final double totalCommission;
  final double paidToDate;
  final double outstandingCommission;

  final double pendingCommission;
  final double approvedCommission;
  final double partiallyPaidCommission;
  final double paidCommission;
  final double disputedCommission;

  final int settlementCount;

  factory PartnerCommissionSummary.fromJson(Map<String, dynamic> json) {
    return PartnerCommissionSummary(
      partnerId: _asInt(json['partner_id']),
      partnerName: _asString(json['partner_name']),
      totalCommission: _asDouble(json['total_commission']),
      paidToDate: _asDouble(json['paid_to_date']),
      outstandingCommission: _asDouble(json['outstanding_commission']),
      pendingCommission: _asDouble(json['pending_commission']),
      approvedCommission: _asDouble(json['approved_commission']),
      partiallyPaidCommission: _asDouble(json['partially_paid_commission']),
      paidCommission: _asDouble(json['paid_commission']),
      disputedCommission: _asDouble(json['disputed_commission']),
      settlementCount: _asInt(json['settlement_count']),
    );
  }
}

class PartnerCommissionSettlement {
  const PartnerCommissionSettlement({
    required this.id,
    required this.dealId,
    required this.dealStatus,
    required this.propertyTitle,
    required this.customerName,
    required this.agreementNumber,
    required this.grossCommissionAmount,
    required this.allocatedAmount,
    required this.unallocatedAmount,
    required this.myShare,
    required this.myPercentage,
    required this.myParticipantType,
    required this.myPaidAmount,
    required this.myOutstandingAmount,
    required this.myPaymentStatus,
    required this.status,
    required this.statusLabel,
    required this.payments,
    required this.approvedAt,
    required this.createdAt,
    required this.updatedAt,
  });

  final int id;
  final int dealId;

  final String dealStatus;
  final String propertyTitle;
  final String customerName;
  final String agreementNumber;

  final double grossCommissionAmount;
  final double allocatedAmount;
  final double unallocatedAmount;

  final double myShare;
  final double myPercentage;
  final String myParticipantType;

  final double myPaidAmount;
  final double myOutstandingAmount;
  final String myPaymentStatus;

  final String status;
  final String statusLabel;

  final List<PartnerCommissionPayment> payments;

  final String? approvedAt;
  final String createdAt;
  final String updatedAt;

  factory PartnerCommissionSettlement.fromJson(Map<String, dynamic> json) {
    return PartnerCommissionSettlement(
      id: _asInt(json['id']),
      dealId: _asInt(json['deal']),
      dealStatus: _asString(json['deal_status']),
      propertyTitle: _asString(json['property_title']),
      customerName: _asString(json['customer_name']),
      agreementNumber: _asString(json['agreement_number']),
      grossCommissionAmount: _asDouble(json['gross_commission_amount']),
      allocatedAmount: _asDouble(json['allocated_amount']),
      unallocatedAmount: _asDouble(json['unallocated_amount']),
      myShare: _asDouble(json['my_share']),
      myPercentage: _asDouble(json['my_percentage']),
      myParticipantType: _asString(json['my_participant_type']),
      myPaidAmount: _asDouble(json['my_paid_amount']),
      myOutstandingAmount: _asDouble(json['my_outstanding_amount']),
      myPaymentStatus: _asString(json['my_payment_status']),
      status: _asString(json['status']),
      statusLabel: _asString(json['status_label']),
      payments: _parsePayments(json['my_payments']),
      approvedAt: _asNullableString(json['approved_at']),
      createdAt: _asString(json['created_at']),
      updatedAt: _asString(json['updated_at']),
    );
  }

  static List<PartnerCommissionPayment> _parsePayments(dynamic value) {
    if (value is! List) {
      return const <PartnerCommissionPayment>[];
    }

    return value
        .whereType<Map>()
        .map(
          (item) => PartnerCommissionPayment.fromJson(
            Map<String, dynamic>.from(item),
          ),
        )
        .toList();
  }
}

class PartnerCommissionPayment {
  const PartnerCommissionPayment({
    required this.id,
    required this.amount,
    required this.currency,
    required this.paymentMethod,
    required this.paymentMethodLabel,
    required this.paymentReference,
    required this.paidAt,
    required this.notes,
    required this.createdAt,
  });

  final int id;
  final double amount;
  final String currency;

  final String paymentMethod;
  final String paymentMethodLabel;
  final String paymentReference;

  final String paidAt;
  final String notes;
  final String createdAt;

  factory PartnerCommissionPayment.fromJson(Map<String, dynamic> json) {
    return PartnerCommissionPayment(
      id: _asInt(json['id']),
      amount: _asDouble(json['amount']),
      currency: _asString(json['currency']),
      paymentMethod: _asString(json['payment_method']),
      paymentMethodLabel: _asString(json['payment_method_label']),
      paymentReference: _asString(json['payment_reference']),
      paidAt: _asString(json['paid_at']),
      notes: _asString(json['notes']),
      createdAt: _asString(json['created_at']),
    );
  }
}

int _asInt(dynamic value) {
  if (value is int) {
    return value;
  }

  if (value is num) {
    return value.toInt();
  }

  return int.tryParse(value?.toString() ?? '') ?? 0;
}

double _asDouble(dynamic value) {
  if (value is double) {
    return value;
  }

  if (value is num) {
    return value.toDouble();
  }

  return double.tryParse(value?.toString() ?? '') ?? 0.0;
}

String _asString(dynamic value) {
  return value?.toString().trim() ?? '';
}

String? _asNullableString(dynamic value) {
  final text = value?.toString().trim();

  if (text == null || text.isEmpty) {
    return null;
  }

  return text;
}
