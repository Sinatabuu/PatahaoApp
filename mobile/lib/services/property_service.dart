import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

import '../models/property.dart';
import '../models/property_type_option.dart';

class PropertyFeedPage {
  const PropertyFeedPage({
    required this.properties,
    required this.recentSuccesses,
    required this.count,
    required this.hasNext,
  });

  final List<Property> properties;
  final List<Property> recentSuccesses;
  final int count;
  final bool hasNext;

  factory PropertyFeedPage.fromJson(dynamic decoded) {
    if (decoded is List) {
      final properties = _parseProperties(decoded);

      return PropertyFeedPage(
        properties: properties
            .where((property) => !property.isSuccessBroadcastActive)
            .toList(),
        recentSuccesses: properties
            .where((property) => property.isSuccessBroadcastActive)
            .toList(),
        count: properties
            .where((property) => !property.isSuccessBroadcastActive)
            .length,
        hasNext: false,
      );
    }

    if (decoded is! Map) {
      throw const FormatException('Properties API returned invalid feed data.');
    }

    final payload = Map<String, dynamic>.from(decoded);
    final results = payload['results'];
    final recentSuccesses = payload['recent_successes'] ?? const <dynamic>[];

    if (results is! List || recentSuccesses is! List) {
      throw const FormatException(
        'Properties API returned an invalid paginated feed.',
      );
    }

    final parsedProperties = _parseProperties(results);
    final parsedSuccesses = _parseProperties(recentSuccesses);

    return PropertyFeedPage(
      properties: parsedProperties,
      recentSuccesses: parsedSuccesses,
      count: _parseCount(payload['count'], parsedProperties.length),
      hasNext: payload['next'] != null,
    );
  }

  static int _parseCount(dynamic value, int fallback) {
    if (value is int) {
      return value;
    }

    return int.tryParse(value?.toString() ?? '') ?? fallback;
  }

  static List<Property> _parseProperties(List<dynamic> items) {
    return items.map<Property>((dynamic item) {
      if (item is! Map) {
        throw const FormatException('Invalid property information received.');
      }

      return Property.fromJson(Map<String, dynamic>.from(item));
    }).toList();
  }
}

class PropertyService {
  static const String baseUrl = 'https://patahao-api.roysafi.com';

  static const Duration _timeout = Duration(seconds: 30);

  Future<PropertyFeedPage> fetchPropertyFeed({
    int page = 1,
    String search = '',
    String listingType = 'all',
    String propertyType = 'all',
    int? bedrooms,
    double? minimumPrice,
    double? maximumPrice,
    bool verifiedOnly = false,
  }) async {
    final queryParameters = <String, String>{
      'feed': 'compact',
      if (page > 1) 'page': '$page',
      if (search.trim().isNotEmpty) 'search': search.trim(),
      if (listingType != 'all') 'listing_type': listingType,
      if (propertyType != 'all') 'property_type': propertyType,
      if (bedrooms != null) 'bedrooms': '$bedrooms',
      if (minimumPrice != null) 'min_price': '$minimumPrice',
      if (maximumPrice != null) 'max_price': '$maximumPrice',
      if (verifiedOnly) 'verified_only': 'true',
    };

    final uri = Uri.parse(
      '$baseUrl/api/properties/',
    ).replace(queryParameters: queryParameters);

    debugPrint('PROPERTY REQUEST: $uri');

    try {
      final response = await http
          .get(uri, headers: const {'Accept': 'application/json'})
          .timeout(_timeout);

      debugPrint('PROPERTY STATUS: ${response.statusCode}');

      if (response.statusCode != 200) {
        throw Exception(
          'Unable to load properties. '
          'Server returned ${response.statusCode}. '
          '${response.body}',
        );
      }

      final dynamic decoded = jsonDecode(utf8.decode(response.bodyBytes));

      return PropertyFeedPage.fromJson(decoded);
    } catch (error, stackTrace) {
      debugPrint('PROPERTY ERROR TYPE: ${error.runtimeType}');

      debugPrint('PROPERTY ERROR: $error');
      debugPrintStack(stackTrace: stackTrace);

      rethrow;
    }
  }

  Future<List<Property>> fetchProperties() async {
    final feed = await fetchPropertyFeed();

    return [...feed.properties, ...feed.recentSuccesses];
  }

  Future<Property> fetchProperty(int propertyId) async {
    if (propertyId <= 0) {
      throw ArgumentError.value(
        propertyId,
        'propertyId',
        'Property ID must be greater than zero.',
      );
    }

    final uri = Uri.parse('$baseUrl/api/properties/$propertyId/');

    debugPrint('PROPERTY DETAILS REQUEST: $uri');

    try {
      final response = await http
          .get(uri, headers: const {'Accept': 'application/json'})
          .timeout(_timeout);

      debugPrint(
        'PROPERTY DETAILS STATUS: '
        '${response.statusCode}',
      );

      if (response.statusCode != 200) {
        throw Exception(
          'Unable to load property. '
          'Server returned ${response.statusCode}. '
          '${response.body}',
        );
      }

      final dynamic decoded = jsonDecode(utf8.decode(response.bodyBytes));

      if (decoded is! Map) {
        throw const FormatException(
          'Properties API returned invalid property data.',
        );
      }

      return Property.fromJson(Map<String, dynamic>.from(decoded));
    } catch (error, stackTrace) {
      debugPrint(
        'PROPERTY DETAILS ERROR TYPE: '
        '${error.runtimeType}',
      );

      debugPrint('PROPERTY DETAILS ERROR: $error');

      debugPrintStack(stackTrace: stackTrace);

      rethrow;
    }
  }

  Future<List<PropertyTypeOption>> fetchPropertyTypes() async {
    final uri = Uri.parse('$baseUrl/api/property-types/');

    debugPrint('PROPERTY TYPES REQUEST: $uri');

    try {
      final response = await http
          .get(uri, headers: const {'Accept': 'application/json'})
          .timeout(_timeout);

      debugPrint(
        'PROPERTY TYPES STATUS: '
        '${response.statusCode}',
      );

      if (response.statusCode != 200) {
        throw Exception(
          'Could not load property types. '
          'Server returned ${response.statusCode}. '
          '${response.body}',
        );
      }

      final dynamic decoded = jsonDecode(utf8.decode(response.bodyBytes));

      if (decoded is! List) {
        throw const FormatException('Property type response must be a list.');
      }

      return decoded.map<PropertyTypeOption>((dynamic item) {
        if (item is! Map) {
          throw const FormatException(
            'Invalid property type information received.',
          );
        }

        return PropertyTypeOption.fromJson(Map<String, dynamic>.from(item));
      }).toList();
    } catch (error, stackTrace) {
      debugPrint(
        'PROPERTY TYPES ERROR TYPE: '
        '${error.runtimeType}',
      );

      debugPrint('PROPERTY TYPES ERROR: $error');

      debugPrintStack(stackTrace: stackTrace);

      rethrow;
    }
  }
}
