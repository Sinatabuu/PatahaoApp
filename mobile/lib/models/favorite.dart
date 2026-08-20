import 'property.dart';

class Favorite {
  final int id;
  final int customerId;
  final int propertyId;
  final Property property;
  final DateTime? createdAt;

  const Favorite({
    required this.id,
    required this.customerId,
    required this.propertyId,
    required this.property,
    required this.createdAt,
  });

  factory Favorite.fromJson(Map<String, dynamic> json) {
    final rawProperty = json['property_details'];

    if (rawProperty is! Map) {
      throw const FormatException(
        'Favorite response does not contain property details.',
      );
    }

    return Favorite(
      id: _toInt(json['id']),
      customerId: _toInt(json['customer']),
      propertyId: _toInt(json['property']),
      property: Property.fromJson(
        Map<String, dynamic>.from(rawProperty),
      ),
      createdAt: DateTime.tryParse(
        json['created_at']?.toString() ?? '',
      ),
    );
  }

  static int _toInt(dynamic value) {
    if (value is int) {
      return value;
    }

    return int.tryParse(value?.toString() ?? '') ?? 0;
  }
}