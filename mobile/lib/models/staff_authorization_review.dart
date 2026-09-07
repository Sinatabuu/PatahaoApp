class StaffAuthorizationReview {
  const StaffAuthorizationReview({
    required this.id,
    required this.mandateNumber,
    required this.propertyId,
    required this.propertyTitle,
    required this.partnerName,
    required this.status,
    required this.statusDisplay,
    required this.authorizationMethodDisplay,
    required this.submittedAt,
    required this.owner,
    required this.commission,
  });

  final int id;
  final String mandateNumber;
  final int propertyId;
  final String propertyTitle;
  final String partnerName;
  final String status;
  final String statusDisplay;
  final String authorizationMethodDisplay;
  final DateTime? submittedAt;
  final Map<String, dynamic> owner;
  final Map<String, dynamic> commission;

  factory StaffAuthorizationReview.fromJson(
    Map<String, dynamic> json,
  ) {
    return StaffAuthorizationReview(
      id: _toInt(json['id']),
      mandateNumber: json['mandate_number']?.toString() ?? '',
      propertyId: _toInt(json['property']),
      propertyTitle: json['property_title']?.toString() ?? 'Property',
      partnerName: json['partner_name']?.toString() ?? 'Partner',
      status: json['status']?.toString() ?? '',
      statusDisplay: json['status_display']?.toString() ?? '',
      authorizationMethodDisplay:
          json['authorization_method_display']?.toString() ?? '',
      submittedAt: DateTime.tryParse(
        json['submitted_at']?.toString() ?? '',
      ),
      owner: _toMap(json['owner_detail']),
      commission: _toMap(json['commission_detail']),
    );
  }

  String get ownerName =>
      owner['legal_name']?.toString().trim() ?? '';

  String get ownerPhone =>
      owner['phone_number']?.toString().trim() ?? '';

  String get agreementNumber =>
      commission['agreement_number']?.toString().trim() ?? '';

  String get commissionMethod =>
      commission['commission_method_display']?.toString().trim() ?? '';

  String get commissionBasis =>
      commission['commission_basis_display']?.toString().trim() ?? '';

  String get expectedCommission =>
      commission['expected_total_commission']?.toString().trim() ?? '';

  String get currency =>
      commission['currency']?.toString().trim() ?? 'KES';

  static int _toInt(dynamic value) {
    if (value is int) {
      return value;
    }

    if (value is num) {
      return value.toInt();
    }

    return int.tryParse(value?.toString() ?? '') ?? 0;
  }

  static Map<String, dynamic> _toMap(dynamic value) {
    if (value is Map) {
      return Map<String, dynamic>.from(value);
    }

    return <String, dynamic>{};
  }
}

class StaffAuthorizationEvidence {
  const StaffAuthorizationEvidence({
    required this.label,
    required this.filename,
    required this.status,
    required this.fileSize,
    required this.fileHash,
  });

  final String label;
  final String filename;
  final String status;
  final int fileSize;
  final String fileHash;

  factory StaffAuthorizationEvidence.fromStep(
    Map<String, dynamic> step,
  ) {
    final rawDocument = step['document'];
    final document = rawDocument is Map
        ? Map<String, dynamic>.from(rawDocument)
        : <String, dynamic>{};

    return StaffAuthorizationEvidence(
      label: step['label']?.toString() ?? 'Evidence',
      filename:
          document['original_filename']?.toString() ?? 'Not provided',
      status:
          document['status_display']?.toString() ?? 'Not provided',
      fileSize: StaffAuthorizationReview._toInt(
        document['file_size'],
      ),
      fileHash: document['file_hash']?.toString() ?? '',
    );
  }

  String get fileSizeLabel {
    if (fileSize <= 0) {
      return '';
    }

    if (fileSize < 1024) {
      return '$fileSize B';
    }

    final kilobytes = fileSize / 1024;

    if (kilobytes < 1024) {
      return '${kilobytes.toStringAsFixed(1)} KB';
    }

    final megabytes = kilobytes / 1024;
    return '${megabytes.toStringAsFixed(1)} MB';
  }

  String get shortHash {
    if (fileHash.length <= 12) {
      return fileHash;
    }

    return fileHash.substring(0, 12);
  }
}
