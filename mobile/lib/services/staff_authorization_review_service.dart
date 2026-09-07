import 'dart:convert';

import 'package:http/http.dart' as http;

import 'package:mobile/models/staff_authorization_review.dart';
import 'package:mobile/services/auth_service.dart';
import 'package:mobile/services/property_service.dart';

class StaffAuthorizationReviewService {
  StaffAuthorizationReviewService._();

  static final StaffAuthorizationReviewService instance =
      StaffAuthorizationReviewService._();

  static const Duration _timeout = Duration(seconds: 30);

  Future<List<StaffAuthorizationReview>> fetchPendingReviews() async {
    final uri = Uri.parse(
      '${PropertyService.baseUrl}/api/mandates/',
    ).replace(
      queryParameters: const {
        'status': 'under_review',
      },
    );

    final response = await _sendAuthorizedRequest((accessToken) {
      return http
          .get(
            uri,
            headers: _authorizationHeaders(accessToken),
          )
          .timeout(_timeout);
    });

    final decoded = _decodeResponse(response);

    if (response.statusCode != 200) {
      throw Exception(
        _extractErrorMessage(
          decoded,
          fallback: 'Unable to load authorization reviews.',
        ),
      );
    }

    final List<dynamic> rawResults;

    if (decoded is List) {
      rawResults = decoded;
    } else if (decoded is Map && decoded['results'] is List) {
      rawResults = List<dynamic>.from(
        decoded['results'] as List,
      );
    } else {
      throw const FormatException(
        'The authorization review server returned invalid data.',
      );
    }

    return rawResults
        .whereType<Map>()
        .map(
          (item) => StaffAuthorizationReview.fromJson(
            Map<String, dynamic>.from(item),
          ),
        )
        .where(
          (review) => review.status == 'under_review',
        )
        .toList(growable: false);
  }

  Future<Map<String, dynamic>> fetchSalePack(
    int mandateId,
  ) async {
    _validateId(mandateId);

    final uri = Uri.parse(
      '${PropertyService.baseUrl}'
      '/api/mandates/$mandateId/sale-pack/',
    );

    final response = await _sendAuthorizedRequest((accessToken) {
      return http
          .get(
            uri,
            headers: _authorizationHeaders(accessToken),
          )
          .timeout(_timeout);
    });

    final decoded = _decodeResponse(response);

    if (response.statusCode != 200) {
      throw Exception(
        _extractErrorMessage(
          decoded,
          fallback: 'Unable to load authorization evidence.',
        ),
      );
    }

    return _requireMap(
      decoded,
      message: 'The authorization evidence response was invalid.',
    );
  }

  Future<Map<String, dynamic>> completeReview(
    int mandateId,
  ) async {
    _validateId(mandateId);

    final uri = Uri.parse(
      '${PropertyService.baseUrl}'
      '/api/mandates/$mandateId/complete-review/',
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

    final decoded = _decodeResponse(response);

    if (response.statusCode != 200) {
      throw Exception(
        _extractErrorMessage(
          decoded,
          fallback: 'Unable to approve this authorization.',
        ),
      );
    }

    return _requireMap(
      decoded,
      message: 'The authorization approval response was invalid.',
    );
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

  Map<String, String> _authorizationHeaders(
    String accessToken,
  ) {
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

  Map<String, dynamic> _requireMap(
    dynamic decoded, {
    required String message,
  }) {
    if (decoded is! Map) {
      throw FormatException(message);
    }

    return Map<String, dynamic>.from(decoded);
  }

  String _extractErrorMessage(
    dynamic decoded, {
    required String fallback,
  }) {
    if (decoded is Map) {
      final detail = decoded['detail'];

      if (detail is String && detail.trim().isNotEmpty) {
        return detail.trim();
      }

      if (detail is List && detail.isNotEmpty) {
        return detail.join(' ');
      }

      if (detail is Map && detail.isNotEmpty) {
        return detail.values
            .expand(
              (value) => value is List ? value : [value],
            )
            .join(' ');
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

  void _validateId(int mandateId) {
    if (mandateId <= 0) {
      throw ArgumentError.value(
        mandateId,
        'mandateId',
        'Mandate ID must be greater than zero.',
      );
    }
  }
}
