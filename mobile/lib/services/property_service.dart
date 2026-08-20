import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

import '../models/property.dart';
import '../models/property_type_option.dart';

class PropertyService {
  static const String baseUrl = 'https://patahao-api.roysafi.com';

  static const Duration _timeout = Duration(seconds: 30);

  Future<List<Property>> fetchProperties() async {
    final uri = Uri.parse('$baseUrl/api/properties/');

    debugPrint('PROPERTY REQUEST: $uri');

    try {
      final response = await http
          .get(uri, headers: const {'Accept': 'application/json'})
          .timeout(_timeout);

      debugPrint('PROPERTY STATUS: ${response.statusCode}');

      debugPrint('PROPERTY BODY: ${response.body}');

      if (response.statusCode != 200) {
        throw Exception(
          'Unable to load properties. '
          'Server returned ${response.statusCode}. '
          '${response.body}',
        );
      }

      final dynamic decoded = jsonDecode(utf8.decode(response.bodyBytes));

      if (decoded is! List) {
        throw const FormatException(
          'Properties API did not return a JSON list.',
        );
      }

      return decoded.map<Property>((dynamic item) {
        if (item is! Map) {
          throw const FormatException('Invalid property information received.');
        }

        return Property.fromJson(Map<String, dynamic>.from(item));
      }).toList();
    } catch (error, stackTrace) {
      debugPrint('PROPERTY ERROR TYPE: ${error.runtimeType}');

      debugPrint('PROPERTY ERROR: $error');
      debugPrintStack(stackTrace: stackTrace);

      rethrow;
    }
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
