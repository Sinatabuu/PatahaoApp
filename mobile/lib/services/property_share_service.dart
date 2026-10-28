import '../models/property.dart';

class PropertyShareUnavailable implements Exception {
  const PropertyShareUnavailable();
}

class PropertyShareContent {
  const PropertyShareContent({required this.uri, required this.text});

  final Uri uri;
  final String text;
}

/// Only public listing details belong in content sent to another application.
PropertyShareContent propertyShareContent(Property property) {
  if (property.id <= 0 || property.status != 'published') {
    throw const PropertyShareUnavailable();
  }
  final uri = Uri.https('patahao.app', '/p/${property.id}/');
  final location = [property.estate, property.town, property.county]
      .map((part) => part.trim())
      .where((part) => part.isNotEmpty)
      .toSet()
      .join(', ');
  return PropertyShareContent(
    uri: uri,
    text: [
      property.title.trim(),
      property.formattedPrice,
      if (location.isNotEmpty) location,
      'View this property on Pata Hao:',
      uri.toString(),
    ].join('\n'),
  );
}
