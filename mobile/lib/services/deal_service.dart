import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:flutter/foundation.dart';
import 'package:mobile/models/deal.dart';
import 'package:mobile/models/customer_completed_transaction.dart';
import 'package:mobile/services/auth_service.dart';
import 'package:mobile/services/property_service.dart';

class DealService {
  DealService._();

  static final DealService instance = DealService._();

  static const Duration _timeout = Duration(seconds: 20);

  Future<List<Deal>> fetchDeals() async {
    final uri = Uri.parse('${PropertyService.baseUrl}/api/deals/');

    final response = await _sendAuthorizedRequest((accessToken) {
      return http.get(uri, headers: _headers(accessToken)).timeout(_timeout);
    });

    final dynamic decoded = _decodeResponse(response);
    debugPrint('DEALS BODY: ${response.body}');

    if (response.statusCode != 200) {
      throw Exception(
        _extractError(decoded, fallback: 'Unable to load deals.'),
      );
    }

    if (decoded is! List) {
      throw const FormatException('The server returned invalid deal data.');
    }

    return decoded
        .whereType<Map>()
        .map((item) => Deal.fromJson(Map<String, dynamic>.from(item)))
        .toList();
  }

  Future<List<CustomerCompletedTransaction>>
  fetchCompletedTransactions() async {
    final uri = Uri.parse('${PropertyService.baseUrl}/api/deals/my-completed/');

    final response = await _sendAuthorizedRequest((accessToken) {
      return http.get(uri, headers: _headers(accessToken)).timeout(_timeout);
    });

    final dynamic decoded = _decodeResponse(response);

    if (response.statusCode != 200) {
      throw Exception(
        _extractError(
          decoded,
          fallback: 'Unable to load completed transactions.',
        ),
      );
    }

    if (decoded is! List) {
      throw const FormatException(
        'The server returned invalid transaction history data.',
      );
    }

    return decoded
        .whereType<Map>()
        .map(
          (item) => CustomerCompletedTransaction.fromJson(
            Map<String, dynamic>.from(item),
          ),
        )
        .toList();
  }

  Future<Deal> fetchDeal(int dealId) async {
    final uri = Uri.parse(
      '${PropertyService.baseUrl}'
      '/api/deals/$dealId/',
    );

    final response = await _sendAuthorizedRequest((accessToken) {
      return http.get(uri, headers: _headers(accessToken)).timeout(_timeout);
    });

    final dynamic decoded = _decodeResponse(response);

    if (response.statusCode != 200) {
      throw Exception(
        _extractError(decoded, fallback: 'Unable to load this deal.'),
      );
    }

    if (decoded is! Map) {
      throw const FormatException('The server returned invalid deal data.');
    }

    return Deal.fromJson(Map<String, dynamic>.from(decoded));
  }

  Future<Deal> submitCustomerOutcome({
    required int dealId,
    required String outcome,
    String notes = '',
  }) async {
    final uri = Uri.parse(
      '${PropertyService.baseUrl}'
      '/api/deals/$dealId/customer-outcome/',
    );

    final response = await _sendAuthorizedRequest((accessToken) {
      return http
          .post(
            uri,
            headers: {
              ..._headers(accessToken),
              'Content-Type': 'application/json',
            },
            body: jsonEncode({'outcome': outcome, 'notes': notes.trim()}),
          )
          .timeout(_timeout);
    });

    final dynamic decoded = _decodeResponse(response);

    if (response.statusCode != 201) {
      throw Exception(
        _extractError(decoded, fallback: 'Unable to submit your confirmation.'),
      );
    }

    if (decoded is! Map) {
      throw const FormatException(
        'The server returned an invalid confirmation response.',
      );
    }

    final responseMap = Map<String, dynamic>.from(decoded);

    final rawDeal = responseMap['deal'];

    if (rawDeal is! Map) {
      throw const FormatException(
        'The server did not return the updated deal.',
      );
    }

    return Deal.fromJson(Map<String, dynamic>.from(rawDeal));
  }

  Future<Deal> submitPartnerOutcome({
    required int dealId,
    required String outcome,
    String notes = '',
  }) async {
    final uri = Uri.parse(
      '${PropertyService.baseUrl}'
      '/api/deals/$dealId/partner-outcome/',
    );

    final response = await _sendAuthorizedRequest((accessToken) {
      return http
          .post(
            uri,
            headers: {
              ..._headers(accessToken),
              'Content-Type': 'application/json',
            },
            body: jsonEncode({'outcome': outcome, 'notes': notes.trim()}),
          )
          .timeout(_timeout);
    });

    final dynamic decoded = _decodeResponse(response);

    if (response.statusCode != 201) {
      throw Exception(
        _extractError(
          decoded,
          fallback: 'Unable to submit the partner confirmation.',
        ),
      );
    }

    if (decoded is! Map) {
      throw const FormatException(
        'The server returned an invalid confirmation response.',
      );
    }

    final responseMap = Map<String, dynamic>.from(decoded);

    final rawDeal = responseMap['deal'];

    if (rawDeal is! Map) {
      throw const FormatException(
        'The server did not return the updated deal.',
      );
    }

    return Deal.fromJson(Map<String, dynamic>.from(rawDeal));
  }

  Future<http.Response> _sendAuthorizedRequest(
    Future<http.Response> Function(String accessToken) sendRequest,
  ) async {
    var accessToken = await AuthService.instance.getAccessToken();

    if (accessToken == null || accessToken.trim().isEmpty) {
      throw Exception('Please sign in to continue.');
    }

    var response = await sendRequest(accessToken);

    if (response.statusCode != 401) {
      return response;
    }

    accessToken = await AuthService.instance.refreshAccessToken();

    if (accessToken == null || accessToken.trim().isEmpty) {
      throw Exception(
        'Your session has expired. '
        'Please sign in again.',
      );
    }

    response = await sendRequest(accessToken);

    return response;
  }

  Map<String, String> _headers(String accessToken) {
    return {
      'Accept': 'application/json',
      'Authorization': 'Bearer $accessToken',
    };
  }

  dynamic _decodeResponse(http.Response response) {
    final body = response.body.trim();

    if (body.isEmpty) {
      return null;
    }

    try {
      return jsonDecode(body);
    } on FormatException {
      throw const FormatException('The server returned an invalid response.');
    }
  }

  String _extractError(dynamic decoded, {required String fallback}) {
    if (decoded is Map) {
      final detail = decoded['detail'];

      if (detail is String && detail.trim().isNotEmpty) {
        return detail;
      }

      if (detail is List && detail.isNotEmpty) {
        return detail.join(' ');
      }

      final message = decoded['message'];

      if (message is String && message.trim().isNotEmpty) {
        return message;
      }

      for (final value in decoded.values) {
        if (value is List && value.isNotEmpty) {
          return value.join(' ');
        }

        if (value is String && value.trim().isNotEmpty) {
          return value;
        }
      }
    }

    return fallback;
  }
}
