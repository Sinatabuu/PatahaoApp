import 'dart:convert';

import 'package:http/http.dart' as http;

import 'package:mobile/services/auth_service.dart';
import 'package:mobile/services/property_service.dart';

class StaffPropertyReviewService {
  StaffPropertyReviewService._();

  static final StaffPropertyReviewService instance =
      StaffPropertyReviewService._();

  static const Duration _timeout = Duration(seconds: 30);

  Future<List<Map<String, dynamic>>> fetchReviewQueue() async {
    final uri = Uri.parse('${PropertyService.baseUrl}/api/property-reviews/');

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
          fallback: 'Unable to load the Pata Hao review queue.',
        ),
      );
    }

    if (decoded is! Map) {
      throw const FormatException(
        'The property review queue returned invalid data.',
      );
    }

    final decodedMap = Map<String, dynamic>.from(decoded);
    final rawResults = decodedMap['results'];

    if (rawResults is! List) {
      throw const FormatException(
        'The property review queue did not contain a valid results list.',
      );
    }

    return rawResults
        .whereType<Map>()
        .map((item) => Map<String, dynamic>.from(item))
        .toList();
  }

  Future<Map<String, dynamic>> fetchPropertyReview(int propertyId) async {
    _validateId(propertyId, name: 'propertyId');

    final uri = Uri.parse(
      '${PropertyService.baseUrl}'
      '/api/property-reviews/$propertyId/',
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
          fallback: 'Unable to load this property review.',
        ),
      );
    }

    if (decoded is! Map) {
      throw const FormatException(
        'The property review API returned invalid data.',
      );
    }

    return Map<String, dynamic>.from(decoded);
  }

  Future<Map<String, dynamic>> verifyCommission(int propertyId) async {
    return _postReviewAction(
      propertyId: propertyId,
      actionPath: 'verify-commission',
      fallbackMessage: 'Unable to verify the commission agreement.',
    );
  }

  Future<Map<String, dynamic>> lockCommission(int propertyId) async {
    return _postReviewAction(
      propertyId: propertyId,
      actionPath: 'lock-commission',
      fallbackMessage: 'Unable to lock the commission agreement.',
    );
  }

  Future<Map<String, dynamic>> approveMandate(int propertyId) async {
    return _postReviewAction(
      propertyId: propertyId,
      actionPath: 'approve-mandate',
      fallbackMessage: 'Unable to approve the digital mandate.',
    );
  }

  Future<Map<String, dynamic>> publishProperty(int propertyId) async {
    _validateId(propertyId, name: 'propertyId');

    final uri = Uri.parse(
      '${PropertyService.baseUrl}'
      '/api/property-reviews/$propertyId/publish/',
    );

    final response = await _sendAuthorizedRequest((accessToken) {
      return http
          .post(
            uri,
            headers: {
              ..._authorizationHeaders(accessToken),
              'Content-Type': 'application/json',
            },
            body: jsonEncode(<String, dynamic>{}),
          )
          .timeout(_timeout);
    });

    final dynamic decoded = _decodeResponse(response);

    if (response.statusCode != 200) {
      throw Exception(
        _extractErrorMessage(
          decoded,
          fallback: 'Unable to publish this property.',
        ),
      );
    }

    if (decoded is! Map) {
      throw const FormatException(
        'The property publishing API returned invalid data.',
      );
    }

    return Map<String, dynamic>.from(decoded);
  }

  Future<Map<String, dynamic>> returnToPartner({
    required int propertyId,
    required String reason,
  }) async {
    _validateId(propertyId, name: 'propertyId');

    final cleanReason = reason.trim();

    if (cleanReason.isEmpty) {
      throw ArgumentError('A return reason is required.');
    }

    final uri = Uri.parse(
      '${PropertyService.baseUrl}'
      '/api/property-reviews/$propertyId/return-to-partner/',
    );

    final response = await _sendAuthorizedRequest((accessToken) {
      return http
          .post(
            uri,
            headers: {
              ..._authorizationHeaders(accessToken),
              'Content-Type': 'application/json',
            },
            body: jsonEncode(<String, dynamic>{'reason': cleanReason}),
          )
          .timeout(_timeout);
    });

    final dynamic decoded = _decodeResponse(response);

    if (response.statusCode != 200) {
      throw Exception(
        _extractErrorMessage(
          decoded,
          fallback: 'Unable to return this property to the partner.',
        ),
      );
    }

    if (decoded is! Map) {
      throw const FormatException(
        'The return-to-partner API returned invalid data.',
      );
    }

    return Map<String, dynamic>.from(decoded);
  }

  Future<Map<String, dynamic>> _postReviewAction({
    required int propertyId,
    required String actionPath,
    required String fallbackMessage,
  }) async {
    _validateId(propertyId, name: 'propertyId');

    final uri = Uri.parse(
      '${PropertyService.baseUrl}'
      '/api/property-reviews/$propertyId/$actionPath/',
    );

    final response = await _sendAuthorizedRequest((accessToken) {
      return http
          .post(
            uri,
            headers: {
              ..._authorizationHeaders(accessToken),
              'Content-Type': 'application/json',
            },
            body: jsonEncode(<String, dynamic>{}),
          )
          .timeout(_timeout);
    });

    final dynamic decoded = _decodeResponse(response);

    if (response.statusCode != 200) {
      throw Exception(_extractErrorMessage(decoded, fallback: fallbackMessage));
    }

    if (decoded is! Map) {
      throw const FormatException(
        'The Pata Hao review API returned invalid data.',
      );
    }

    return Map<String, dynamic>.from(decoded);
  }

  Future<http.Response> _sendAuthorizedRequest(
    Future<http.Response> Function(String accessToken) request,
  ) async {
    var accessToken = await AuthService.instance.getAccessToken();

    if (accessToken == null || accessToken.isEmpty) {
      throw Exception('Please sign in to continue.');
    }

    var response = await request(accessToken);

    if (response.statusCode != 401) {
      return response;
    }

    accessToken = await AuthService.instance.refreshAccessToken();

    if (accessToken == null || accessToken.isEmpty) {
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
    final body = response.body.trim();

    if (body.isEmpty) {
      return <String, dynamic>{};
    }

    try {
      return jsonDecode(body);
    } on FormatException {
      return <String, dynamic>{
        'detail': 'The server returned an invalid response.',
      };
    }
  }

  String _extractErrorMessage(dynamic decoded, {required String fallback}) {
    if (decoded is Map) {
      final decodedMap = Map<String, dynamic>.from(decoded);

      final detail = decodedMap['detail'];

      if (detail != null) {
        final detailMessage = _stringifyErrorValue(detail);

        if (detailMessage.isNotEmpty) {
          return detailMessage;
        }
      }

      final reasons = decodedMap['reasons'];

      if (reasons != null) {
        final reasonsMessage = _stringifyErrorValue(reasons);

        if (reasonsMessage.isNotEmpty) {
          return reasonsMessage;
        }
      }

      final blockers = decodedMap['blockers'];

      if (blockers != null) {
        final blockersMessage = _stringifyErrorValue(blockers);

        if (blockersMessage.isNotEmpty) {
          return blockersMessage;
        }
      }
    }

    if (decoded is List) {
      final message = _stringifyErrorValue(decoded);

      if (message.isNotEmpty) {
        return message;
      }
    }

    return fallback;
  }

  String _stringifyErrorValue(dynamic value) {
    if (value == null) {
      return '';
    }

    if (value is List) {
      return value
          .map(_stringifyErrorValue)
          .where((message) => message.isNotEmpty)
          .join('\n');
    }

    if (value is Map) {
      final messages = <String>[];

      for (final entry in value.entries) {
        final message = _stringifyErrorValue(entry.value);

        if (message.isNotEmpty) {
          messages.add(message);
        }
      }

      return messages.join('\n');
    }

    return value.toString().trim();
  }

  void _validateId(int value, {required String name}) {
    if (value <= 0) {
      throw ArgumentError('$name must be greater than zero.');
    }
  }
}
