import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

import '../models/payment.dart';
import 'auth_service.dart';
import 'property_service.dart';

class PaymentService {
  /// Loads all payments belonging to the authenticated customer.
  Future<List<Payment>> fetchPayments() async {
    final token = await _validAccessToken();

    final uri = Uri.parse('${PropertyService.baseUrl}/api/payments/');

    debugPrint('PAYMENTS REQUEST: $uri');

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

    debugPrint('PAYMENTS STATUS: ${response.statusCode}');

    if (response.statusCode != 200) {
      throw Exception(
        _extractError(
          decoded,
          fallback: 'Unable to load your payment history.',
        ),
      );
    }

    if (decoded is List) {
      return decoded
          .whereType<Map>()
          .map((item) => Payment.fromJson(Map<String, dynamic>.from(item)))
          .toList();
    }

    if (decoded is Map) {
      final decodedMap = Map<String, dynamic>.from(decoded);

      final results = decodedMap['results'];

      if (results is List) {
        return results
            .whereType<Map>()
            .map((item) => Payment.fromJson(Map<String, dynamic>.from(item)))
            .toList();
      }
    }

    throw const FormatException(
      'The payments API returned an unexpected format.',
    );
  }

  /// Creates a pending M-Pesa payment record for a viewing.
  Future<Payment> createPayment({
    required int viewingId,
    required String phoneNumber,
  }) async {
    final token = await _validAccessToken();
    final normalizedPhone = _normalizePhoneNumber(phoneNumber);

    final requestBody = <String, dynamic>{
      'viewing': viewingId,
      'phone_number': normalizedPhone,
      'provider': 'mpesa',
    };

    debugPrint('CREATE PAYMENT REQUEST: ${jsonEncode(requestBody)}');

    final response = await http
        .post(
          Uri.parse('${PropertyService.baseUrl}/api/payments/'),
          headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Authorization': 'Bearer $token',
          },
          body: jsonEncode(requestBody),
        )
        .timeout(const Duration(seconds: 30));

    final decoded = _decode(response.body);

    debugPrint('CREATE PAYMENT STATUS: ${response.statusCode}');
    debugPrint('CREATE PAYMENT RESPONSE: ${response.body}');

    if ((response.statusCode == 200 || response.statusCode == 201) &&
        decoded is Map<String, dynamic>) {
      return Payment.fromJson(decoded);
    }

    throw Exception(
      _extractError(decoded, fallback: 'Unable to create the M-Pesa payment.'),
    );
  }

  /// Sends the real Safaricom M-Pesa STK Push.
  Future<Payment> initiateMpesaPayment({required int paymentId}) async {
    final token = await _validAccessToken();

    final response = await http
        .post(
          Uri.parse(
            '${PropertyService.baseUrl}/api/payments/'
            '$paymentId/initiate/',
          ),
          headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Authorization': 'Bearer $token',
          },
          body: jsonEncode(<String, dynamic>{}),
        )
        .timeout(const Duration(seconds: 45));

    final decoded = _decode(response.body);

    debugPrint('INITIATE M-PESA STATUS: ${response.statusCode}');
    debugPrint('INITIATE M-PESA RESPONSE: ${response.body}');

    if ((response.statusCode == 200 || response.statusCode == 201) &&
        decoded is Map<String, dynamic>) {
      final nestedPayment = decoded['payment'];

      if (nestedPayment is Map<String, dynamic>) {
        return Payment.fromJson(nestedPayment);
      }

      return Payment.fromJson(decoded);
    }

    throw Exception(
      _extractError(decoded, fallback: 'Unable to send the M-Pesa request.'),
    );
  }

  /// Loads the latest payment state from Django.
  Future<Payment> getPayment({required int paymentId}) async {
    final token = await _validAccessToken();

    final response = await http
        .get(
          Uri.parse('${PropertyService.baseUrl}/api/payments/$paymentId/'),
          headers: {
            'Accept': 'application/json',
            'Authorization': 'Bearer $token',
          },
        )
        .timeout(const Duration(seconds: 30));

    final decoded = _decode(response.body);

    debugPrint('GET PAYMENT STATUS: ${response.statusCode}');
    debugPrint('GET PAYMENT RESPONSE: ${response.body}');

    if (response.statusCode == 200 && decoded is Map<String, dynamic>) {
      return Payment.fromJson(decoded);
    }

    throw Exception(
      _extractError(
        decoded,
        fallback: 'Unable to check the M-Pesa payment status.',
      ),
    );
  }

  /// Loads the official receipt for a paid viewing.
  Future<Payment> getViewingReceipt({required int viewingId}) async {
    final token = await _validAccessToken();

    final response = await http
        .get(
          Uri.parse(
            '${PropertyService.baseUrl}/api/viewings/'
            '$viewingId/receipt/',
          ),
          headers: {
            'Accept': 'application/json',
            'Authorization': 'Bearer $token',
          },
        )
        .timeout(const Duration(seconds: 30));

    final decoded = _decode(response.body);

    debugPrint('GET RECEIPT STATUS: ${response.statusCode}');
    debugPrint('GET RECEIPT RESPONSE: ${response.body}');

    if (response.statusCode == 200 && decoded is Map<String, dynamic>) {
      return Payment.fromJson(decoded);
    }

    throw Exception(
      _extractError(decoded, fallback: 'Unable to load the viewing receipt.'),
    );
  }

  Future<String> _validAccessToken() async {
    final token = await AuthService.instance.getAccessToken();

    if (token == null || token.trim().isEmpty) {
      throw Exception('Please log in before making a payment.');
    }

    return token;
  }

  String _normalizePhoneNumber(String value) {
    var number = value.replaceAll(RegExp(r'[^0-9]'), '');

    if (number.startsWith('0') && number.length == 10) {
      number = '254${number.substring(1)}';
    }

    if (number.startsWith('7') && number.length == 9) {
      number = '254$number';
    }

    if (number.startsWith('1') && number.length == 9) {
      number = '254$number';
    }

    final isValid = RegExp(r'^254(7|1)\d{8}$').hasMatch(number);

    if (!isValid) {
      throw Exception(
        'Enter a valid Kenyan phone number, '
        'for example 0712345678.',
      );
    }

    return number;
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

  String _extractError(dynamic decoded, {required String fallback}) {
    if (decoded is Map<String, dynamic>) {
      final detail = decoded['detail'];

      if (detail != null && detail.toString().trim().isNotEmpty) {
        return detail.toString();
      }

      final messages = <String>[];

      for (final entry in decoded.entries) {
        final value = entry.value;

        if (value is List) {
          messages.add(
            '${entry.key}: '
            '${value.map((item) => item.toString()).join(', ')}',
          );
        } else if (value is Map) {
          messages.add('${entry.key}: ${jsonEncode(value)}');
        } else if (value != null) {
          messages.add('${entry.key}: $value');
        }
      }

      if (messages.isNotEmpty) {
        return messages.join('\n');
      }
    }

    return fallback;
  }
}
