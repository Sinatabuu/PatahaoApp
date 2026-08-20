import 'dart:convert';

import 'package:http/http.dart' as http;

import 'package:mobile/services/auth_service.dart';
import 'package:mobile/services/property_service.dart';

class PartnerGovernanceService {
  PartnerGovernanceService._();

  static final PartnerGovernanceService instance = PartnerGovernanceService._();

  static const Duration _timeout = Duration(seconds: 30);

  Future<List<Map<String, dynamic>>> fetchActiveCases() async {
    final uri = Uri.parse(
      '${PropertyService.baseUrl}'
      '/api/partner/governance-cases/',
    );

    final response = await _sendAuthorizedRequest((accessToken) {
      return http
          .get(uri, headers: _authorizationHeaders(accessToken))
          .timeout(_timeout);
    });

    final decoded = _decodeResponse(response);

    if (response.statusCode != 200) {
      throw Exception(
        _extractErrorMessage(
          decoded,
          fallback: 'Unable to load governance actions.',
        ),
      );
    }

    if (decoded is! Map || decoded['results'] is! List) {
      throw const FormatException(
        'Governance actions API returned invalid data.',
      );
    }

    final results = <Map<String, dynamic>>[];

    for (final item in decoded['results'] as List) {
      if (item is Map) {
        results.add(Map<String, dynamic>.from(item));
      }
    }

    return results;
  }

  Future<Map<String, dynamic>> requestReview(int caseId) async {
    if (caseId <= 0) {
      throw ArgumentError.value(
        caseId,
        'caseId',
        'Governance case ID must be greater than zero.',
      );
    }

    final uri = Uri.parse(
      '${PropertyService.baseUrl}'
      '/api/partner/governance-cases/'
      '$caseId/request-review/',
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
          fallback: 'Unable to request governance review.',
        ),
      );
    }

    if (decoded is! Map) {
      throw const FormatException(
        'Governance review API returned invalid data.',
      );
    }

    return Map<String, dynamic>.from(decoded);
  }

  Future<http.Response> _sendAuthorizedRequest(
    Future<http.Response> Function(String accessToken) request,
  ) async {
    var accessToken = await AuthService.instance.getAccessToken();

    if (accessToken == null || accessToken.trim().isEmpty) {
      throw Exception('Please sign in to continue.');
    }

    var response = await request(accessToken.trim());

    if (response.statusCode != 401) {
      return response;
    }

    accessToken = await AuthService.instance.refreshAccessToken();

    if (accessToken == null || accessToken.trim().isEmpty) {
      throw Exception('Your session has expired. Please sign in again.');
    }

    return request(accessToken.trim());
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
    }

    return fallback;
  }
}
