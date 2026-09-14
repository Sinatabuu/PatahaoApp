import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/services/property_service.dart';

Map<String, dynamic> propertyJson({
  required int id,
  String status = 'published',
  bool success = false,
}) {
  return {
    'id': id,
    'title': 'Property $id',
    'property_type': 'apartment',
    'listing_type': 'rent',
    'price': '25000.00',
    'county': 'Nairobi',
    'town': 'Roysambu',
    'estate': 'Roysambu',
    'bedrooms': 2,
    'bathrooms': 1,
    'status': status,
    'trust_badge': 'none',
    'is_success_broadcast_active': success,
    'photos': <dynamic>[],
    'videos': <dynamic>[],
  };
}

void main() {
  group('PropertyFeedPage', () {
    test('parses paginated homes and compact successes', () {
      final feed = PropertyFeedPage.fromJson({
        'count': 41,
        'next': 'https://example.test/api/properties/?page=2',
        'previous': null,
        'results': List<dynamic>.generate(
          20,
          (index) => propertyJson(id: index + 1),
        ),
        'recent_successes': [
          propertyJson(id: 100, status: 'rented', success: true),
          propertyJson(id: 101, status: 'sold', success: true),
        ],
      });

      expect(feed.count, 41);
      expect(feed.hasNext, isTrue);
      expect(feed.properties, hasLength(20));
      expect(feed.recentSuccesses, hasLength(2));
      expect(feed.recentSuccesses.first.status, 'rented');
    });

    test('accepts the legacy list during backend rollout', () {
      final feed = PropertyFeedPage.fromJson([
        propertyJson(id: 1),
        propertyJson(id: 2, status: 'sold', success: true),
      ]);

      expect(feed.count, 1);
      expect(feed.hasNext, isFalse);
      expect(feed.properties.single.id, 1);
      expect(feed.recentSuccesses.single.id, 2);
    });

    test('rejects invalid paginated feed data', () {
      expect(
        () => PropertyFeedPage.fromJson({
          'count': 1,
          'results': 'not-a-list',
          'recent_successes': <dynamic>[],
        }),
        throwsFormatException,
      );
    });
  });
}
