import 'dart:convert';

import 'package:http/http.dart' as http;

import 'package:mobile/models/property.dart';
import 'package:mobile/services/auth_service.dart';
import 'package:mobile/services/property_service.dart';

class StaffPropertyAdminService {
  StaffPropertyAdminService._();

  static final StaffPropertyAdminService instance =
      StaffPropertyAdminService._();

  static const Duration _timeout = Duration(seconds: 30);

  Future<List<Property>> fetchProperties({String? status}) async {
    final queryParameters = <String, String>{};

    final cleanStatus = status?.trim() ?? '';

    if (cleanStatus.isNotEmpty) {
      queryParameters['status'] = cleanStatus;
    }

    final baseUri = Uri.parse('${PropertyService.baseUrl}/api/properties/');

    final uri = queryParameters.isEmpty
        ? baseUri
        : baseUri.replace(queryParameters: queryParameters);

    final response = await _sendAuthorizedRequest((accessToken) {
      return http
          .get(uri, headers: _authorizationHeaders(accessToken))
          .timeout(_timeout);
    });

    final dynamic decoded = _decodeResponse(response);

    if (response.statusCode != 200) {
      throw Exception(
        _extractErrorMessage(decoded, fallback: 'Unable to load properties.'),
      );
    }

    if (decoded is! List) {
      throw const FormatException(
        'The admin properties API returned invalid data.',
      );
    }

    return decoded.map<Property>((dynamic item) {
      if (item is! Map) {
        throw const FormatException('Invalid property information received.');
      }

      return Property.fromJson(Map<String, dynamic>.from(item));
    }).toList();
  }

  Future<Property> fetchProperty(int propertyId) async {
    if (propertyId <= 0) {
      throw ArgumentError.value(
        propertyId,
        'propertyId',
        'Property ID must be greater than zero.',
      );
    }

    final uri = Uri.parse(
      '${PropertyService.baseUrl}/api/properties/$propertyId/',
    );

    final response = await _sendAuthorizedRequest((accessToken) {
      return http
          .get(uri, headers: _authorizationHeaders(accessToken))
          .timeout(_timeout);
    });

    final dynamic decoded = _decodeResponse(response);

    if (response.statusCode != 200) {
      throw Exception(
        _extractErrorMessage(
          decoded,
          fallback: 'Unable to load this property.',
        ),
      );
    }

    if (decoded is! Map) {
      throw const FormatException(
        'The admin property API returned invalid data.',
      );
    }

    return Property.fromJson(Map<String, dynamic>.from(decoded));
  }

  Future<http.Response> _sendAuthorizedRequest(
    Future<http.Response> Function(String accessToken) request,
  ) async {
    var accessToken = await AuthService.instance.getAccessToken();

    if (accessToken == null || accessToken.trim().isEmpty) {
      throw Exception('Please sign in to continue.');
    }

    var response = await request(accessToken);

    if (response.statusCode != 401) {
      return response;
    }

    accessToken = await AuthService.instance.refreshAccessToken();

    if (accessToken == null || accessToken.trim().isEmpty) {
      throw Exception('Your session has expired. Please sign in again.');
    }

    response = await request(accessToken);

    return response;
  }

  Map<String, String> _authorizationHeaders(String accessToken) {
    return {
      'Accept': 'application/json',
      'Authorization': 'Bearer $accessToken',
    };
  }

  dynamic _decodeResponse(http.Response response) {
    if (response.body.trim().isEmpty) {
      return <String, dynamic>{};
    }

    try {
      return jsonDecode(response.body);
    } on FormatException {
      throw const FormatException(
        'The Pata Hao server returned an invalid response.',
      );
    }
  }

  String _extractErrorMessage(dynamic decoded, {required String fallback}) {
    if (decoded is Map) {
      final detail = decoded['detail'];

      if (detail is String && detail.trim().isNotEmpty) {
        return detail.trim();
      }

      if (detail is List && detail.isNotEmpty) {
        return detail.join(' ');
      }

      for (final value in decoded.values) {
        if (value is String && value.trim().isNotEmpty) {
          return value.trim();
        }

        if (value is List && value.isNotEmpty) {
          return value.join(' ');
        }
      }
    }

    return fallback;
  }
}
