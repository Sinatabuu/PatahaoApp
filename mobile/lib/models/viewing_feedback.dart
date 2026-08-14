class ViewingFeedback {
  const ViewingFeedback({
    required this.id,
    required this.viewingId,
    required this.customerId,
    required this.customerName,
    required this.attended,
    required this.propertyAccuracy,
    required this.propertyAccuracyLabel,
    required this.partnerRating,
    required this.propertyRating,
    required this.comments,
    required this.submittedAt,
    required this.updatedAt,
  });

  final int id;
  final int viewingId;

  final int customerId;
  final String customerName;

  final bool attended;

  final String propertyAccuracy;
  final String propertyAccuracyLabel;

  final int partnerRating;
  final int propertyRating;

  final String comments;

  final String submittedAt;
  final String updatedAt;

  factory ViewingFeedback.fromJson(Map<String, dynamic> json) {
    return ViewingFeedback(
      id: _parseInt(json['id']),
      viewingId: _parseInt(json['viewing']),
      customerId: _parseInt(json['customer']),
      customerName: json['customer_name']?.toString() ?? '',
      attended: _parseBool(json['attended']),
      propertyAccuracy: json['property_accuracy']?.toString() ?? '',
      propertyAccuracyLabel: json['property_accuracy_label']?.toString() ?? '',
      partnerRating: _parseInt(json['partner_rating']),
      propertyRating: _parseInt(json['property_rating']),
      comments: json['comments']?.toString() ?? '',
      submittedAt: json['submitted_at']?.toString() ?? '',
      updatedAt: json['updated_at']?.toString() ?? '',
    );
  }

  bool get propertyMatchedListing {
    return propertyAccuracy == 'yes';
  }

  String get friendlyPropertyAccuracy {
    if (propertyAccuracyLabel.trim().isNotEmpty) {
      return propertyAccuracyLabel.trim();
    }

    switch (propertyAccuracy) {
      case 'yes':
        return 'Yes';

      case 'partially':
        return 'Partially';

      case 'no':
        return 'No';

      default:
        return 'Not specified';
    }
  }

  DateTime? get submittedDateTime {
    return DateTime.tryParse(submittedAt)?.toLocal();
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

  static bool _parseBool(dynamic value) {
    if (value is bool) {
      return value;
    }

    final text = value?.toString().trim().toLowerCase();

    return text == 'true' || text == '1' || text == 'yes';
  }
}
