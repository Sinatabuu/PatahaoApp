import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

import '../models/notification.dart';
import 'auth_service.dart';
import 'property_service.dart';

class NotificationService {
  const NotificationService();

  Future<List<AppNotification>> fetchNotifications() async {
    final token = await _token();
    final uri = Uri.parse('${PropertyService.baseUrl}/api/notifications/');

    debugPrint('NOTIFICATIONS REQUEST: $uri');

    final response = await http
        .get(
          uri,
          headers: {
            'Accept': 'application/json',
            'Authorization': 'Bearer $token',
          },
        )
        .timeout(const Duration(seconds: 30));

    final decoded = _decode(response.body);

    if (response.statusCode != 200) {
      throw Exception(
        _error(decoded, fallback: 'Unable to load notifications.'),
      );
    }

    final List<dynamic> items;

    if (decoded is List) {
      items = decoded;
    } else if (decoded is Map && decoded['results'] is List) {
      items = decoded['results'] as List<dynamic>;
    } else {
      throw const FormatException(
        'Notifications API returned an unexpected format.',
      );
    }

    return items
        .whereType<Map>()
        .map(
          (item) => AppNotification.fromJson(Map<String, dynamic>.from(item)),
        )
        .toList();
  }

  Future<AppNotification> markAsRead({required int notificationId}) async {
    final token = await _token();
    final uri = Uri.parse(
      '${PropertyService.baseUrl}/api/notifications/'
      '$notificationId/mark-read/',
    );

    final response = await http
        .post(
          uri,
          headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Authorization': 'Bearer $token',
          },
          body: jsonEncode(<String, dynamic>{}),
        )
        .timeout(const Duration(seconds: 30));

    final decoded = _decode(response.body);

    if (response.statusCode == 200 && decoded is Map) {
      return AppNotification.fromJson(Map<String, dynamic>.from(decoded));
    }

    throw Exception(
      _error(decoded, fallback: 'Unable to mark notification as read.'),
    );
  }

  Future<int> markAllAsRead() async {
    final token = await _token();
    final uri = Uri.parse(
      '${PropertyService.baseUrl}/api/notifications/'
      'mark-all-read/',
    );

    final response = await http
        .post(
          uri,
          headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Authorization': 'Bearer $token',
          },
          body: jsonEncode(<String, dynamic>{}),
        )
        .timeout(const Duration(seconds: 30));

    final decoded = _decode(response.body);

    if (response.statusCode == 200 && decoded is Map) {
      final value = decoded['updated_count'];
      if (value is int) return value;
      return int.tryParse(value?.toString() ?? '') ?? 0;
    }

    throw Exception(
      _error(decoded, fallback: 'Unable to mark all notifications as read.'),
    );
  }

  Future<String> _token() async {
    var token = await AuthService.instance.getAccessToken();

    if (token == null || token.trim().isEmpty) {
      throw Exception('Please log in to view notifications.');
    }

    return token.trim();
  }

  dynamic _decode(String body) {
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

  String _error(dynamic decoded, {required String fallback}) {
    if (decoded is Map) {
      final detail = decoded['detail'];
      if (detail != null && detail.toString().trim().isNotEmpty) {
        return detail.toString();
      }
    }

    return fallback;
  }
}
