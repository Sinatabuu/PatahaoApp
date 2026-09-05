import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/models/partner_property_photo.dart';
import 'package:mobile/models/partner_property_photo_coverage.dart';

void main() {
  group('Partner property photo coverage', () {
    test('residential requirements follow room counts', () {
      final required = PartnerPropertyPhotoCoverage.requiredTypesFor(
        propertyType: 'apartment',
        bedrooms: 2,
        bathrooms: 1,
      );

      expect(
        required,
        [
          PartnerPropertyPhotoType.exterior,
          PartnerPropertyPhotoType.livingArea,
          PartnerPropertyPhotoType.kitchen,
          PartnerPropertyPhotoType.bedroom,
          PartnerPropertyPhotoType.bathroom,
        ],
      );
    });

    test('land uses site-specific required views', () {
      final required = PartnerPropertyPhotoCoverage.requiredTypesFor(
        propertyType: 'land',
        bedrooms: 0,
        bathrooms: 0,
      );

      expect(
        required,
        [
          PartnerPropertyPhotoType.siteOverview,
          PartnerPropertyPhotoType.boundary,
          PartnerPropertyPhotoType.access,
        ],
      );
    });

    test('commercial property requires the main space', () {
      final required = PartnerPropertyPhotoCoverage.requiredTypesFor(
        propertyType: 'warehouse',
        bedrooms: 0,
        bathrooms: 1,
      );

      expect(
        required,
        [
          PartnerPropertyPhotoType.exterior,
          PartnerPropertyPhotoType.mainSpace,
          PartnerPropertyPhotoType.access,
          PartnerPropertyPhotoType.bathroom,
        ],
      );
    });

    test('five categorized photos and a cover complete coverage', () {
      final photoTypes = [
        PartnerPropertyPhotoType.exterior,
        PartnerPropertyPhotoType.livingArea,
        PartnerPropertyPhotoType.kitchen,
        PartnerPropertyPhotoType.bedroom,
        PartnerPropertyPhotoType.bathroom,
      ];

      final photos = [
        for (var index = 0; index < photoTypes.length; index++)
          PartnerPropertyPhoto(
            id: index + 1,
            imageUrl: '/photo-$index.jpg',
            caption: '',
            isCover: index == 0,
            photoType: photoTypes[index],
          ),
      ];

      final coverage = PartnerPropertyPhotoCoverage.evaluate(
        propertyType: 'house',
        bedrooms: 3,
        bathrooms: 2,
        photos: photos,
      );

      expect(coverage.photoCount, 5);
      expect(coverage.hasMinimumPhotos, isTrue);
      expect(coverage.hasCover, isTrue);
      expect(coverage.missingPhotoTypes, isEmpty);
      expect(coverage.complete, isTrue);
    });

    test('legacy Other photos do not satisfy required views', () {
      final photos = [
        for (var index = 0; index < 5; index++)
          PartnerPropertyPhoto(
            id: index + 1,
            imageUrl: '/legacy-$index.jpg',
            caption: '',
            isCover: index == 0,
          ),
      ];

      final coverage = PartnerPropertyPhotoCoverage.evaluate(
        propertyType: 'land',
        bedrooms: 0,
        bathrooms: 0,
        photos: photos,
      );

      expect(coverage.hasMinimumPhotos, isTrue);
      expect(coverage.hasCover, isTrue);
      expect(
        coverage.missingPhotoLabels,
        [
          'Site overview',
          'Boundary',
          'Access or entrance',
        ],
      );
      expect(coverage.complete, isFalse);
    });
  });
}
