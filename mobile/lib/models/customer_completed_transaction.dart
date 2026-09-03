class CustomerCompletedTransaction {
  final int id;
  final String dealNumber;
  final int propertyId;
  final String propertyTitle;
  final String dealType;
  final String partnerName;
  final String status;
  final String completedAt;
  final String closedAt;

  const CustomerCompletedTransaction({
    required this.id,
    required this.dealNumber,
    required this.propertyId,
    required this.propertyTitle,
    required this.dealType,
    required this.partnerName,
    required this.status,
    required this.completedAt,
    required this.closedAt,
  });

  factory CustomerCompletedTransaction.fromJson(Map<String, dynamic> json) {
    return CustomerCompletedTransaction(
      id: _toInt(json['id']),
      dealNumber: json['deal_number']?.toString() ?? '',
      propertyId: _toInt(json['property']),
      propertyTitle: json['property_title']?.toString() ?? 'Property',
      dealType: json['deal_type']?.toString() ?? '',
      partnerName: json['partner_name']?.toString() ?? '',
      status: json['status']?.toString() ?? '',
      completedAt: json['completed_at']?.toString() ?? '',
      closedAt: json['closed_at']?.toString() ?? '',
    );
  }

  bool get isSale => dealType.toLowerCase() == 'sale';

  String get dealTypeLabel => isSale ? 'Sale' : 'Rental';

  static int _toInt(dynamic value) {
    if (value is int) {
      return value;
    }

    return int.tryParse(value?.toString() ?? '') ?? 0;
  }
}
