import 'dart:convert';

import 'package:http/http.dart' as http;

import '../models/partner_dashboard.dart';
import '../models/viewing.dart';
import 'auth_service.dart';
import 'property_service.dart';

class PartnerService {
  PartnerService._();

  static final PartnerService instance = PartnerService._();

  static const Duration _timeout = Duration(seconds: 20);

  Future<PartnerDashboard> fetchDashboard() async {
    final response = await _authenticatedRequest(
      method: 'GET',
      path: '/api/partners/dashboard/',
    );

    final decoded = _decodeResponse(response.body);

    if (response.statusCode != 200) {
      throw Exception(
        _extractErrorMessage(
          decoded,
          fallback: 'Unable to load the partner dashboard.',
        ),
      );
    }

    if (decoded is! Map) {
      throw const FormatException(
        'The partner dashboard returned an unexpected response.',
      );
    }

    return PartnerDashboard.fromJson(
      Map<String, dynamic>.from(decoded),
    );
  }

  Future<List<Viewing>> fetchViewings({
    String? status,
  }) async {
    final queryParameters = <String, String>{};

    if (status != null && status.trim().isNotEmpty) {
      queryParameters['status'] = status.trim();
    }

    final response = await _authenticatedRequest(
      method: 'GET',
      path: '/api/partners/viewings/',
      queryParameters: queryParameters,
    );

    final decoded = _decodeResponse(response.body);

    if (response.statusCode != 200) {
      throw Exception(
        _extractErrorMessage(
          decoded,
          fallback: 'Unable to load partner viewings.',
        ),
      );
    }

    if (decoded is! List) {
      throw const FormatException(
        'The partner viewings endpoint returned an unexpected response.',
      );
    }

    return decoded
        .whereType<Map>()
        .map(
          (item) => Viewing.fromJson(
            Map<String, dynamic>.from(item),
          ),
        )
        .toList();
  }

  Future<List<Viewing>> fetchTodayViewings() async {
    final response = await _authenticatedRequest(
      method: 'GET',
      path: '/api/partners/viewings/today/',
    );

    final decoded = _decodeResponse(response.body);

    if (response.statusCode != 200) {
      throw Exception(
        _extractErrorMessage(
          decoded,
          fallback: 'Unable to load today\'s viewings.',
        ),
      );
    }

    if (decoded is List) {
      return _parseViewingList(decoded);
    }

    if (decoded is Map) {
      final viewings = decoded['viewings'];

      if (viewings is List) {
        return _parseViewingList(viewings);
      }
    }

    throw const FormatException(
      'Today\'s viewings endpoint returned an unexpected response.',
    );
  }

  Future<List<PartnerDashboardProperty>> fetchProperties() async {
    final response = await _authenticatedRequest(
      method: 'GET',
      path: '/api/partners/properties/',
    );

    final decoded = _decodeResponse(response.body);

    if (response.statusCode != 200) {
      throw Exception(
        _extractErrorMessage(
          decoded,
          fallback: 'Unable to load partner properties.',
        ),
      );
    }

    if (decoded is! List) {
      throw const FormatException(
        'The partner properties endpoint returned an unexpected response.',
      );
    }

    return decoded
        .whereType<Map>()
        .map(
          (item) => PartnerDashboardProperty.fromJson(
            Map<String, dynamic>.from(item),
          ),
        )
        .toList();
  }

  Future<Viewing> confirmViewing({
    required int viewingId,
    String? confirmedDate,
    String? confirmedTime,
    String partnerResponseMessage = '',
  }) async {
    final body = <String, dynamic>{
      'partner_response_message': partnerResponseMessage.trim(),
    };

    if (confirmedDate != null && confirmedDate.trim().isNotEmpty) {
      body['confirmed_date'] = confirmedDate.trim();
    }

    if (confirmedTime != null && confirmedTime.trim().isNotEmpty) {
      body['confirmed_time'] = confirmedTime.trim();
    }

    return _performViewingAction(
      path: '/api/partners/viewings/$viewingId/confirm/',
      body: body,
      fallbackError: 'Unable to confirm this viewing.',
    );
  }

  Future<Viewing> rescheduleViewing({
    required int viewingId,
    required String proposedDate,
    required String proposedTime,
    required String partnerResponseMessage,
  }) {
    return _performViewingAction(
      path: '/api/partners/viewings/$viewingId/reschedule/',
      body: {
        'proposed_date': proposedDate.trim(),
        'proposed_time': proposedTime.trim(),
        'partner_response_message': partnerResponseMessage.trim(),
      },
      fallbackError: 'Unable to propose another viewing time.',
    );
  }

  Future<Viewing> declineViewing({
    required int viewingId,
    required String reason,
  }) {
    return _performViewingAction(
      path: '/api/partners/viewings/$viewingId/decline/',
      body: {
        'partner_response_message': reason.trim(),
      },
      fallbackError: 'Unable to decline this viewing.',
    );
  }

  Future<Viewing> markEnRoute({
    required int viewingId,
    String notes = '',
  }) {
    return _performViewingAction(
      path: '/api/partners/viewings/$viewingId/en-route/',
      body: {
        'notes': notes.trim(),
      },
      fallbackError: 'Unable to mark the partner as en route.',
    );
  }

  Future<Viewing> markArrived({
    required int viewingId,
    String notes = '',
  }) {
    return _performViewingAction(
      path: '/api/partners/viewings/$viewingId/arrived/',
      body: {
        'notes': notes.trim(),
      },
      fallbackError: 'Unable to mark the partner as arrived.',
    );
  }

  Future<Viewing> startViewing({
    required int viewingId,
    String notes = '',
  }) {
    return _performViewingAction(
      path: '/api/partners/viewings/$viewingId/start/',
      body: {
        'notes': notes.trim(),
      },
      fallbackError: 'Unable to start this viewing.',
    );
  }

  Future<Viewing> completeViewing({
    required int viewingId,
    String completionNotes = '',
  }) {
    return _performViewingAction(
      path: '/api/partners/viewings/$viewingId/complete/',
      body: {
        'completion_notes': completionNotes.trim(),
      },
      fallbackError: 'Unable to complete this viewing.',
    );
  }

  Future<Viewing> _performViewingAction({
    required String path,
    required Map<String, dynamic> body,
    required String fallbackError,
  }) async {
    final response = await _authenticatedRequest(
      method: 'POST',
      path: path,
      body: body,
    );

    final decoded = _decodeResponse(response.body);

    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw Exception(
        _extractErrorMessage(
          decoded,
          fallback: fallbackError,
        ),
      );
    }

    if (decoded is! Map) {
      throw const FormatException(
        'The viewing action returned an unexpected response.',
      );
    }

    final responseMap = Map<String, dynamic>.from(decoded);
    final viewingData = responseMap['viewing'];

    // Confirm, reschedule, and decline return:
    // {"detail": "...", "viewing": {...}}
    if (viewingData is Map) {
      return Viewing.fromJson(
        Map<String, dynamic>.from(viewingData),
      );
    }

    // Operational endpoints return the viewing object directly.
    return Viewing.fromJson(responseMap);
  }

  Future<http.Response> _authenticatedRequest({
    required String method,
    required String path,
    Map<String, String>? queryParameters,
    Map<String, dynamic>? body,
  }) async {
    var accessToken = await AuthService.instance.getAccessToken();

    if (accessToken == null || accessToken.isEmpty) {
      throw Exception('Your session has expired. Please sign in again.');
    }

    var response = await _sendRequest(
      method: method,
      path: path,
      accessToken: accessToken,
      queryParameters: queryParameters,
      body: body,
    );

    if (response.statusCode != 401) {
      return response;
    }

    accessToken = await AuthService.instance.refreshAccessToken();

    if (accessToken == null || accessToken.isEmpty) {
      throw Exception('Your session has expired. Please sign in again.');
    }

    response = await _sendRequest(
      method: method,
      path: path,
      accessToken: accessToken,
      queryParameters: queryParameters,
      body: body,
    );

    return response;
  }

  Future<http.Response> _sendRequest({
    required String method,
    required String path,
    required String accessToken,
    Map<String, String>? queryParameters,
    Map<String, dynamic>? body,
  }) {
    final baseUri = Uri.parse('${PropertyService.baseUrl}$path');

    final uri = baseUri.replace(
      queryParameters:
          queryParameters == null || queryParameters.isEmpty
          ? null
          : queryParameters,
    );

    final headers = <String, String>{
      'Accept': 'application/json',
      'Authorization': 'Bearer $accessToken',
    };

    if (body != null) {
      headers['Content-Type'] = 'application/json';
    }

    switch (method.toUpperCase()) {
      case 'GET':
        return http.get(uri, headers: headers).timeout(_timeout);

      case 'POST':
        return http
            .post(
              uri,
              headers: headers,
              body: body == null ? null : jsonEncode(body),
            )
            .timeout(_timeout);

      default:
        throw UnsupportedError(
          'Unsupported HTTP method: $method',
        );
    }
  }

  List<Viewing> _parseViewingList(List<dynamic> values) {
    return values
        .whereType<Map>()
        .map(
          (item) => Viewing.fromJson(
            Map<String, dynamic>.from(item),
          ),
        )
        .toList();
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

  String _extractErrorMessage(
    dynamic decoded, {
    required String fallback,
  }) {
    if (decoded is Map) {
      final map = Map<String, dynamic>.from(decoded);
      final detail = map['detail'];

      if (detail != null && detail.toString().trim().isNotEmpty) {
        return detail.toString();
      }

      final messages = <String>[];

      for (final entry in map.entries) {
        final value = entry.value;

        if (value is List) {
          final message = value
              .map((item) => item.toString())
              .join(', ');

          if (message.isNotEmpty) {
            messages.add(message);
          }
        } else if (value is Map) {
          messages.add(
            value.values.map((item) => item.toString()).join(', '),
          );
        } else if (value != null &&
            value.toString().trim().isNotEmpty) {
          messages.add(value.toString());
        }
      }

      if (messages.isNotEmpty) {
        return messages.join('\n');
      }
    }

    return fallback;
  }
}