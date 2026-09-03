import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/models/property.dart';

void main() {
  group('Property success broadcast', () {
    test('parses an active sold broadcast', () {
      final property = Property.fromJson({
        'id': 42,
        'title': 'Kwetu View',
        'property_type': 'house',
        'listing_type': 'sale',
        'price': '5000000.00',
        'county': 'Nairobi',
        'town': 'Roysambu',
        'estate': 'Roysambu',
        'bedrooms': 3,
        'bathrooms': 2,
        'description': 'Completed property transaction.',
        'status': 'sold',
        'trust_badge': 'gold',
        'is_success_broadcast_active': true,
        'success_badge': 'Sold Through Pata Hao',
        'transaction_completed_at': '2026-09-03T12:00:00Z',
        'success_broadcast_until': '2026-10-03T12:00:00Z',
        'photos': <dynamic>[],
        'videos': <dynamic>[],
        'amenities': <dynamic>[],
      });

      expect(property.isCompletedTransaction, isTrue);
      expect(property.isSuccessBroadcastActive, isTrue);
      expect(property.successDisplayLabel, 'Sold Through Pata Hao');
      expect(
        property.transactionCompletedAt,
        DateTime.parse('2026-09-03T12:00:00Z'),
      );
      expect(
        property.successBroadcastUntil,
        DateTime.parse('2026-10-03T12:00:00Z'),
      );

      final favoriteCopy = property.copyWith(isFavorite: true);

      expect(favoriteCopy.isSuccessBroadcastActive, isTrue);
      expect(favoriteCopy.successDisplayLabel, 'Sold Through Pata Hao');
    });

    test('provides a safe rented fallback label', () {
      final property = Property.fromJson({
        'id': 43,
        'title': 'Completed Rental',
        'property_type': 'apartment',
        'listing_type': 'rent',
        'price': '30000.00',
        'county': 'Nairobi',
        'town': 'Roysambu',
        'estate': '',
        'bedrooms': 2,
        'bathrooms': 1,
        'description': 'Completed rental transaction.',
        'status': 'rented',
        'is_success_broadcast_active': true,
        'success_badge': '',
        'photos': <dynamic>[],
        'videos': <dynamic>[],
        'amenities': <dynamic>[],
      });

      expect(property.isCompletedTransaction, isTrue);
      expect(property.successDisplayLabel, 'Rented Through Pata Hao');
    });
  });
}
