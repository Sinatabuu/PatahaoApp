class PartnerPropertyPhoto {
  const PartnerPropertyPhoto({
    required this.id,
    required this.imageUrl,
    required this.caption,
    required this.isCover,
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
  final int imageWidth;
  final int imageHeight;
  final int fileSize;
  final String qualityStatus;
  final int qualityScore;
  final List<String> qualityWarnings;

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

    return PartnerPropertyPhoto(
      id: _parseInt(json['id']),
      imageUrl: rawImageUrl?.toString().trim() ?? '',
      caption: json['caption']?.toString().trim() ?? '',
      isCover: json['is_cover'] == true,
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
