import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/models/property.dart';
import 'package:mobile/screens/property_detail_screen.dart';

Map<String, dynamic> _propertyJson({
  String floorArea = '1850.50',
  String floorAreaUnit = 'sq_ft',
  String landArea = '0.1250',
  String landAreaUnit = 'acres',
}) {
  return <String, dynamic>{
    'id': 87,
    'title': 'Garden Estate Family Home',
    'property_type': 'house',
    'listing_type': 'sale',
    'price': '12500000.00',
    'county': 'Nairobi',
    'town': 'Roysambu',
    'estate': 'Garden Estate',
    'bedrooms': 4,
    'bathrooms': 3,
    'floor_area': floorArea,
    'floor_area_unit': floorAreaUnit,
    'land_area': landArea,
    'land_area_unit': landAreaUnit,
    'description': 'Bright family home with a private garden.',
    'status': 'published',
    'trust_badge': 'gold',
    'photos': <dynamic>[],
    'videos': <dynamic>[],
    'amenities': <dynamic>[],
  };
}

void main() {
  test('property parses and formats floor and plot measurements', () {
    final property = Property.fromJson(_propertyJson());

    expect(property.hasFloorArea, true);
    expect(property.hasLandArea, true);
    expect(property.formattedFloorArea, '1,850.5 sq ft');
    expect(property.formattedLandArea, '0.125 acres');
  });

  test('missing measurements remain backward compatible', () {
    final property = Property.fromJson(
      _propertyJson(floorArea: '', landArea: ''),
    );

    expect(property.hasFloorArea, false);
    expect(property.hasLandArea, false);
    expect(property.formattedFloorArea, '');
    expect(property.formattedLandArea, '');
  });

  testWidgets('property details show marketing facts and real description', (
    tester,
  ) async {
    final property = Property.fromJson(_propertyJson());

    await tester.pumpWidget(
      MaterialApp(home: PropertyDetailScreen(property: property)),
    );
    await tester.pumpAndSettle();

    expect(find.text('4 bedrooms'), findsOneWidget);
    expect(find.text('3 bathrooms'), findsOneWidget);
    expect(find.text('Floor 1,850.5 sq ft'), findsOneWidget);
    expect(find.text('Plot 0.125 acres'), findsOneWidget);
    expect(
      find.text('Bright family home with a private garden.'),
      findsOneWidget,
    );
    expect(
      find.textContaining('request a viewing to receive more information'),
      findsNothing,
    );
  });
}
