class ViewingCreditBalance {
  const ViewingCreditBalance({
    required this.currency,
    required this.availableAmount,
    required this.credits,
  });

  final String currency;
  final double availableAmount;
  final List<ViewingCredit> credits;

  bool get hasCredit => availableAmount > 0;

  factory ViewingCreditBalance.fromJson(Map<String, dynamic> json) {
    final rawCredits = json['credits'];

    return ViewingCreditBalance(
      currency: json['currency']?.toString() ?? 'KES',
      availableAmount: _toDouble(json['available_amount']),
      credits: rawCredits is List
          ? rawCredits
                .whereType<Map>()
                .map(
                  (item) =>
                      ViewingCredit.fromJson(Map<String, dynamic>.from(item)),
                )
                .toList(growable: false)
          : const <ViewingCredit>[],
    );
  }
}

class ViewingCredit {
  const ViewingCredit({
    required this.id,
    required this.reference,
    required this.propertyTitle,
    required this.amount,
    required this.remainingAmount,
    required this.currency,
    required this.status,
    required this.issuedAt,
  });

  final int id;
  final String reference;
  final String propertyTitle;
  final double amount;
  final double remainingAmount;
  final String currency;
  final String status;
  final String issuedAt;

  factory ViewingCredit.fromJson(Map<String, dynamic> json) {
    return ViewingCredit(
      id: _toInt(json['id']),
      reference: json['credit_reference']?.toString() ?? '',
      propertyTitle: json['property_title']?.toString() ?? 'Property',
      amount: _toDouble(json['amount']),
      remainingAmount: _toDouble(json['remaining_amount']),
      currency: json['currency']?.toString() ?? 'KES',
      status: json['status']?.toString() ?? '',
      issuedAt: json['issued_at']?.toString() ?? '',
    );
  }
}

int _toInt(dynamic value) {
  if (value is int) {
    return value;
  }

  if (value is num) {
    return value.toInt();
  }

  return int.tryParse(value?.toString() ?? '') ?? 0;
}

double _toDouble(dynamic value) {
  if (value is num) {
    return value.toDouble();
  }

  return double.tryParse(value?.toString() ?? '') ?? 0;
}
