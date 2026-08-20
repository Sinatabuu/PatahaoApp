import 'dart:convert';

import 'package:http/http.dart' as http;

import 'package:mobile/services/auth_service.dart';
import 'package:mobile/services/property_service.dart';

class PartnerMandateService {
  PartnerMandateService._();

  static final PartnerMandateService instance = PartnerMandateService._();

  static const Duration _timeout = Duration(seconds: 30);

  Future<Map<String, dynamic>> fetchCommissionAgreementForProperty(
    int propertyId,
  ) async {
    _validateId(propertyId, 'propertyId');

    final uri = Uri.parse(
      '${PropertyService.baseUrl}'
      '/api/partner/commission-agreements/',
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
          fallback: 'Unable to load the commission agreement.',
        ),
      );
    }

    if (decoded is! List) {
      throw const FormatException(
        'The commission agreement server returned invalid data.',
      );
    }

    for (final item in decoded) {
      if (item is! Map) {
        continue;
      }

      final map = Map<String, dynamic>.from(item);

      final itemPropertyId = int.tryParse(map['property']?.toString() ?? '');

      if (itemPropertyId == propertyId) {
        return map;
      }
    }

    return <String, dynamic>{};
  }

  Future<Map<String, dynamic>> createCommissionAgreement({
    required int propertyId,
    required String ownerName,
    required String ownerPhoneNumber,
    required String commissionMethod,
    required String commissionBasis,
    required String transactionValue,
    String? commissionRate,
    String? fixedCommissionAmount,
  }) async {
    _validateId(propertyId, 'propertyId');

    final uri = Uri.parse(
      '${PropertyService.baseUrl}'
      '/api/partner/commission-agreements/',
    );

    final body = <String, dynamic>{
      'property': propertyId,
      'owner_name': ownerName.trim(),
      'owner_phone_number': ownerPhoneNumber.trim(),
      'commission_method': commissionMethod.trim(),
      'commission_basis': commissionBasis.trim(),
      'transaction_value': transactionValue.trim(),
      'commission_rate': _emptyToNull(commissionRate),
      'fixed_commission_amount': _emptyToNull(fixedCommissionAmount),
    };

    final response = await _sendAuthorizedRequest((accessToken) {
      return http
          .post(
            uri,
            headers: _jsonAuthorizationHeaders(accessToken),
            body: jsonEncode(body),
          )
          .timeout(_timeout);
    });

    final decoded = _decodeResponse(response);

    if (response.statusCode != 201) {
      throw Exception(
        _extractErrorMessage(
          decoded,
          fallback: 'Unable to create the commission agreement.',
        ),
      );
    }

    return _requireMap(
      decoded,
      message: 'The commission agreement server returned invalid data.',
    );
  }

  Future<Map<String, dynamic>> updateCommissionAgreement({
    required int agreementId,
    required String ownerName,
    required String ownerPhoneNumber,
    required String commissionMethod,
    required String commissionBasis,
    required String transactionValue,
    String? commissionRate,
    String? fixedCommissionAmount,
  }) async {
    _validateId(agreementId, 'agreementId');

    final uri = Uri.parse(
      '${PropertyService.baseUrl}'
      '/api/partner/commission-agreements/'
      '$agreementId/',
    );

    final body = <String, dynamic>{
      'owner_name': ownerName.trim(),
      'owner_phone_number': ownerPhoneNumber.trim(),
      'commission_method': commissionMethod.trim(),
      'commission_basis': commissionBasis.trim(),
      'transaction_value': transactionValue.trim(),
      'commission_rate': _emptyToNull(commissionRate),
      'fixed_commission_amount': _emptyToNull(fixedCommissionAmount),
    };

    final response = await _sendAuthorizedRequest((accessToken) {
      return http
          .patch(
            uri,
            headers: _jsonAuthorizationHeaders(accessToken),
            body: jsonEncode(body),
          )
          .timeout(_timeout);
    });

    final decoded = _decodeResponse(response);

    if (response.statusCode != 200) {
      throw Exception(
        _extractErrorMessage(
          decoded,
          fallback: 'Unable to update the commission agreement.',
        ),
      );
    }

    return _requireMap(
      decoded,
      message: 'The commission agreement server returned invalid data.',
    );
  }

  Future<Map<String, dynamic>> acceptCommissionAgreement(
    int agreementId,
  ) async {
    _validateId(agreementId, 'agreementId');

    final uri = Uri.parse(
      '${PropertyService.baseUrl}'
      '/api/partner/commission-agreements/'
      '$agreementId/accept/',
    );

    final response = await _sendAuthorizedRequest((accessToken) {
      return http
          .post(
            uri,
            headers: _jsonAuthorizationHeaders(accessToken),
            body: jsonEncode(<String, dynamic>{}),
          )
          .timeout(_timeout);
    });

    final decoded = _decodeResponse(response);

    if (response.statusCode != 200) {
      throw Exception(
        _extractErrorMessage(
          decoded,
          fallback: 'Unable to accept the commission agreement.',
        ),
      );
    }

    return _requireMap(
      decoded,
      message: 'The commission acceptance server returned invalid data.',
    );
  }

  Future<Map<String, dynamic>> fetchMandateForProperty(int propertyId) async {
    _validateId(propertyId, 'propertyId');

    final uri = Uri.parse(
      '${PropertyService.baseUrl}'
      '/api/mandates/',
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
          fallback: 'Unable to load the property mandate.',
        ),
      );
    }

    if (decoded is! List) {
      throw const FormatException('The mandate server returned invalid data.');
    }

    Map<String, dynamic>? latest;

    for (final item in decoded) {
      if (item is! Map) {
        continue;
      }

      final map = Map<String, dynamic>.from(item);

      final itemPropertyId = int.tryParse(map['property']?.toString() ?? '');

      if (itemPropertyId != propertyId) {
        continue;
      }

      if (latest == null) {
        latest = map;
        continue;
      }

      final latestVersion =
          int.tryParse(latest['version']?.toString() ?? '') ?? 0;

      final itemVersion = int.tryParse(map['version']?.toString() ?? '') ?? 0;

      if (itemVersion > latestVersion) {
        latest = map;
      }
    }

    return latest ?? <String, dynamic>{};
  }

  Future<Map<String, dynamic>> createMandate({
    required int propertyId,
    required String ownerName,
    required String ownerPhoneNumber,
    String ownerType = 'individual',
    required int commissionAgreementId,
    required String authorizationMethod,
    String authorizationNotes = '',
  }) async {
    _validateId(propertyId, 'propertyId');
    _validateId(commissionAgreementId, 'commissionAgreementId');

    final uri = Uri.parse(
      '${PropertyService.baseUrl}'
      '/api/mandates/',
    );

    final body = <String, dynamic>{
      'property': propertyId,
      'owner_name': ownerName.trim(),
      'owner_phone_number': ownerPhoneNumber.trim(),
      'owner_type': ownerType.trim(),
      'commission_agreement': commissionAgreementId,
      'authorization_method': authorizationMethod.trim(),
      'authorization_notes': authorizationNotes.trim(),
    };

    final response = await _sendAuthorizedRequest((accessToken) {
      return http
          .post(
            uri,
            headers: _jsonAuthorizationHeaders(accessToken),
            body: jsonEncode(body),
          )
          .timeout(_timeout);
    });

    final decoded = _decodeResponse(response);

    if (response.statusCode != 201) {
      throw Exception(
        _extractErrorMessage(
          decoded,
          fallback: 'Unable to create the property mandate.',
        ),
      );
    }

    return _requireMap(
      decoded,
      message: 'The mandate server returned invalid data.',
    );
  }

  Future<Map<String, dynamic>> declareMandate({
    required int mandateId,
    required String authorizationMethod,
    String authorizationNotes = '',
  }) async {
    _validateId(mandateId, 'mandateId');

    final uri = Uri.parse(
      '${PropertyService.baseUrl}'
      '/api/mandates/$mandateId/declare/',
    );

    final body = <String, dynamic>{
      'authorization_method': authorizationMethod.trim(),
      'authorization_notes': authorizationNotes.trim(),
      'owner_authority_confirmed': true,
      'no_cash_acknowledged': true,
      'anti_circumvention_acknowledged': true,
    };

    final response = await _sendAuthorizedRequest((accessToken) {
      return http
          .post(
            uri,
            headers: _jsonAuthorizationHeaders(accessToken),
            body: jsonEncode(body),
          )
          .timeout(_timeout);
    });

    final decoded = _decodeResponse(response);

    if (response.statusCode != 200) {
      throw Exception(
        _extractErrorMessage(
          decoded,
          fallback: 'Unable to accept the digital mandate.',
        ),
      );
    }

    return _requireMap(
      decoded,
      message: 'The mandate declaration server returned invalid data.',
    );
  }

  Future<Map<String, dynamic>> submitMandateForReview(int mandateId) async {
    _validateId(mandateId, 'mandateId');

    final uri = Uri.parse(
      '${PropertyService.baseUrl}'
      '/api/mandates/$mandateId/'
      'submit-for-review/',
    );

    final response = await _sendAuthorizedRequest((accessToken) {
      return http
          .post(
            uri,
            headers: _jsonAuthorizationHeaders(accessToken),
            body: jsonEncode(<String, dynamic>{}),
          )
          .timeout(_timeout);
    });

    final decoded = _decodeResponse(response);

    if (response.statusCode != 200) {
      throw Exception(
        _extractErrorMessage(
          decoded,
          fallback: 'Unable to submit the mandate for review.',
        ),
      );
    }

    return _requireMap(
      decoded,
      message: 'The mandate review server returned invalid data.',
    );
  }

  Future<http.Response> _sendAuthorizedRequest(
    Future<http.Response> Function(String accessToken) requestBuilder,
  ) async {
    var accessToken = await AuthService.instance.getAccessToken();

    if (accessToken == null || accessToken.isEmpty) {
      throw Exception('Please sign in to continue.');
    }

    var response = await requestBuilder(accessToken);

    if (response.statusCode != 401) {
      return response;
    }

    accessToken = await AuthService.instance.refreshAccessToken();

    if (accessToken == null || accessToken.isEmpty) {
      throw Exception(
        'Your session has expired. '
        'Please sign in again.',
      );
    }

    return requestBuilder(accessToken);
  }

  Map<String, String> _authorizationHeaders(String accessToken) {
    return <String, String>{
      'Accept': 'application/json',
      'Authorization': 'Bearer $accessToken',
    };
  }

  Map<String, String> _jsonAuthorizationHeaders(String accessToken) {
    return <String, String>{
      ..._authorizationHeaders(accessToken),
      'Content-Type': 'application/json',
    };
  }

  dynamic _decodeResponse(http.Response response) {
    if (response.body.trim().isEmpty) {
      return null;
    }

    try {
      return jsonDecode(response.body);
    } on FormatException {
      throw const FormatException('The server returned an invalid response.');
    }
  }

  Map<String, dynamic> _requireMap(dynamic decoded, {required String message}) {
    if (decoded is! Map) {
      throw FormatException(message);
    }

    return Map<String, dynamic>.from(decoded);
  }

  String _extractErrorMessage(dynamic decoded, {required String fallback}) {
    if (decoded is Map) {
      final detail = decoded['detail'];

      if (detail != null && detail.toString().trim().isNotEmpty) {
        return detail.toString().trim();
      }

      final message = decoded['message'];

      if (message != null && message.toString().trim().isNotEmpty) {
        return message.toString().trim();
      }

      final errors = <String>[];

      decoded.forEach((dynamic key, dynamic value) {
        if (value == null) {
          return;
        }

        if (value is List) {
          for (final item in value) {
            final text = item.toString().trim();

            if (text.isNotEmpty) {
              errors.add(text);
            }
          }

          return;
        }

        final text = value.toString().trim();

        if (text.isNotEmpty) {
          errors.add(text);
        }
      });

      if (errors.isNotEmpty) {
        return errors.join('\n');
      }
    }

    if (decoded is List) {
      final errors = decoded
          .map((item) => item.toString().trim())
          .where((item) => item.isNotEmpty)
          .toList();

      if (errors.isNotEmpty) {
        return errors.join('\n');
      }
    }

    return fallback;
  }

  void _validateId(int value, String name) {
    if (value <= 0) {
      throw ArgumentError('$name must be greater than zero.');
    }
  }

  String? _emptyToNull(String? value) {
    final cleaned = value?.trim() ?? '';

    return cleaned.isEmpty ? null : cleaned;
  }
}
