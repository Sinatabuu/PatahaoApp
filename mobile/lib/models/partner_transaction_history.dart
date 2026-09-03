class PartnerTransactionHistoryPage {
  const PartnerTransactionHistoryPage({
    required this.count,
    required this.page,
    required this.pageSize,
    required this.totalPages,
    required this.hasNext,
    required this.hasPrevious,
    required this.results,
  });

  final int count;
  final int page;
  final int pageSize;
  final int totalPages;
  final bool hasNext;
  final bool hasPrevious;

  final List<PartnerTransactionHistoryItem> results;

  factory PartnerTransactionHistoryPage.fromJson(Map<String, dynamic> json) {
    final results = <PartnerTransactionHistoryItem>[];

    final rawResults = json['results'];

    if (rawResults is List) {
      for (final item in rawResults) {
        if (item is Map) {
          results.add(
            PartnerTransactionHistoryItem.fromJson(
              Map<String, dynamic>.from(item),
            ),
          );
        }
      }
    }

    return PartnerTransactionHistoryPage(
      count: _asInt(json['count']),
      page: _asInt(json['page']),
      pageSize: _asInt(json['page_size']),
      totalPages: _asInt(json['total_pages']),
      hasNext: json['has_next'] == true,
      hasPrevious: json['has_previous'] == true,
      results: results,
    );
  }
}

class PartnerTransactionHistoryItem {
  const PartnerTransactionHistoryItem({
    required this.dealId,
    required this.dealNumber,
    required this.propertyId,
    required this.propertyTitle,
    required this.customerName,
    required this.dealType,
    required this.dealStatus,
    required this.completedAt,
    required this.closedAt,
    required this.settlementId,
    required this.settlementStatus,
    required this.currency,
    required this.myShare,
    required this.paidAmount,
    required this.outstandingAmount,
    required this.payments,
  });

  final int dealId;
  final String dealNumber;

  final int propertyId;
  final String propertyTitle;
  final String customerName;

  final String dealType;
  final String dealStatus;

  final String completedAt;
  final String closedAt;

  final int settlementId;
  final String settlementStatus;

  final String currency;

  final double myShare;
  final double paidAmount;
  final double outstandingAmount;

  final List<PartnerTransactionHistoryPayment> payments;

  factory PartnerTransactionHistoryItem.fromJson(Map<String, dynamic> json) {
    final payments = <PartnerTransactionHistoryPayment>[];

    final rawPayments = json['payments'];

    if (rawPayments is List) {
      for (final item in rawPayments) {
        if (item is Map) {
          payments.add(
            PartnerTransactionHistoryPayment.fromJson(
              Map<String, dynamic>.from(item),
            ),
          );
        }
      }
    }

    return PartnerTransactionHistoryItem(
      dealId: _asInt(json['deal_id']),
      dealNumber: _asString(json['deal_number']),
      propertyId: _asInt(json['property_id']),
      propertyTitle: _asString(json['property_title']),
      customerName: _asString(json['customer_name']),
      dealType: _asString(json['deal_type']),
      dealStatus: _asString(json['deal_status']),
      completedAt: _asString(json['completed_at']),
      closedAt: _asString(json['closed_at']),
      settlementId: _asInt(json['settlement_id']),
      settlementStatus: _asString(json['settlement_status']),
      currency: _asString(json['currency']).isEmpty
          ? 'KES'
          : _asString(json['currency']),
      myShare: _asDouble(json['my_share']),
      paidAmount: _asDouble(json['paid_amount']),
      outstandingAmount: _asDouble(json['outstanding_amount']),
      payments: payments,
    );
  }
}

class PartnerTransactionHistoryPayment {
  const PartnerTransactionHistoryPayment({
    required this.id,
    required this.amount,
    required this.currency,
    required this.paymentMethod,
    required this.paymentReference,
    required this.paidAt,
  });

  final int id;
  final double amount;
  final String currency;
  final String paymentMethod;
  final String paymentReference;
  final String paidAt;

  factory PartnerTransactionHistoryPayment.fromJson(Map<String, dynamic> json) {
    return PartnerTransactionHistoryPayment(
      id: _asInt(json['id']),
      amount: _asDouble(json['amount']),
      currency: _asString(json['currency']),
      paymentMethod: _asString(json['payment_method']),
      paymentReference: _asString(json['payment_reference']),
      paidAt: _asString(json['paid_at']),
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
