import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/models/property.dart';

void main() {
  group('PropertyPhoto optimized image URLs', () {
    test('reads original and optimized image URLs', () {
      final photo = PropertyPhoto.fromJson({
        'id': 1,
        'image': 'property_photos/original.jpg',
        'image_url': 'https://example.com/original.jpg',
        'thumbnail_url': 'https://example.com/thumbnail.jpg',
        'listing_image_url': 'https://example.com/listing.jpg',
        'caption': 'Living room',
        'is_cover': true,
      });

      expect(photo.image, 'https://example.com/original.jpg');
      expect(photo.thumbnailUrl, 'https://example.com/thumbnail.jpg');
      expect(photo.listingImageUrl, 'https://example.com/listing.jpg');
      expect(photo.isCover, isTrue);
    });

    test('supports older photographs without optimized images', () {
      final photo = PropertyPhoto.fromJson({
        'id': 2,
        'image_url': 'https://example.com/legacy.jpg',
        'thumbnail_url': null,
        'listing_image_url': null,
        'is_cover': true,
      });

      expect(photo.image, 'https://example.com/legacy.jpg');
      expect(photo.thumbnailUrl, isEmpty);
      expect(photo.listingImageUrl, isEmpty);
    });

    test('preserves original image fallback', () {
      final photo = PropertyPhoto.fromJson({
        'id': 3,
        'image': 'property_photos/fallback.jpg',
      });

      expect(photo.image, 'property_photos/fallback.jpg');
      expect(photo.thumbnailUrl, isEmpty);
      expect(photo.listingImageUrl, isEmpty);
    });
  });
}
