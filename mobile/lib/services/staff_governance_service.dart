import 'dart:convert';

import 'package:http/http.dart' as http;

import 'package:mobile/services/auth_service.dart';
import 'package:mobile/services/property_service.dart';

class StaffGovernanceService {
  StaffGovernanceService._();

  static final StaffGovernanceService instance = StaffGovernanceService._();

  static const Duration _timeout = Duration(seconds: 30);

  Future<Map<String, dynamic>> fetchCases() async {
    final uri = Uri.parse(
      '${PropertyService.baseUrl}/api/admin/governance-cases/',
    );

    final response = await _sendAuthorizedRequest((accessToken) {
      return http.get(uri, headers: _headers(accessToken)).timeout(_timeout);
    });

    final decoded = _decode(response);

    if (response.statusCode != 200) {
      throw Exception(
        _error(decoded, fallback: 'Unable to load governance cases.'),
      );
    }

    if (decoded is! Map) {
      throw const FormatException(
        'Governance cases API returned invalid data.',
      );
    }

    return Map<String, dynamic>.from(decoded);
  }

  Future<Map<String, dynamic>> decideCase({
    required int caseId,
    required String decision,
    String notes = '',
  }) async {
    if (caseId <= 0) {
      throw ArgumentError.value(
        caseId,
        'caseId',
        'Governance case ID must be greater than zero.',
      );
    }

    final cleanDecision = decision.trim();

    const allowed = {'keep_blocked', 'return_to_partner', 'resolve'};

    if (!allowed.contains(cleanDecision)) {
      throw ArgumentError.value(
        decision,
        'decision',
        'Invalid governance decision.',
      );
    }

    final uri = Uri.parse(
      '${PropertyService.baseUrl}'
      '/api/admin/governance-cases/'
      '$caseId/decision/',
    );

    final response = await _sendAuthorizedRequest((accessToken) {
      return http
          .post(
            uri,
            headers: {
              ..._headers(accessToken),
              'Content-Type': 'application/json',
            },
            body: jsonEncode({
              'decision': cleanDecision,
              'notes': notes.trim(),
            }),
          )
          .timeout(_timeout);
    });

    final decoded = _decode(response);

    if (response.statusCode != 200) {
      throw Exception(
        _error(decoded, fallback: 'Unable to apply governance decision.'),
      );
    }

    if (decoded is! Map) {
      throw const FormatException(
        'Governance decision API returned invalid data.',
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

  Map<String, String> _headers(String accessToken) {
    return {
      'Accept': 'application/json',
      'Authorization': 'Bearer $accessToken',
    };
  }

  dynamic _decode(http.Response response) {
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

  String _error(dynamic decoded, {required String fallback}) {
    if (decoded is Map) {
      final detail = decoded['detail'];

      if (detail is String && detail.trim().isNotEmpty) {
        return detail.trim();
      }

      if (detail is List && detail.isNotEmpty) {
        return detail.join(' ');
      }

      if (detail is Map) {
        final parts = <String>[];

        for (final value in detail.values) {
          if (value is List) {
            parts.addAll(value.map((item) => item.toString()));
          } else if (value != null) {
            parts.add(value.toString());
          }
        }

        if (parts.isNotEmpty) {
          return parts.join(' ');
        }
      }
    }

    return fallback;
  }
}
