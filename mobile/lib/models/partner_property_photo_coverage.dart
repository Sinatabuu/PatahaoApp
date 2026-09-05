import 'partner_property_photo.dart';

class PartnerPropertyPhotoCoverage {
  const PartnerPropertyPhotoCoverage({
    required this.photoCount,
    required this.minimumPhotoCount,
    required this.hasCover,
    required this.requiredPhotoTypes,
    required this.missingPhotoTypes,
  });

  static const int requiredMinimum = 5;

  final int photoCount;
  final int minimumPhotoCount;
  final bool hasCover;
  final List<String> requiredPhotoTypes;
  final List<String> missingPhotoTypes;

  bool get hasMinimumPhotos => photoCount >= minimumPhotoCount;

  bool get complete {
    return hasMinimumPhotos && hasCover && missingPhotoTypes.isEmpty;
  }

  List<String> get missingPhotoLabels {
    return missingPhotoTypes
        .map(PartnerPropertyPhotoType.labelFor)
        .toList(growable: false);
  }

  static List<String> requiredTypesFor({
    required String propertyType,
    required int bedrooms,
    required int bathrooms,
  }) {
    switch (propertyType) {
      case 'apartment':
      case 'house':
        return [
          PartnerPropertyPhotoType.exterior,
          PartnerPropertyPhotoType.livingArea,
          PartnerPropertyPhotoType.kitchen,
          if (bedrooms > 0) PartnerPropertyPhotoType.bedroom,
          if (bathrooms > 0) PartnerPropertyPhotoType.bathroom,
        ];

      case 'land':
        return const [
          PartnerPropertyPhotoType.siteOverview,
          PartnerPropertyPhotoType.boundary,
          PartnerPropertyPhotoType.access,
        ];

      case 'office':
      case 'shop':
      case 'warehouse':
        return [
          PartnerPropertyPhotoType.exterior,
          PartnerPropertyPhotoType.mainSpace,
          PartnerPropertyPhotoType.access,
          if (bathrooms > 0) PartnerPropertyPhotoType.bathroom,
        ];

      default:
        return const [
          PartnerPropertyPhotoType.exterior,
        ];
    }
  }

  factory PartnerPropertyPhotoCoverage.evaluate({
    required String propertyType,
    required int bedrooms,
    required int bathrooms,
    required List<PartnerPropertyPhoto> photos,
  }) {
    final requiredPhotoTypes = requiredTypesFor(
      propertyType: propertyType,
      bedrooms: bedrooms,
      bathrooms: bathrooms,
    );

    final presentTypes = photos.map((photo) => photo.photoType).toSet();

    final missingPhotoTypes = requiredPhotoTypes
        .where((photoType) => !presentTypes.contains(photoType))
        .toList(growable: false);

    return PartnerPropertyPhotoCoverage(
      photoCount: photos.length,
      minimumPhotoCount: requiredMinimum,
      hasCover: photos.any((photo) => photo.isCover),
      requiredPhotoTypes: List<String>.unmodifiable(requiredPhotoTypes),
      missingPhotoTypes: missingPhotoTypes,
    );
  }
}
