import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/models/partner_property_photo.dart';

void main() {
  group('PartnerPropertyPhoto quality metadata', () {
    test('parses an accepted quality result', () {
      final photo = PartnerPropertyPhoto.fromJson({
        'id': 7,
        'image_url': 'https://example.com/property.jpg',
        'caption': 'Front view',
        'is_cover': true,
        'photo_type': 'exterior',
        'image_width': 1600,
        'image_height': 900,
        'file_size': 2097152,
        'quality_status': 'accepted',
        'quality_score': 100,
        'quality_warnings': <dynamic>[],
      });

      expect(photo.photoType, PartnerPropertyPhotoType.exterior);
      expect(photo.photoTypeLabel, 'Exterior');
      expect(photo.hasQualityAnalysis, isTrue);
      expect(photo.qualityAccepted, isTrue);
      expect(photo.needsQualityReview, isFalse);
      expect(photo.qualityLabel, 'Quality checked');
      expect(photo.dimensionsLabel, '1600 × 900');
      expect(photo.fileSizeLabel, '2.0 MB');
      expect(photo.qualityWarnings, isEmpty);
    });

    test('parses advisory warnings without rejecting the photo', () {
      final photo = PartnerPropertyPhoto.fromJson({
        'id': '8',
        'image': '/media/property_photos/dark.jpg',
        'caption': '',
        'is_cover': false,
        'image_width': '1280',
        'image_height': '720',
        'file_size': 524288,
        'quality_status': 'needs_review',
        'quality_score': '60',
        'quality_warnings': <dynamic>[
          'The photo may be too dark.',
          'The photo may be blurry or lack detail.',
          '',
        ],
      });

      expect(photo.hasQualityAnalysis, isTrue);
      expect(photo.qualityAccepted, isFalse);
      expect(photo.needsQualityReview, isTrue);
      expect(photo.qualityLabel, 'Needs improvement');
      expect(photo.dimensionsLabel, '1280 × 720');
      expect(photo.fileSizeLabel, '512 KB');
      expect(photo.qualityWarnings, hasLength(2));
      expect(photo.qualityWarnings.first, 'The photo may be too dark.');
    });

    test('identifies legacy photos that were not analyzed', () {
      final photo = PartnerPropertyPhoto.fromJson({
        'id': 9,
        'image_url': '/media/property_photos/legacy.jpg',
        'caption': 'Older upload',
        'is_cover': false,
      });

      expect(photo.photoType, PartnerPropertyPhotoType.other);
      expect(photo.photoTypeLabel, 'Other');
      expect(photo.hasQualityAnalysis, isFalse);
      expect(photo.qualityAccepted, isFalse);
      expect(photo.needsQualityReview, isFalse);
      expect(photo.qualityLabel, 'Not yet checked');
      expect(photo.dimensionsLabel, isEmpty);
      expect(photo.fileSizeLabel, isEmpty);
      expect(photo.qualityWarnings, isEmpty);
    });
  });
}
