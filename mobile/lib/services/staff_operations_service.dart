import 'dart:convert';

import 'package:http/http.dart' as http;

import 'package:mobile/services/auth_service.dart';
import 'package:mobile/services/property_service.dart';

class StaffOperationsService {
  StaffOperationsService._();

  static final StaffOperationsService instance = StaffOperationsService._();

  static const Duration _timeout = Duration(seconds: 30);

  Future<StaffOperationsSummary> fetchSummary() async {
    final uri = Uri.parse(
      '${PropertyService.baseUrl}/api/admin/operations-summary/',
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
          fallback: 'Unable to load Pata Hao operations.',
        ),
      );
    }

    if (decoded is! Map) {
      throw const FormatException(
        'The operations dashboard returned invalid data.',
      );
    }

    return StaffOperationsSummary.fromJson(Map<String, dynamic>.from(decoded));
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

      if (detail is Map && detail.isNotEmpty) {
        return detail.values
            .expand((value) {
              if (value is List) {
                return value;
              }

              return [value];
            })
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
}

class StaffOperationsSummary {
  const StaffOperationsSummary({
    required this.pendingReviews,
    required this.publishedProperties,
    required this.activePartners,
    required this.todaysViewings,
    required this.openDeals,
    required this.commissionActivity,
    required this.generatedForDate,
  });

  final int pendingReviews;
  final int publishedProperties;
  final int activePartners;
  final int todaysViewings;
  final int openDeals;
  final int commissionActivity;
  final String generatedForDate;

  factory StaffOperationsSummary.fromJson(Map<String, dynamic> json) {
    return StaffOperationsSummary(
      pendingReviews: _parseInt(json['pending_reviews']),
      publishedProperties: _parseInt(json['published_properties']),
      activePartners: _parseInt(json['active_partners']),
      todaysViewings: _parseInt(json['todays_viewings']),
      openDeals: _parseInt(json['open_deals']),
      commissionActivity: _parseInt(json['commission_activity']),
      generatedForDate: json['generated_for_date']?.toString() ?? '',
    );
  }

  static int _parseInt(dynamic value) {
    if (value is int) {
      return value;
    }

    if (value is num) {
      return value.toInt();
    }

    return int.tryParse(value?.toString() ?? '') ?? 0;
  }
}
