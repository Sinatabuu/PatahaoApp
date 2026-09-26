class Payment {
  const Payment({
    required this.id,
    required this.viewingId,
    required this.payerId,
    required this.amount,
    required this.creditAppliedAmount,
    required this.cashAmount,
    required this.currency,
    required this.phoneNumber,
    required this.paymentMethod,
    required this.purpose,
    required this.status,
    required this.paymentReference,
    required this.receiptNumber,
    required this.providerTransactionId,
    required this.providerReceiptNumber,
    required this.failureReason,
    required this.paidAt,
    required this.createdAt,
    required this.updatedAt,
    required this.creditRedemptions,
    this.refundReference = '',
    this.refundNotes = '',
    this.refundedAt = '',
    this.refundedBy,
  });

  final int id;
  final int viewingId;
  final int payerId;
  final double amount;
  final double creditAppliedAmount;
  final double cashAmount;
  final String currency;
  final String phoneNumber;
  final String paymentMethod;
  final String purpose;
  final String status;
  final String paymentReference;

  /// Pata Hao's official customer-facing receipt.
  final String receiptNumber;

  /// Provider identifiers such as M-Pesa references.
  final String providerTransactionId;
  final String providerReceiptNumber;

  final String failureReason;

  /// The confirmed payment timestamp returned by Django.
  final String paidAt;

  /// Evidence recorded after an external refund has completed.
  final String refundReference;
  final String refundNotes;
  final String refundedAt;
  final int? refundedBy;

  final String createdAt;
  final String updatedAt;
  final List<PaymentCreditRedemption> creditRedemptions;

  factory Payment.fromJson(Map<String, dynamic> json) {
    final amount = _parseDouble(json['amount']);
    final creditAppliedAmount = _parseDouble(json['credit_applied_amount']);
    final cashAmount = json.containsKey('cash_amount')
        ? _parseDouble(json['cash_amount'])
        : amount - creditAppliedAmount;

    return Payment(
      id: _parseInt(json['id']),
      viewingId: _parseInt(json['viewing']),
      payerId: _parseInt(json['payer']),
      amount: amount,
      creditAppliedAmount: creditAppliedAmount,
      cashAmount: cashAmount,
      currency: json['currency']?.toString() ?? 'KES',
      phoneNumber: json['phone_number']?.toString() ?? '',
      paymentMethod:
          (json['provider'] ?? json['payment_method'])?.toString() ??
          'mobile_money',
      purpose: json['purpose']?.toString() ?? 'viewing_fee',
      status: json['status']?.toString() ?? 'pending',
      paymentReference: json['payment_reference']?.toString() ?? '',
      receiptNumber: json['receipt_number']?.toString() ?? '',
      providerTransactionId: json['provider_transaction_id']?.toString() ?? '',
      providerReceiptNumber: json['provider_receipt_number']?.toString() ?? '',
      failureReason: json['failure_reason']?.toString() ?? '',
      paidAt: json['paid_at']?.toString() ?? '',
      createdAt: json['created_at']?.toString() ?? '',
      updatedAt: json['updated_at']?.toString() ?? '',
      creditRedemptions: _parseCreditRedemptions(json['credit_redemptions']),
      refundReference: json['refund_reference']?.toString() ?? '',
      refundNotes: json['refund_notes']?.toString() ?? '',
      refundedAt: json['refunded_at']?.toString() ?? '',
      refundedBy: _parseNullableInt(json['refunded_by']),
    );
  }

  bool get isSuccessful {
    final normalizedStatus = status.trim().toLowerCase();

    return normalizedStatus == 'successful' ||
        normalizedStatus == 'success' ||
        normalizedStatus == 'paid' ||
        normalizedStatus == 'completed';
  }

  bool get isRefunded {
    return status.trim().toLowerCase() == 'refunded';
  }

  bool get usedViewingCredit => creditAppliedAmount > 0;

  bool get fullyCoveredByCredit => usedViewingCredit && cashAmount <= 0;

  bool get hasReceipt {
    return isSuccessful || isRefunded;
  }

  String get displayReceiptNumber {
    if (receiptNumber.trim().isNotEmpty) {
      return receiptNumber.trim();
    }

    if (providerReceiptNumber.trim().isNotEmpty) {
      return providerReceiptNumber.trim();
    }

    if (paymentReference.trim().isNotEmpty) {
      return paymentReference.trim();
    }

    return 'Payment #$id';
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

  static double _parseDouble(dynamic value) {
    if (value is num) {
      return value.toDouble();
    }

    return double.tryParse(value?.toString() ?? '') ?? 0;
  }

  static List<PaymentCreditRedemption> _parseCreditRedemptions(dynamic value) {
    if (value is! List) {
      return const <PaymentCreditRedemption>[];
    }

    return value
        .whereType<Map>()
        .map(
          (item) =>
              PaymentCreditRedemption.fromJson(Map<String, dynamic>.from(item)),
        )
        .toList(growable: false);
  }
}

class PaymentCreditRedemption {
  const PaymentCreditRedemption({
    required this.reference,
    required this.creditReference,
    required this.amount,
  });

  final String reference;
  final String creditReference;
  final double amount;

  factory PaymentCreditRedemption.fromJson(Map<String, dynamic> json) {
    return PaymentCreditRedemption(
      reference: json['reference']?.toString() ?? '',
      creditReference: json['credit_reference']?.toString() ?? '',
      amount: Payment._parseDouble(json['amount']),
    );
  }
}
