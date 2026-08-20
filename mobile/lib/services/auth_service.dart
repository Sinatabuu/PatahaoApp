import 'dart:convert';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;

import 'package:mobile/services/property_service.dart';

class AuthService {
  AuthService._();

  static final AuthService instance = AuthService._();

  static const FlutterSecureStorage _storage = FlutterSecureStorage();

  static const String _accessTokenKey = 'pata_hao_access_token';
  static const String _refreshTokenKey = 'pata_hao_refresh_token';

  static const Duration _timeout = Duration(seconds: 20);

  Future<void> login({
    required String username,
    required String password,
  }) async {
    final uri = Uri.parse('${PropertyService.baseUrl}/api/auth/login/');

    final response = await http
        .post(
          uri,
          headers: const {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
          },
          body: jsonEncode({'username': username.trim(), 'password': password}),
        )
        .timeout(_timeout);

    final dynamic decoded = _decodeResponse(response.body);

    if (response.statusCode != 200) {
      throw Exception(
        _extractErrorMessage(
          decoded,
          fallback: 'Login failed. Check your username and password.',
        ),
      );
    }

    if (decoded is! Map<String, dynamic>) {
      throw const FormatException(
        'The login server returned an unexpected response.',
      );
    }

    final accessToken = decoded['access']?.toString() ?? '';
    final refreshToken = decoded['refresh']?.toString() ?? '';

    if (accessToken.isEmpty || refreshToken.isEmpty) {
      throw const FormatException(
        'The login response did not contain valid tokens.',
      );
    }

    await Future.wait([
      _storage.write(key: _accessTokenKey, value: accessToken),
      _storage.write(key: _refreshTokenKey, value: refreshToken),
    ]);
  }

  Future<AuthUser> registerCustomer({
    required String username,
    required String email,
    required String phoneNumber,
    required String fullName,
    required String password,
    required String passwordConfirm,
  }) async {
    final uri = Uri.parse('${PropertyService.baseUrl}/api/auth/register/');

    final response = await http
        .post(
          uri,
          headers: const {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
          },
          body: jsonEncode({
            'username': username.trim(),
            'email': email.trim(),
            'phone_number': phoneNumber.trim().isEmpty
                ? null
                : phoneNumber.trim(),
            'full_name': fullName.trim(),
            'password': password,
            'password_confirm': passwordConfirm,
          }),
        )
        .timeout(_timeout);

    final dynamic decoded = _decodeResponse(response.body);

    if (response.statusCode != 201) {
      throw Exception(
        _extractErrorMessage(
          decoded,
          fallback: 'Unable to create your account.',
        ),
      );
    }

    if (decoded is! Map) {
      throw const FormatException(
        'The registration server returned an unexpected response.',
      );
    }

    final decodedMap = Map<String, dynamic>.from(decoded);
    final userData = decodedMap['user'];

    if (userData is! Map) {
      throw const FormatException(
        'The registration response did not contain a valid user.',
      );
    }

    return AuthUser.fromJson(Map<String, dynamic>.from(userData));
  }

  Future<AuthUser> getCurrentUser() async {
    var accessToken = await getAccessToken();

    if (accessToken == null || accessToken.isEmpty) {
      throw Exception('Please sign in to continue.');
    }

    var response = await _fetchCurrentUser(accessToken);

    if (response.statusCode == 401) {
      accessToken = await refreshAccessToken();

      if (accessToken == null || accessToken.isEmpty) {
        throw Exception('Your session has expired. Please sign in again.');
      }

      response = await _fetchCurrentUser(accessToken);
    }

    final dynamic decoded = _decodeResponse(response.body);

    if (response.statusCode != 200) {
      throw Exception(
        _extractErrorMessage(decoded, fallback: 'Unable to load your account.'),
      );
    }

    if (decoded is! Map) {
      throw const FormatException(
        'The account server returned an unexpected response.',
      );
    }

    return AuthUser.fromJson(Map<String, dynamic>.from(decoded));
  }

  Future<AuthUser> updatePhoneNumber({required String phoneNumber}) async {
    var accessToken = await getAccessToken();

    if (accessToken == null || accessToken.isEmpty) {
      throw Exception('Please sign in to continue.');
    }

    var response = await _updatePhoneNumber(accessToken, phoneNumber);

    if (response.statusCode == 401) {
      accessToken = await refreshAccessToken();

      if (accessToken == null || accessToken.isEmpty) {
        throw Exception('Your session has expired. Please sign in again.');
      }

      response = await _updatePhoneNumber(accessToken, phoneNumber);
    }

    final dynamic decoded = _decodeResponse(response.body);

    if (response.statusCode != 200) {
      throw Exception(
        _extractErrorMessage(
          decoded,
          fallback: 'Unable to save your phone number.',
        ),
      );
    }

    if (decoded is! Map) {
      throw const FormatException(
        'The account server returned an unexpected response.',
      );
    }

    final decodedMap = Map<String, dynamic>.from(decoded);
    final userData = decodedMap['user'];

    if (userData is! Map) {
      throw const FormatException(
        'The account response did not contain a valid user.',
      );
    }

    return AuthUser.fromJson(Map<String, dynamic>.from(userData));
  }

  Future<http.Response> _fetchCurrentUser(String accessToken) {
    final uri = Uri.parse('${PropertyService.baseUrl}/api/auth/me/');

    return http
        .get(
          uri,
          headers: {
            'Accept': 'application/json',
            'Authorization': 'Bearer $accessToken',
          },
        )
        .timeout(_timeout);
  }

  Future<http.Response> _updatePhoneNumber(
    String accessToken,
    String phoneNumber,
  ) {
    final uri = Uri.parse('${PropertyService.baseUrl}/api/auth/me/');

    return http
        .patch(
          uri,
          headers: {
            'Accept': 'application/json',
            'Authorization': 'Bearer $accessToken',
            'Content-Type': 'application/json',
          },
          body: jsonEncode({'phone_number': phoneNumber.trim()}),
        )
        .timeout(_timeout);
  }

  Future<String?> getAccessToken() async {
    return _storage.read(key: _accessTokenKey);
  }

  Future<String?> getRefreshToken() async {
    return _storage.read(key: _refreshTokenKey);
  }

  Future<bool> isLoggedIn() async {
    final token = await getAccessToken();

    return token != null && token.isNotEmpty;
  }

  Future<String?> refreshAccessToken() async {
    final refreshToken = await getRefreshToken();

    if (refreshToken == null || refreshToken.isEmpty) {
      return null;
    }

    final uri = Uri.parse('${PropertyService.baseUrl}/api/auth/refresh/');

    final response = await http
        .post(
          uri,
          headers: const {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
          },
          body: jsonEncode({'refresh': refreshToken}),
        )
        .timeout(_timeout);

    final dynamic decoded = _decodeResponse(response.body);

    if (response.statusCode != 200 || decoded is! Map) {
      await logout();
      return null;
    }

    final decodedMap = Map<String, dynamic>.from(decoded);
    final accessToken = decodedMap['access']?.toString() ?? '';

    if (accessToken.isEmpty) {
      await logout();
      return null;
    }

    await _storage.write(key: _accessTokenKey, value: accessToken);

    return accessToken;
  }

  Future<void> logout() async {
    await Future.wait([
      _storage.delete(key: _accessTokenKey),
      _storage.delete(key: _refreshTokenKey),
    ]);
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
    if (decoded is Map) {
      final decodedMap = Map<String, dynamic>.from(decoded);
      final detail = decodedMap['detail'];

      if (detail != null && detail.toString().trim().isNotEmpty) {
        return detail.toString();
      }

      final messages = <String>[];

      for (final entry in decodedMap.entries) {
        final value = entry.value;

        if (value is List) {
          messages.add(value.map((item) => item.toString()).join(', '));
        } else if (value != null) {
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

class AuthUser {
  const AuthUser({
    required this.id,
    required this.username,
    required this.email,
    required this.phoneNumber,
    required this.fullName,
    required this.role,
    required this.isVerified,
    required this.trustScore,
    required this.isStaff,
    required this.isSuperuser,
  });

  final int id;
  final String username;
  final String email;
  final String phoneNumber;
  final String fullName;
  final String role;
  final bool isVerified;
  final double trustScore;
  final bool isStaff;
  final bool isSuperuser;

  factory AuthUser.fromJson(Map<String, dynamic> json) {
    return AuthUser(
      id: _parseInt(json['id']),
      username: json['username']?.toString() ?? '',
      email: json['email']?.toString() ?? '',
      phoneNumber: json['phone_number']?.toString() ?? '',
      fullName: json['full_name']?.toString() ?? '',
      role: json['role']?.toString().trim().toLowerCase() ?? 'customer',
      isVerified: _parseBool(json['is_verified']),
      trustScore: _parseDouble(json['trust_score']),
      isStaff: _parseBool(json['is_staff']),
      isSuperuser: _parseBool(json['is_superuser']),
    );
  }

  bool get isPartner {
    return role == 'partner';
  }

  bool get isCustomer {
    return role == 'customer';
  }

  bool get isAdmin {
    return isStaff;
  }

  String get displayName {
    if (fullName.trim().isNotEmpty) {
      return fullName.trim();
    }

    if (username.trim().isNotEmpty) {
      return username.trim();
    }

    return 'Pata Hao User';
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

  static double _parseDouble(dynamic value) {
    if (value is num) {
      return value.toDouble();
    }

    return double.tryParse(value?.toString() ?? '') ?? 0;
  }

  static bool _parseBool(dynamic value) {
    if (value is bool) {
      return value;
    }

    final normalized = value?.toString().trim().toLowerCase();

    return normalized == 'true' || normalized == '1' || normalized == 'yes';
  }
}
