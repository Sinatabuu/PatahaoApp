class Partner {
  final int id;
  final String name;
  final String businessName;
  final String? partnerCode;
  final String partnerType;
  final String? profilePhoto;
  final String? bio;
  final String county;
  final String town;
  final String? serviceArea;
  final bool isVerified;

  const Partner({
    required this.id,
    required this.name,
    required this.businessName,
    this.partnerCode,
    required this.partnerType,
    this.profilePhoto,
    this.bio,
    required this.county,
    required this.town,
    this.serviceArea,
    required this.isVerified,
  });

  factory Partner.fromJson(Map<String, dynamic> json) {
    final absolutePhoto = json['profile_photo_url']?.toString();

    final legacyPhoto = json['profile_photo']?.toString();

    return Partner(
      id: _toInt(json['id']),
      name: json['name']?.toString() ?? '',
      businessName: json['business_name']?.toString() ?? '',
      partnerCode: json['partner_code']?.toString(),
      partnerType: json['partner_type']?.toString() ?? '',
      profilePhoto: _firstNonEmpty(absolutePhoto, legacyPhoto),
      bio: json['bio']?.toString(),
      county: json['county']?.toString() ?? '',
      town: json['town']?.toString() ?? '',
      serviceArea: json['service_area']?.toString(),
      isVerified: json['is_verified'] == true,
    );
  }

  String get displayName {
    if (businessName.trim().isNotEmpty) {
      return businessName;
    }

    if (name.trim().isNotEmpty) {
      return name;
    }

    return 'Pata Hao Partner';
  }

  bool get hasPhoto {
    return profilePhoto != null && profilePhoto!.trim().isNotEmpty;
  }

  String get location {
    final parts = <String>[
      town,
      county,
    ].where((value) => value.trim().isNotEmpty).toList();

    return parts.join(', ');
  }

  String get verificationLabel {
    return isVerified ? 'Verified Partner' : 'Partner';
  }

  static int _toInt(dynamic value) {
    if (value is int) {
      return value;
    }

    return int.tryParse(value?.toString() ?? '') ?? 0;
  }

  static String? _firstNonEmpty(String? first, String? second) {
    if (first != null && first.trim().isNotEmpty) {
      return first;
    }

    if (second != null && second.trim().isNotEmpty) {
      return second;
    }

    return null;
  }
}

