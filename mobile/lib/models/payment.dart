class Payment {
  const Payment({
    required this.id,
    required this.viewingId,
    required this.payerId,
    required this.amount,
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
  });

  final int id;
  final int viewingId;
  final int payerId;
  final double amount;
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

  final String createdAt;
  final String updatedAt;

  factory Payment.fromJson(Map<String, dynamic> json) {
    return Payment(
      id: _parseInt(json['id']),
      viewingId: _parseInt(json['viewing']),
      payerId: _parseInt(json['payer']),
      amount: _parseDouble(json['amount']),
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
    );
  }

  bool get isSuccessful {
    final normalizedStatus = status.trim().toLowerCase();

    return normalizedStatus == 'successful' ||
        normalizedStatus == 'success' ||
        normalizedStatus == 'paid' ||
        normalizedStatus == 'completed';
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

  static double _parseDouble(dynamic value) {
    if (value is num) {
      return value.toDouble();
    }

    return double.tryParse(value?.toString() ?? '') ?? 0;
  }
}
