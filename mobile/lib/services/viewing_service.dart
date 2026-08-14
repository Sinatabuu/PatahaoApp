import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

import '../models/viewing.dart';
import 'auth_service.dart';
import 'property_service.dart';

import '../models/viewing_feedback.dart';

class ViewingService {
  static const Duration _timeout = Duration(seconds: 30);

  Future<Viewing> createViewing({
    required int propertyId,
    required DateTime requestedDate,
    required String requestedTime,
    required String customerMessage,
  }) async {
    final uri = Uri.parse('${PropertyService.baseUrl}/api/viewings/');

    final body = jsonEncode({
      'property': propertyId,
      'requested_date': _formatDate(requestedDate),
      'requested_time': requestedTime,
      'customer_message': customerMessage.trim(),
    });

    debugPrint('CREATE VIEWING REQUEST: $uri');

    final response = await _authorizedPost(uri, body: body);

    debugPrint('CREATE VIEWING STATUS: ${response.statusCode}');

    debugPrint('CREATE VIEWING BODY: ${response.body}');

    final dynamic decoded = _decodeResponse(
      response.body,
      fallback: <String, dynamic>{},
    );

    if (response.statusCode == 201 && decoded is Map) {
      return Viewing.fromJson(Map<String, dynamic>.from(decoded));
    }

    throw Exception(
      _extractError(
        decoded,
        fallback:
            'Unable to create the viewing reservation. '
            'Server returned ${response.statusCode}.',
      ),
    );
  }

  Future<List<Viewing>> getMyViewings() async {
    final uri = Uri.parse('${PropertyService.baseUrl}/api/viewings/');

    debugPrint('MY VIEWINGS REQUEST: $uri');

    try {
      final response = await _authorizedGet(uri);

      debugPrint('MY VIEWINGS STATUS: ${response.statusCode}');

      debugPrint('MY VIEWINGS BODY: ${response.body}');

      final dynamic decoded = _decodeResponse(
        response.body,
        fallback: <dynamic>[],
      );

      if (response.statusCode == 200) {
        if (decoded is List) {
          return decoded
              .whereType<Map>()
              .map((item) => Viewing.fromJson(Map<String, dynamic>.from(item)))
              .toList();
        }

        if (decoded is Map) {
          final decodedMap = Map<String, dynamic>.from(decoded);

          final dynamic results = decodedMap['results'];

          if (results is List) {
            return results
                .whereType<Map>()
                .map(
                  (item) => Viewing.fromJson(Map<String, dynamic>.from(item)),
                )
                .toList();
          }
        }

        throw const FormatException(
          'The viewings API returned an unexpected format.',
        );
      }

      throw Exception(
        _extractError(
          decoded,
          fallback:
              'Unable to load your viewings. '
              'Server returned ${response.statusCode}.',
        ),
      );
    } catch (error, stackTrace) {
      debugPrint('MY VIEWINGS ERROR TYPE: ${error.runtimeType}');

      debugPrint('MY VIEWINGS ERROR: $error');

      debugPrintStack(stackTrace: stackTrace);

      rethrow;
    }
  }

  Future<Viewing> getViewing(int viewingId) async {
    final uri = Uri.parse(
      '${PropertyService.baseUrl}/api/viewings/'
      '$viewingId/',
    );

    debugPrint('VIEWING DETAILS REQUEST: $uri');

    final response = await _authorizedGet(uri);

    debugPrint(
      'VIEWING DETAILS STATUS: '
      '${response.statusCode}',
    );

    debugPrint('VIEWING DETAILS BODY: ${response.body}');

    final dynamic decoded = _decodeResponse(
      response.body,
      fallback: <String, dynamic>{},
    );

    if (response.statusCode == 200 && decoded is Map) {
      return Viewing.fromJson(Map<String, dynamic>.from(decoded));
    }

    throw Exception(
      _extractError(
        decoded,
        fallback:
            'Unable to load the viewing details. '
            'Server returned ${response.statusCode}.',
      ),
    );
  }

  Future<ViewingFeedback?> getViewingFeedback(int viewingId) async {
    final uri = Uri.parse(
      '${PropertyService.baseUrl}/api/viewings/'
      '$viewingId/feedback/',
    );

    debugPrint('GET VIEWING FEEDBACK REQUEST: $uri');

    final response = await _authorizedGet(uri);

    debugPrint(
      'GET VIEWING FEEDBACK STATUS: '
      '${response.statusCode}',
    );

    debugPrint(
      'GET VIEWING FEEDBACK BODY: '
      '${response.body}',
    );

    final dynamic decoded = _decodeResponse(
      response.body,
      fallback: <String, dynamic>{},
    );

    if (response.statusCode == 200 && decoded is Map) {
      return ViewingFeedback.fromJson(Map<String, dynamic>.from(decoded));
    }

    if (response.statusCode == 404 && decoded is Map) {
      final decodedMap = Map<String, dynamic>.from(decoded);

      final detail = decodedMap['detail']?.toString() ?? '';

      if (detail.toLowerCase().contains('feedback has not been submitted')) {
        return null;
      }
    }

    throw Exception(
      _extractError(
        decoded,
        fallback:
            'Unable to check the viewing feedback. '
            'Server returned ${response.statusCode}.',
      ),
    );
  }

  Future<ViewingFeedback> submitViewingFeedback({
    required int viewingId,
    required bool attended,
    required String propertyAccuracy,
    required int partnerRating,
    required int propertyRating,
    required String comments,
  }) async {
    if (!const {'yes', 'partially', 'no'}.contains(propertyAccuracy)) {
      throw Exception(
        'Select whether the property matched '
        'the listing.',
      );
    }

    if (partnerRating < 1 || partnerRating > 5) {
      throw Exception('Partner rating must be between 1 and 5.');
    }

    if (propertyRating < 1 || propertyRating > 5) {
      throw Exception('Property rating must be between 1 and 5.');
    }

    final uri = Uri.parse(
      '${PropertyService.baseUrl}/api/viewings/'
      '$viewingId/feedback/',
    );

    final body = jsonEncode(<String, dynamic>{
      'attended': attended,
      'property_accuracy': propertyAccuracy,
      'partner_rating': partnerRating,
      'property_rating': propertyRating,
      'comments': comments.trim(),
    });

    debugPrint('SUBMIT VIEWING FEEDBACK REQUEST: $uri');

    debugPrint('SUBMIT VIEWING FEEDBACK BODY: $body');

    final response = await _authorizedPost(uri, body: body);

    debugPrint(
      'SUBMIT VIEWING FEEDBACK STATUS: '
      '${response.statusCode}',
    );

    debugPrint(
      'SUBMIT VIEWING FEEDBACK RESPONSE: '
      '${response.body}',
    );

    final dynamic decoded = _decodeResponse(
      response.body,
      fallback: <String, dynamic>{},
    );

    if (response.statusCode == 201 && decoded is Map) {
      return ViewingFeedback.fromJson(Map<String, dynamic>.from(decoded));
    }

    throw Exception(
      _extractError(
        decoded,
        fallback:
            'Unable to submit your feedback. '
            'Server returned ${response.statusCode}.',
      ),
    );
  }

  Future<Viewing> acceptReschedule(int viewingId) async {
    final uri = Uri.parse(
      '${PropertyService.baseUrl}/api/viewings/'
      '$viewingId/accept-reschedule/',
    );

    final response = await _authorizedPost(
      uri,
      body: jsonEncode(<String, dynamic>{}),
    );

    final dynamic decoded = _decodeResponse(
      response.body,
      fallback: <String, dynamic>{},
    );

    if (response.statusCode == 200 && decoded is Map) {
      final dynamic viewingData = decoded['viewing'];

      if (viewingData is Map) {
        return Viewing.fromJson(Map<String, dynamic>.from(viewingData));
      }
    }

    throw Exception(
      _extractError(
        decoded,
        fallback:
            'Unable to accept the proposed '
            'viewing time.',
      ),
    );
  }

  Future<Viewing> declineReschedule(int viewingId) async {
    final uri = Uri.parse(
      '${PropertyService.baseUrl}/api/viewings/'
      '$viewingId/decline-reschedule/',
    );

    final response = await _authorizedPost(
      uri,
      body: jsonEncode(<String, dynamic>{}),
    );

    final dynamic decoded = _decodeResponse(
      response.body,
      fallback: <String, dynamic>{},
    );

    if (response.statusCode == 200 && decoded is Map) {
      final dynamic viewingData = decoded['viewing'];

      if (viewingData is Map) {
        return Viewing.fromJson(Map<String, dynamic>.from(viewingData));
      }
    }

    throw Exception(
      _extractError(
        decoded,
        fallback:
            'Unable to decline the proposed '
            'viewing time.',
      ),
    );
  }

  Future<http.Response> _authorizedGet(Uri uri) async {
    String? accessToken = await AuthService.instance.getAccessToken();

    if (accessToken == null || accessToken.trim().isEmpty) {
      throw Exception('Please log in to continue.');
    }

    debugPrint(
      'VIEWING AUTH TOKEN PRESENT: '
      '${accessToken.isNotEmpty}',
    );

    var response = await http
        .get(uri, headers: _headers(accessToken))
        .timeout(_timeout);

    if (response.statusCode == 401) {
      debugPrint(
        'VIEWING REQUEST RECEIVED 401. '
        'Refreshing access token.',
      );

      accessToken = await AuthService.instance.refreshAccessToken();

      if (accessToken == null || accessToken.trim().isEmpty) {
        throw Exception(
          'Your session has expired. '
          'Please log in again.',
        );
      }

      response = await http
          .get(uri, headers: _headers(accessToken))
          .timeout(_timeout);
    }

    return response;
  }

  Future<http.Response> _authorizedPost(Uri uri, {required String body}) async {
    String? accessToken = await AuthService.instance.getAccessToken();

    if (accessToken == null || accessToken.trim().isEmpty) {
      throw Exception(
        'Please log in before requesting '
        'a viewing.',
      );
    }

    var response = await http
        .post(
          uri,
          headers: _headers(accessToken, includeContentType: true),
          body: body,
        )
        .timeout(_timeout);

    if (response.statusCode == 401) {
      accessToken = await AuthService.instance.refreshAccessToken();

      if (accessToken == null || accessToken.trim().isEmpty) {
        throw Exception(
          'Your session has expired. '
          'Please log in again.',
        );
      }

      response = await http
          .post(
            uri,
            headers: _headers(accessToken, includeContentType: true),
            body: body,
          )
          .timeout(_timeout);
    }

    return response;
  }

  Map<String, String> _headers(
    String accessToken, {
    bool includeContentType = false,
  }) {
    return {
      'Accept': 'application/json',
      if (includeContentType) 'Content-Type': 'application/json',
      'Authorization': 'Bearer ${accessToken.trim()}',
    };
  }

  dynamic _decodeResponse(String body, {required dynamic fallback}) {
    if (body.trim().isEmpty) {
      return fallback;
    }

    try {
      return jsonDecode(body);
    } on FormatException {
      return <String, dynamic>{
        'detail': 'The server returned an invalid response.',
      };
    }
  }

  String _formatDate(DateTime date) {
    final year = date.year.toString().padLeft(4, '0');

    final month = date.month.toString().padLeft(2, '0');

    final day = date.day.toString().padLeft(2, '0');

    return '$year-$month-$day';
  }

  String _extractError(dynamic decoded, {required String fallback}) {
    if (decoded is Map) {
      final decodedMap = Map<String, dynamic>.from(decoded);

      final dynamic detail = decodedMap['detail'];

      if (detail != null && detail.toString().trim().isNotEmpty) {
        return detail.toString();
      }

      final messages = <String>[];

      for (final entry in decodedMap.entries) {
        final value = entry.value;

        if (value is List) {
          messages.add(
            '${entry.key}: '
            '${value.map((item) => item.toString()).join(', ')}',
          );
        } else if (value != null) {
          messages.add('${entry.key}: $value');
        }
      }

      if (messages.isNotEmpty) {
        return messages.join('\n');
      }
    }

    return fallback;
  }
}
