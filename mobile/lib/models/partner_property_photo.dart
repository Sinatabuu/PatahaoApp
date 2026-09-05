class PartnerPropertyPhotoTypeOption {
  const PartnerPropertyPhotoTypeOption({
    required this.value,
    required this.label,
  });

  final String value;
  final String label;
}

class PartnerPropertyPhotoType {
  static const exterior = 'exterior';
  static const livingArea = 'living_area';
  static const bedroom = 'bedroom';
  static const kitchen = 'kitchen';
  static const bathroom = 'bathroom';
  static const siteOverview = 'site_overview';
  static const boundary = 'boundary';
  static const access = 'access';
  static const mainSpace = 'main_space';
  static const amenity = 'amenity';
  static const other = 'other';

  static const options = <PartnerPropertyPhotoTypeOption>[
    PartnerPropertyPhotoTypeOption(value: exterior, label: 'Exterior'),
    PartnerPropertyPhotoTypeOption(
      value: livingArea,
      label: 'Living area',
    ),
    PartnerPropertyPhotoTypeOption(value: bedroom, label: 'Bedroom'),
    PartnerPropertyPhotoTypeOption(value: kitchen, label: 'Kitchen'),
    PartnerPropertyPhotoTypeOption(value: bathroom, label: 'Bathroom'),
    PartnerPropertyPhotoTypeOption(
      value: siteOverview,
      label: 'Site overview',
    ),
    PartnerPropertyPhotoTypeOption(value: boundary, label: 'Boundary'),
    PartnerPropertyPhotoTypeOption(
      value: access,
      label: 'Access or entrance',
    ),
    PartnerPropertyPhotoTypeOption(
      value: mainSpace,
      label: 'Main commercial space',
    ),
    PartnerPropertyPhotoTypeOption(value: amenity, label: 'Amenity'),
    PartnerPropertyPhotoTypeOption(value: other, label: 'Other'),
  ];

  static String labelFor(String value) {
    for (final option in options) {
      if (option.value == value) {
        return option.label;
      }
    }

    return 'Other';
  }
}

class PartnerPropertyPhoto {
  const PartnerPropertyPhoto({
    required this.id,
    required this.imageUrl,
    required this.caption,
    required this.isCover,
    this.photoType = PartnerPropertyPhotoType.other,
    this.imageWidth = 0,
    this.imageHeight = 0,
    this.fileSize = 0,
    this.qualityStatus = '',
    this.qualityScore = 0,
    this.qualityWarnings = const [],
  });

  final int id;
  final String imageUrl;
  final String caption;
  final bool isCover;
  final String photoType;
  final int imageWidth;
  final int imageHeight;
  final int fileSize;
  final String qualityStatus;
  final int qualityScore;
  final List<String> qualityWarnings;

  String get photoTypeLabel {
    return PartnerPropertyPhotoType.labelFor(photoType);
  }

  bool get hasQualityAnalysis {
    return imageWidth > 0 &&
        imageHeight > 0 &&
        fileSize > 0 &&
        qualityStatus.trim().isNotEmpty;
  }

  bool get needsQualityReview {
    return hasQualityAnalysis && qualityStatus == 'needs_review';
  }

  bool get qualityAccepted {
    return hasQualityAnalysis && qualityStatus == 'accepted';
  }

  String get qualityLabel {
    if (!hasQualityAnalysis) {
      return 'Not yet checked';
    }

    if (needsQualityReview) {
      return 'Needs improvement';
    }

    return 'Quality checked';
  }

  String get dimensionsLabel {
    if (imageWidth <= 0 || imageHeight <= 0) {
      return '';
    }

    return '$imageWidth × $imageHeight';
  }

  String get fileSizeLabel {
    if (fileSize <= 0) {
      return '';
    }

    if (fileSize >= 1024 * 1024) {
      final megabytes = fileSize / (1024 * 1024);
      return '${megabytes.toStringAsFixed(1)} MB';
    }

    final kilobytes = (fileSize / 1024).round();
    return '$kilobytes KB';
  }

  factory PartnerPropertyPhoto.fromJson(Map<String, dynamic> json) {
    final rawImageUrl = json['image_url'] ?? json['image'];
    final rawPhotoType = json['photo_type']?.toString().trim() ?? '';

    return PartnerPropertyPhoto(
      id: _parseInt(json['id']),
      imageUrl: rawImageUrl?.toString().trim() ?? '',
      caption: json['caption']?.toString().trim() ?? '',
      isCover: json['is_cover'] == true,
      photoType: rawPhotoType.isEmpty
          ? PartnerPropertyPhotoType.other
          : rawPhotoType,
      imageWidth: _parseInt(json['image_width']),
      imageHeight: _parseInt(json['image_height']),
      fileSize: _parseInt(json['file_size']),
      qualityStatus: json['quality_status']?.toString().trim() ?? '',
      qualityScore: _parseInt(json['quality_score']),
      qualityWarnings: _parseStringList(json['quality_warnings']),
    );
  }

  static List<String> _parseStringList(dynamic value) {
    if (value is! List) {
      return const [];
    }

    return value
        .map((item) => item?.toString().trim() ?? '')
        .where((item) => item.isNotEmpty)
        .toList(growable: false);
  }

  static int _parseInt(dynamic value) {
    if (value is int) {
      return value;
    }

    return int.tryParse(value?.toString() ?? '') ?? 0;
  }
}
