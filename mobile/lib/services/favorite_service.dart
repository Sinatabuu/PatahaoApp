import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

import '../models/favorite.dart';
import 'auth_service.dart';
import 'property_service.dart';

class FavoriteService {
  FavoriteService._();

  static final FavoriteService instance = FavoriteService._();

  static const Duration _timeout = Duration(seconds: 30);

  Future<String> _getValidAccessToken() async {
    String? accessToken = await AuthService.instance.getAccessToken();

    if (accessToken == null || accessToken.trim().isEmpty) {
      throw const FavoriteException('Please sign in to save properties.');
    }

    return accessToken;
  }

  Future<Map<String, String>> _headers() async {
    final accessToken = await _getValidAccessToken();

    return {
      'Accept': 'application/json',
      'Content-Type': 'application/json',
      'Authorization': 'Bearer $accessToken',
    };
  }

  Future<List<Favorite>> fetchFavorites() async {
    final uri = Uri.parse('${PropertyService.baseUrl}/api/favorites/');

    var headers = await _headers();

    var response = await http.get(uri, headers: headers).timeout(_timeout);

    if (response.statusCode == 401) {
      final refreshedToken = await AuthService.instance.refreshAccessToken();

      if (refreshedToken == null || refreshedToken.trim().isEmpty) {
        throw const FavoriteException(
          'Your session has expired. Please sign in again.',
        );
      }

      headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Authorization': 'Bearer $refreshedToken',
      };

      response = await http.get(uri, headers: headers).timeout(_timeout);
    }

    debugPrint('FAVORITES STATUS: ${response.statusCode}');

    if (
        response.statusCode != 200 &&
        response.statusCode != 201
    ) {
      throw FavoriteException(
        _extractError(
          response,
          fallback: 'Unable to save this property.',
        ),
      );
    }

    final dynamic decoded = jsonDecode(utf8.decode(response.bodyBytes));

    if (decoded is! List) {
      throw const FormatException('Favorites API did not return a list.');
    }

    return decoded.map<Favorite>((dynamic item) {
      if (item is! Map) {
        throw const FormatException('Invalid favorite information received.');
      }

      return Favorite.fromJson(Map<String, dynamic>.from(item));
    }).toList();
  }

  Future<Favorite> saveProperty({required int propertyId}) async {
    if (propertyId <= 0) {
      throw ArgumentError.value(
        propertyId,
        'propertyId',
        'Property ID must be greater than zero.',
      );
    }

    final uri = Uri.parse('${PropertyService.baseUrl}/api/favorites/');

    var headers = await _headers();

    var response = await http
        .post(uri, headers: headers, body: jsonEncode({'property': propertyId}))
        .timeout(_timeout);

    if (response.statusCode == 401) {
      final refreshedToken = await AuthService.instance.refreshAccessToken();

      if (refreshedToken == null || refreshedToken.trim().isEmpty) {
        throw const FavoriteException(
          'Your session has expired. Please sign in again.',
        );
      }

      headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Authorization': 'Bearer $refreshedToken',
      };

      response = await http
          .post(
            uri,
            headers: headers,
            body: jsonEncode({'property': propertyId}),
          )
          .timeout(_timeout);
    }

    debugPrint(
      'SAVE FAVORITE STATUS: ${response.statusCode}',
    );

    debugPrint(
      'SAVE FAVORITE BODY: ${response.body}',
    );

    if (
        response.statusCode != 200 &&
        response.statusCode != 201
    ) {
      throw FavoriteException(
        _extractError(
          response,
          fallback: 'Unable to save this property.',
        ),
      );
    }

    final dynamic decoded = jsonDecode(utf8.decode(response.bodyBytes));

    if (decoded is! Map) {
      throw const FormatException('Favorites API returned invalid data.');
    }

    return Favorite.fromJson(Map<String, dynamic>.from(decoded));
  }

  Future<void> removeFavorite({required int favoriteId}) async {
    if (favoriteId <= 0) {
      throw ArgumentError.value(
        favoriteId,
        'favoriteId',
        'Favorite ID must be greater than zero.',
      );
    }

    final uri = Uri.parse(
      '${PropertyService.baseUrl}/api/favorites/$favoriteId/',
    );

    var headers = await _headers();

    var response = await http.delete(uri, headers: headers).timeout(_timeout);

    if (response.statusCode == 401) {
      final refreshedToken = await AuthService.instance.refreshAccessToken();

      if (refreshedToken == null || refreshedToken.trim().isEmpty) {
        throw const FavoriteException(
          'Your session has expired. Please sign in again.',
        );
      }

      headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Authorization': 'Bearer $refreshedToken',
      };

      response = await http.delete(uri, headers: headers).timeout(_timeout);
    }

    debugPrint('REMOVE FAVORITE STATUS: ${response.statusCode}');

    if (response.statusCode != 204) {
      throw FavoriteException(
        _extractError(
          response,
          fallback: 'Unable to remove this saved property.',
        ),
      );
    }
  }

  String _extractError(http.Response response, {required String fallback}) {
    if (response.body.trim().isEmpty) {
      return fallback;
    }

    try {
      final dynamic decoded = jsonDecode(response.body);

      if (decoded is Map) {
        final map = Map<String, dynamic>.from(decoded);

        final detail = map['detail'];

        if (detail != null && detail.toString().trim().isNotEmpty) {
          return detail.toString();
        }

        final propertyErrors = map['property'];

        if (propertyErrors is List && propertyErrors.isNotEmpty) {
          return propertyErrors.map((item) => item.toString()).join(', ');
        }
      }
    } on FormatException {
      return fallback;
    }

    return fallback;
  }
}

class FavoriteException implements Exception {
  const FavoriteException(this.message);

  final String message;

  @override
  String toString() => message;
}
