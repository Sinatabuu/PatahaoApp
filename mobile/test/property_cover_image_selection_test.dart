import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/models/property.dart';

void main() {
  Property makeProperty({
    required List<Map<String, dynamic>> photos,
    List<Map<String, dynamic>> videos = const [],
  }) {
    return Property.fromJson({
      'id': 1,
      'title': 'New Era',
      'photos': photos,
      'videos': videos,
    });
  }

  final optimizedPhoto = {
    'id': 6,
    'image_url': 'https://example.com/original.jpg',
    'thumbnail_url': 'https://example.com/360.jpg',
    'listing_image_url': 'https://example.com/900.jpg',
    'is_cover': true,
  };

  test('small cards prefer 360px thumbnails', () {
    final property = makeProperty(photos: [optimizedPhoto]);

    expect(
      property.coverMediaUrlForWidth(360),
      'https://example.com/360.jpg',
    );
  });

  test('large cards prefer 900px listing images', () {
    final property = makeProperty(photos: [optimizedPhoto]);

    expect(
      property.coverMediaUrlForWidth(900),
      'https://example.com/900.jpg',
    );
  });

  test('legacy photographs fall back to original', () {
    final property = makeProperty(photos: [
      {
        'id': 7,
        'image_url': 'https://example.com/legacy.jpg',
        'is_cover': true,
      },
    ]);

    expect(
      property.coverMediaUrlForWidth(360),
      'https://example.com/legacy.jpg',
    );
  });

  test('video thumbnails retain priority', () {
    final property = makeProperty(
      photos: [optimizedPhoto],
      videos: [
        {
          'id': 3,
          'thumbnail_url': 'https://example.com/video.jpg',
          'is_featured': true,
        },
      ],
    );

    expect(
      property.coverMediaUrlForWidth(360),
      'https://example.com/video.jpg',
    );
  });
}
