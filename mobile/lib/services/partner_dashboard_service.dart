import 'dart:convert';

import 'package:http/http.dart' as http;

import 'package:mobile/models/partner_dashboard.dart';
import 'package:mobile/services/auth_service.dart';
import 'package:flutter/foundation.dart';
import 'package:mobile/services/property_service.dart';

class PartnerDashboardService {
  PartnerDashboardService._();

  static final PartnerDashboardService instance = PartnerDashboardService._();

  static const Duration _requestTimeout = Duration(seconds: 20);

  Future<PartnerDashboard> getDashboard() async {
    final response = await _authenticatedRequest(
      method: 'GET',
      path: '/api/partners/dashboard/',
    );
    debugPrint('===================================');
    debugPrint('PARTNER DASHBOARD STATUS: ${response.statusCode}');
    debugPrint(response.body);
    debugPrint('===================================');
    final dynamic decoded = _decodeResponse(response.body);

    if (response.statusCode != 200) {
      throw Exception(
        _extractErrorMessage(
          decoded,
          fallback: 'Unable to load the partner dashboard.',
        ),
      );
    }

    if (decoded is! Map<String, dynamic>) {
      throw const FormatException(
        'The dashboard server returned an unexpected response.',
      );
    }

    return PartnerDashboard.fromJson(decoded);
  }

  Future<PartnerDashboardViewing> getViewing(int viewingId) async {
    final response = await _authenticatedRequest(
      method: 'GET',
      path: '/api/viewings/partner-inbox/',
    );

    final dynamic decoded = _decodeResponse(response.body);

    if (response.statusCode != 200) {
      throw Exception(
        _extractErrorMessage(decoded, fallback: 'Unable to load the viewing.'),
      );
    }

    final List<dynamic> rawViewings;

    if (decoded is List<dynamic>) {
      rawViewings = decoded;
    } else if (decoded is Map<String, dynamic> &&
        decoded['results'] is List<dynamic>) {
      rawViewings = decoded['results'] as List<dynamic>;
    } else if (decoded is Map<String, dynamic> &&
        decoded['viewings'] is List<dynamic>) {
      rawViewings = decoded['viewings'] as List<dynamic>;
    } else {
      throw const FormatException(
        'The server returned an unexpected viewing response.',
      );
    }

    for (final item in rawViewings) {
      if (item is! Map) continue;

      final json = Map<String, dynamic>.from(item);
      final itemId = int.tryParse(json['id']?.toString() ?? '');

      if (itemId == viewingId) {
        return PartnerDashboardViewing.fromJson(json);
      }
    }

    throw Exception(
      'This viewing could not be found or is no longer assigned to you.',
    );
  }

  Future<void> confirmViewing(int viewingId) async {
    final response = await _authenticatedRequest(
      method: 'POST',
      path: '/api/viewings/$viewingId/accept/',
      body: const <String, dynamic>{},
    );

    _ensureActionSucceeded(
      response,
      fallback: 'Unable to confirm this viewing.',
    );
  }

  Future<void> rescheduleViewing({
    required int viewingId,
    required String proposedDate,
    required String proposedTime,
    required String reason,
  }) async {
    final response = await _authenticatedRequest(
      method: 'POST',
      path: '/api/viewings/$viewingId/propose-reschedule/',
      body: <String, dynamic>{
        'proposed_date': proposedDate,
        'proposed_time': proposedTime,
        'partner_response_message': reason.trim(),
      },
    );

    _ensureActionSucceeded(
      response,
      fallback: 'Unable to suggest a new viewing time.',
    );
  }

  Future<void> declineViewing({
    required int viewingId,
    required String reason,
  }) async {
    final response = await _authenticatedRequest(
      method: 'POST',
      path: '/api/viewings/$viewingId/decline/',
      body: <String, dynamic>{'partner_response_message': reason.trim()},
    );

    _ensureActionSucceeded(
      response,
      fallback: 'Unable to decline this viewing request.',
    );
  }

  Future<void> markEnRoute({required int viewingId, String notes = ''}) async {
    final response = await _authenticatedRequest(
      method: 'POST',
      path: '/api/viewings/$viewingId/partner-en-route/',
      body: <String, dynamic>{'notes': notes.trim()},
    );

    _ensureActionSucceeded(
      response,
      fallback: 'Unable to mark the partner as en route.',
    );
  }

  Future<void> markArrived({required int viewingId, String notes = ''}) async {
    final response = await _authenticatedRequest(
      method: 'POST',
      path: '/api/viewings/$viewingId/partner-arrived/',
      body: <String, dynamic>{'notes': notes.trim()},
    );

    _ensureActionSucceeded(
      response,
      fallback: 'Unable to record the partner arrival.',
    );
  }

  Future<void> startViewing({required int viewingId, String notes = ''}) async {
    final response = await _authenticatedRequest(
      method: 'POST',
      path: '/api/viewings/$viewingId/start-viewing/',
      body: <String, dynamic>{'notes': notes.trim()},
    );

    _ensureActionSucceeded(response, fallback: 'Unable to start this viewing.');
  }

  Future<void> completeViewing({
    required int viewingId,
    required String completionNotes,
  }) async {
    final response = await _authenticatedRequest(
      method: 'POST',
      path: '/api/viewings/$viewingId/complete-viewing/',
      body: <String, dynamic>{'completion_notes': completionNotes.trim()},
    );

    _ensureActionSucceeded(
      response,
      fallback: 'Unable to complete this viewing.',
    );
  }

  Future<http.Response> _authenticatedRequest({
    required String method,
    required String path,
    Map<String, dynamic>? body,
  }) async {
    String? accessToken = await AuthService.instance.getAccessToken();

    if (accessToken == null || accessToken.isEmpty) {
      throw Exception('You are not logged in. Please log in again.');
    }

    http.Response response = await _sendRequest(
      method: method,
      path: path,
      accessToken: accessToken,
      body: body,
    );

    if (response.statusCode == 401) {
      accessToken = await AuthService.instance.refreshAccessToken();

      if (accessToken == null || accessToken.isEmpty) {
        throw Exception('Your session has expired. Please log in again.');
      }

      response = await _sendRequest(
        method: method,
        path: path,
        accessToken: accessToken,
        body: body,
      );
    }

    return response;
  }

  Future<http.Response> _sendRequest({
    required String method,
    required String path,
    required String accessToken,
    Map<String, dynamic>? body,
  }) {
    final uri = Uri.parse('${PropertyService.baseUrl}$path');

    final headers = <String, String>{
      'Accept': 'application/json',
      'Authorization': 'Bearer $accessToken',
    };

    switch (method.toUpperCase()) {
      case 'POST':
        headers['Content-Type'] = 'application/json';

        return http
            .post(
              uri,
              headers: headers,
              body: jsonEncode(body ?? const <String, dynamic>{}),
            )
            .timeout(_requestTimeout);

      case 'GET':
        return http.get(uri, headers: headers).timeout(_requestTimeout);

      default:
        throw UnsupportedError('Unsupported HTTP method: $method');
    }
  }

  void _ensureActionSucceeded(
    http.Response response, {
    required String fallback,
  }) {
    final dynamic decoded = _decodeResponse(response.body);

    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw Exception(_extractErrorMessage(decoded, fallback: fallback));
    }
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
          final errorText = value
              .map((item) => item.toString().trim())
              .where((item) => item.isNotEmpty)
              .join(', ');

          if (errorText.isNotEmpty) {
            errors.add(errorText);
          }
        } else if (value is Map) {
          final nestedText = value.values
              .expand((item) => item is List ? item : <dynamic>[item])
              .map((item) => item.toString().trim())
              .where((item) => item.isNotEmpty)
              .join(', ');

          if (nestedText.isNotEmpty) {
            errors.add(nestedText);
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
