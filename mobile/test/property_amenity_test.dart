import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/models/property.dart';

void main() {
  group('Property amenities', () {
    test('parses amenity marketing information', () {
      final amenity = PropertyAmenity.fromJson({
        'id': 7,
        'name': 'Reliable Water Supply',
        'slug': 'water-supply',
        'icon': 'water_drop',
        'display_order': 30,
      });

      expect(amenity.id, 7);
      expect(amenity.name, 'Reliable Water Supply');
      expect(amenity.slug, 'water-supply');
      expect(amenity.icon, 'water_drop');
      expect(amenity.displayOrder, 30);
    });

    test('uses safe values for incomplete legacy data', () {
      final amenity = PropertyAmenity.fromJson({
        'name': 'Parking',
      });

      expect(amenity.id, 0);
      expect(amenity.name, 'Parking');
      expect(amenity.slug, '');
      expect(amenity.icon, '');
      expect(amenity.displayOrder, 0);
    });
  });
}
