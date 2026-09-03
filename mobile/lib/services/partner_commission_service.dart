import 'dart:convert';

import 'package:http/http.dart' as http;

import 'package:mobile/models/partner_commission.dart';
import 'package:mobile/services/auth_service.dart';
import 'package:mobile/services/property_service.dart';

class PartnerCommissionService {
  PartnerCommissionService._();

  static final PartnerCommissionService instance = PartnerCommissionService._();

  static const Duration _requestTimeout = Duration(seconds: 20);

  Future<PartnerCommissionSummary> getSummary() async {
    final response = await _authenticatedGet(
      '/api/partner/commission-summary/',
    );

    final dynamic decoded = _decodeResponse(response.body);

    if (response.statusCode != 200) {
      throw Exception(
        _extractErrorMessage(
          decoded,
          fallback: 'Unable to load your commission summary.',
        ),
      );
    }

    if (decoded is! Map<String, dynamic>) {
      throw const FormatException(
        'The commission summary server returned '
        'an unexpected response.',
      );
    }

    return PartnerCommissionSummary.fromJson(decoded);
  }

  Future<List<PartnerCommissionSettlement>> getSettlements() async {
    final response = await _authenticatedGet(
      '/api/partner/commission-settlements/',
    );

    final dynamic decoded = _decodeResponse(response.body);

    if (response.statusCode != 200) {
      throw Exception(
        _extractErrorMessage(
          decoded,
          fallback: 'Unable to load your commission settlements.',
        ),
      );
    }

    final List<dynamic> rawSettlements;

    if (decoded is List<dynamic>) {
      rawSettlements = decoded;
    } else if (decoded is Map<String, dynamic> &&
        decoded['results'] is List<dynamic>) {
      rawSettlements = decoded['results'] as List<dynamic>;
    } else {
      throw const FormatException(
        'The commission settlement server returned '
        'an unexpected response.',
      );
    }

    return rawSettlements
        .whereType<Map>()
        .map(
          (item) => PartnerCommissionSettlement.fromJson(
            Map<String, dynamic>.from(item),
          ),
        )
        .toList();
  }

  Future<PartnerCommissionSettlement> getSettlement(int settlementId) async {
    if (settlementId <= 0) {
      throw ArgumentError.value(
        settlementId,
        'settlementId',
        'Settlement ID must be greater than zero.',
      );
    }

    final response = await _authenticatedGet(
      '/api/partner/commission-settlements/'
      '$settlementId/',
    );

    final dynamic decoded = _decodeResponse(response.body);

    if (response.statusCode != 200) {
      throw Exception(
        _extractErrorMessage(
          decoded,
          fallback: 'Unable to load this commission settlement.',
        ),
      );
    }

    if (decoded is! Map<String, dynamic>) {
      throw const FormatException(
        'The commission settlement server returned '
        'an unexpected response.',
      );
    }

    return PartnerCommissionSettlement.fromJson(decoded);
  }

  Future<http.Response> _authenticatedGet(String path) async {
    String? accessToken = await AuthService.instance.getAccessToken();

    if (accessToken == null || accessToken.isEmpty) {
      throw Exception('You are not logged in. Please log in again.');
    }

    http.Response response = await _sendGet(
      path: path,
      accessToken: accessToken,
    );

    if (response.statusCode == 401) {
      accessToken = await AuthService.instance.refreshAccessToken();

      if (accessToken == null || accessToken.isEmpty) {
        throw Exception(
          'Your session has expired. '
          'Please log in again.',
        );
      }

      response = await _sendGet(path: path, accessToken: accessToken);
    }

    return response;
  }

  Future<http.Response> _sendGet({
    required String path,
    required String accessToken,
  }) {
    final uri = Uri.parse('${PropertyService.baseUrl}$path');

    return http
        .get(
          uri,
          headers: <String, String>{
            'Accept': 'application/json',
            'Authorization': 'Bearer $accessToken',
          },
        )
        .timeout(_requestTimeout);
  }

  dynamic _decodeResponse(String body) {
    if (body.trim().isEmpty) {
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
    if (decoded is Map<String, dynamic>) {
      final detail = decoded['detail'];

      if (detail != null && detail.toString().trim().isNotEmpty) {
        return detail.toString().trim();
      }

      final message = decoded['message'];

      if (message != null && message.toString().trim().isNotEmpty) {
        return message.toString().trim();
      }

      final errors = <String>[];

      for (final entry in decoded.entries) {
        final value = entry.value;

        if (value is List) {
          final text = value
              .map((item) => item.toString().trim())
              .where((item) => item.isNotEmpty)
              .join(', ');

          if (text.isNotEmpty) {
            errors.add(text);
          }
        } else if (value != null && value.toString().trim().isNotEmpty) {
          errors.add(value.toString().trim());
        }
      }

      if (errors.isNotEmpty) {
        return errors.join('\n');
      }
    }

    return fallback;
  }
}
