import 'dart:convert';

import 'package:http/http.dart' as http;

import 'package:mobile/models/partner_transaction_history.dart';
import 'package:mobile/services/auth_service.dart';
import 'package:mobile/services/property_service.dart';

class PartnerTransactionHistoryService {
  PartnerTransactionHistoryService._();

  static final PartnerTransactionHistoryService instance =
      PartnerTransactionHistoryService._();

  static const Duration _timeout = Duration(seconds: 20);

  Future<PartnerTransactionHistoryPage> fetchHistory({
    String search = '',
    String dealType = '',
    String payoutState = '',
    int page = 1,
    int pageSize = 25,
  }) async {
    final query = <String, String>{
      'page': page.toString(),
      'page_size': pageSize.toString(),
    };

    if (search.trim().isNotEmpty) {
      query['search'] = search.trim();
    }

    if (dealType.trim().isNotEmpty) {
      query['deal_type'] = dealType.trim();
    }

    if (payoutState.trim().isNotEmpty) {
      query['payout_state'] = payoutState.trim();
    }

    final uri = Uri.parse(
      '${PropertyService.baseUrl}'
      '/api/partner/transaction-history/',
    ).replace(queryParameters: query);

    final response = await _sendAuthorizedRequest((accessToken) {
      return http
          .get(
            uri,
            headers: {
              'Accept': 'application/json',
              'Authorization': 'Bearer $accessToken',
            },
          )
          .timeout(_timeout);
    });

    final decoded = _decodeResponse(response);

    if (response.statusCode != 200) {
      throw Exception(
        _extractErrorMessage(
          decoded,
          fallback: 'Unable to load your transaction history.',
        ),
      );
    }

    if (decoded is! Map) {
      throw const FormatException(
        'The transaction history server returned '
        'an unexpected response.',
      );
    }

    return PartnerTransactionHistoryPage.fromJson(
      Map<String, dynamic>.from(decoded),
    );
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

  dynamic _decodeResponse(http.Response response) {
    if (response.body.trim().isEmpty) {
      return <String, dynamic>{};
    }

    try {
      return jsonDecode(response.body);
    } on FormatException {
      throw const FormatException(
        'The Pata Hao server returned '
        'an invalid response.',
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
