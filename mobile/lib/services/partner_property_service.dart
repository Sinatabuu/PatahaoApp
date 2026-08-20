import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

import 'package:mobile/models/partner_property_photo.dart';
import 'package:mobile/models/property.dart';
import 'package:mobile/services/auth_service.dart';
import 'package:mobile/services/property_service.dart';

class PartnerPropertyService {
  PartnerPropertyService._();

  static final PartnerPropertyService instance = PartnerPropertyService._();

  static const Duration _timeout = Duration(seconds: 30);

  Future<List<Property>> fetchMyProperties({
    String? status,
    String? listingType,
  }) async {
    final queryParameters = <String, String>{};

    if (status != null && status.trim().isNotEmpty) {
      queryParameters['status'] = status.trim();
    }

    if (listingType != null && listingType.trim().isNotEmpty) {
      queryParameters['listing_type'] = listingType.trim();
    }

    final baseUri = Uri.parse(
      '${PropertyService.baseUrl}/api/partner/properties/',
    );

    final uri = queryParameters.isEmpty
        ? baseUri
        : baseUri.replace(queryParameters: queryParameters);

    debugPrint('PARTNER PROPERTIES REQUEST: $uri');

    final response = await _sendAuthorizedRequest(
      (accessToken) {
        return http
            .get(
              uri,
              headers: _authorizationHeaders(accessToken),
            )
            .timeout(_timeout);
      },
    );

    debugPrint('PARTNER PROPERTIES STATUS: ${response.statusCode}');

    final dynamic decoded = _decodeResponse(response);

    if (response.statusCode != 200) {
      throw Exception(
        _extractErrorMessage(
          decoded,
          fallback: 'Unable to load your properties.',
        ),
      );
    }

    if (decoded is! List) {
      throw const FormatException(
        'The partner properties API returned invalid data.',
      );
    }

    return decoded.map<Property>((dynamic item) {
      if (item is! Map) {
        throw const FormatException(
          'Invalid property information received.',
        );
      }

      return Property.fromJson(
        Map<String, dynamic>.from(item),
      );
    }).toList();
  }

  Future<Property> fetchMyProperty(int propertyId) async {
    _validateId(
      propertyId,
      name: 'propertyId',
      message: 'Property ID must be greater than zero.',
    );

    final uri = Uri.parse(
      '${PropertyService.baseUrl}'
      '/api/partner/properties/$propertyId/',
    );

    final response = await _sendAuthorizedRequest(
      (accessToken) {
        return http
            .get(
              uri,
              headers: _authorizationHeaders(accessToken),
            )
            .timeout(_timeout);
      },
    );

    final dynamic decoded = _decodeResponse(response);

    if (response.statusCode != 200) {
      throw Exception(
        _extractErrorMessage(
          decoded,
          fallback: 'Unable to load this property.',
        ),
      );
    }

    if (decoded is! Map) {
      throw const FormatException(
        'The partner property API returned invalid data.',
      );
    }

    return Property.fromJson(
      Map<String, dynamic>.from(decoded),
    );
  }

  Future<List<PartnerPropertyPhoto>> fetchPropertyPhotos(
    int propertyId,
  ) async {
    _validateId(
      propertyId,
      name: 'propertyId',
      message: 'Property ID must be greater than zero.',
    );

    final uri = Uri.parse(
      '${PropertyService.baseUrl}/api/partner/photos/',
    ).replace(
      queryParameters: {
        'property': propertyId.toString(),
      },
    );

    debugPrint('PROPERTY PHOTOS REQUEST: $uri');

    final response = await _sendAuthorizedRequest(
      (accessToken) {
        return http
            .get(
              uri,
              headers: _authorizationHeaders(accessToken),
            )
            .timeout(_timeout);
      },
    );

    debugPrint('PROPERTY PHOTOS STATUS: ${response.statusCode}');

    final dynamic decoded = _decodeResponse(response);

    if (response.statusCode != 200) {
      throw Exception(
        _extractErrorMessage(
          decoded,
          fallback: 'Unable to load the property photos.',
        ),
      );
    }

    if (decoded is! List) {
      throw const FormatException(
        'The property photos API returned invalid data.',
      );
    }

    return decoded.map<PartnerPropertyPhoto>((dynamic item) {
      if (item is! Map) {
        throw const FormatException(
          'Invalid property photo information received.',
        );
      }

      return PartnerPropertyPhoto.fromJson(
        Map<String, dynamic>.from(item),
      );
    }).toList();
  }

  Future<PartnerPropertyPhoto> uploadPropertyPhoto({
    required int propertyId,
    required Uint8List imageBytes,
    required String fileName,
    String caption = '',
    bool isCover = false,
  }) async {
    _validateId(
      propertyId,
      name: 'propertyId',
      message: 'Property ID must be greater than zero.',
    );

    if (imageBytes.isEmpty) {
      throw ArgumentError(
        'The selected photo contains no image data.',
      );
    }

    final safeFileName = fileName.trim().isEmpty
        ? 'property_photo.jpg'
        : fileName.trim();

    final uri = Uri.parse(
      '${PropertyService.baseUrl}/api/partner/photos/',
    );

    final response = await _sendAuthorizedRequest(
      (accessToken) async {
        final request = http.MultipartRequest(
          'POST',
          uri,
        );

        request.headers.addAll(
          _authorizationHeaders(accessToken),
        );

        request.fields['property'] = propertyId.toString();
        request.fields['caption'] = caption.trim();
        request.fields['is_cover'] = isCover.toString();

        request.files.add(
          http.MultipartFile.fromBytes(
            'image',
            imageBytes,
            filename: safeFileName,
          ),
        );

        final streamedResponse = await request.send().timeout(
          _timeout,
        );

        return http.Response.fromStream(streamedResponse);
      },
    );

    final dynamic decoded = _decodeResponse(response);

    if (response.statusCode != 201) {
      throw Exception(
        _extractErrorMessage(
          decoded,
          fallback: 'Unable to upload the property photo.',
        ),
      );
    }

    if (decoded is! Map) {
      throw const FormatException(
        'The photo upload API returned invalid data.',
      );
    }

    return PartnerPropertyPhoto.fromJson(
      Map<String, dynamic>.from(decoded),
    );
  }

  Future<PartnerPropertyPhoto> setCoverPhoto(
    int photoId,
  ) async {
    _validateId(
      photoId,
      name: 'photoId',
      message: 'Photo ID must be greater than zero.',
    );

    final uri = Uri.parse(
      '${PropertyService.baseUrl}'
      '/api/partner/photos/$photoId/',
    );

    final response = await _sendAuthorizedRequest(
      (accessToken) {
        return http
            .patch(
              uri,
              headers: {
                ..._authorizationHeaders(accessToken),
                'Content-Type': 'application/json',
              },
              body: jsonEncode({
                'is_cover': true,
              }),
            )
            .timeout(_timeout);
      },
    );

    final dynamic decoded = _decodeResponse(response);

    if (response.statusCode != 200) {
      throw Exception(
        _extractErrorMessage(
          decoded,
          fallback: 'Unable to set the cover photo.',
        ),
      );
    }

    if (decoded is! Map) {
      throw const FormatException(
        'The cover photo API returned invalid data.',
      );
    }

    return PartnerPropertyPhoto.fromJson(
      Map<String, dynamic>.from(decoded),
    );
  }

  Future<PartnerPropertyPhoto> updatePhotoCaption({
    required int photoId,
    required String caption,
  }) async {
    _validateId(
      photoId,
      name: 'photoId',
      message: 'Photo ID must be greater than zero.',
    );

    final uri = Uri.parse(
      '${PropertyService.baseUrl}'
      '/api/partner/photos/$photoId/',
    );

    final response = await _sendAuthorizedRequest(
      (accessToken) {
        return http
            .patch(
              uri,
              headers: {
                ..._authorizationHeaders(accessToken),
                'Content-Type': 'application/json',
              },
              body: jsonEncode({
                'caption': caption.trim(),
              }),
            )
            .timeout(_timeout);
      },
    );

    final dynamic decoded = _decodeResponse(response);

    if (response.statusCode != 200) {
      throw Exception(
        _extractErrorMessage(
          decoded,
          fallback: 'Unable to update the photo caption.',
        ),
      );
    }

    if (decoded is! Map) {
      throw const FormatException(
        'The photo update API returned invalid data.',
      );
    }

    return PartnerPropertyPhoto.fromJson(
      Map<String, dynamic>.from(decoded),
    );
  }

  Future<void> deletePropertyPhoto(int photoId) async {
    _validateId(
      photoId,
      name: 'photoId',
      message: 'Photo ID must be greater than zero.',
    );

    final uri = Uri.parse(
      '${PropertyService.baseUrl}'
      '/api/partner/photos/$photoId/',
    );

    final response = await _sendAuthorizedRequest(
      (accessToken) {
        return http
            .delete(
              uri,
              headers: _authorizationHeaders(accessToken),
            )
            .timeout(_timeout);
      },
    );

    if (response.statusCode == 204) {
      return;
    }

    final dynamic decoded = _decodeResponse(response);

    throw Exception(
      _extractErrorMessage(
        decoded,
        fallback: 'Unable to delete the property photo.',
      ),
    );
  }

  Future<Map<String, dynamic>> findNearbyProperties({
    required double latitude,
    required double longitude,
  }) async {
    final uri = Uri.parse(
      '${PropertyService.baseUrl}/api/properties/nearby/',
    ).replace(
      queryParameters: {
        'latitude': latitude.toString(),
        'longitude': longitude.toString(),
      },
    );

    debugPrint(
      'NEARBY PROPERTIES REQUEST: $uri',
    );

    final response = await _sendAuthorizedRequest(
      (accessToken) {
        return http
            .get(
              uri,
              headers: _authorizationHeaders(
                accessToken,
              ),
            )
            .timeout(_timeout);
      },
    );

    debugPrint(
      'NEARBY PROPERTIES STATUS: '
      '${response.statusCode}',
    );

    debugPrint(
      'NEARBY PROPERTIES BODY: '
      '${response.body}',
    );

    final dynamic decoded =
        _decodeResponse(response);

    if (response.statusCode != 200) {
      throw Exception(
        _extractErrorMessage(
          decoded,
          fallback:
              'Unable to check nearby properties.',
        ),
      );
    }

    if (decoded is! Map) {
      throw const FormatException(
        'Nearby properties returned invalid data.',
      );
    }

    return Map<String, dynamic>.from(
      decoded,
    );
  }

  Future<Map<String, dynamic>> joinExistingProperty(
    int propertyId,
  ) async {
    _validateId(
      propertyId,
      name: 'propertyId',
      message: 'Property ID must be greater than zero.',
    );

    final uri = Uri.parse(
      '${PropertyService.baseUrl}'
      '/api/partner/properties/$propertyId/join/',
    );

    final response = await _sendAuthorizedRequest(
      (accessToken) {
        return http
            .post(
              uri,
              headers: {
                ..._authorizationHeaders(accessToken),
                'Content-Type': 'application/json',
              },
              body: jsonEncode({}),
            )
            .timeout(_timeout);
      },
    );

    final dynamic decoded = _decodeResponse(response);

    if (response.statusCode != 200 &&
        response.statusCode != 201) {
      throw Exception(
        _extractErrorMessage(
          decoded,
          fallback: 'Unable to join this property.',
        ),
      );
    }

    if (decoded is! Map) {
      throw const FormatException(
        'Join property response was invalid.',
      );
    }

    return Map<String, dynamic>.from(decoded);
  }


  Future<Property> createProperty({
    required String title,
    required String propertyType,
    required String listingType,
    required double price,
    required String county,
    required String town,
    required String estate,
    required String address,
    required double latitude,
    required double longitude,
    required int bedrooms,
    required int bathrooms,
    required String description,
  }) async {
    final uri = Uri.parse(
      '${PropertyService.baseUrl}/api/partner/properties/',
    );

    final response = await _sendAuthorizedRequest(
      (accessToken) {
        return http
            .post(
              uri,
              headers: {
                ..._authorizationHeaders(accessToken),
                'Content-Type': 'application/json',
              },
              body: jsonEncode({
                'title': title.trim(),
                'property_type': propertyType,
                'listing_type': listingType,
                'price': price.toStringAsFixed(2),
                'county': county.trim(),
                'town': town.trim(),
                'estate': estate.trim(),
                'address': address.trim(),
                'latitude': latitude.toString(),
                'longitude': longitude.toString(),
                'bedrooms': bedrooms,
                'bathrooms': bathrooms,
                'description': description.trim(),
              }),
            )
            .timeout(_timeout);
      },
    );

    final dynamic decoded = _decodeResponse(response);

    if (response.statusCode != 201) {
      throw Exception(
        _extractErrorMessage(
          decoded,
          fallback: 'Unable to create property.',
        ),
      );
    }

    if (decoded is! Map) {
      throw const FormatException(
        'Property creation returned invalid data.',
      );
    }

    return Property.fromJson(
      Map<String, dynamic>.from(decoded),
    );
  }

  Future<Map<String, dynamic>> confirmDifferentProperty({
    required double latitude,
    required double longitude,
    required List<int> candidateIds,
  }) async {
    final uri = Uri.parse(
      '${PropertyService.baseUrl}'
      '/api/properties/confirm-different/',
    );

    final response = await _sendAuthorizedRequest(
      (accessToken) {
        return http
            .post(
              uri,
              headers: {
                ..._authorizationHeaders(accessToken),
                'Content-Type': 'application/json',
              },
              body: jsonEncode({
                'latitude': latitude.toString(),
                'longitude': longitude.toString(),
                'candidate_ids': candidateIds,
              }),
            )
            .timeout(_timeout);
      },
    );

    final dynamic decoded = _decodeResponse(response);

    if (response.statusCode != 200) {
      throw Exception(
        _extractErrorMessage(
          decoded,
          fallback: (
            'Unable to confirm that this is a different property.'
          ),
        ),
      );
    }

    if (decoded is! Map) {
      throw const FormatException(
        'Different-property confirmation returned invalid data.',
      );
    }

    return Map<String, dynamic>.from(decoded);
  }

  Future<Map<String, dynamic>> submitPropertyForVerification(
    int propertyId,
  ) async {
    _validateId(
      propertyId,
      name: 'propertyId',
      message: 'Property ID must be greater than zero.',
    );

    final uri = Uri.parse(
      '${PropertyService.baseUrl}'
      '/api/partner/properties/$propertyId/submit-verification/',
    );

    final response = await _sendAuthorizedRequest(
      (accessToken) {
        return http
            .post(
              uri,
              headers: {
                ..._authorizationHeaders(accessToken),
                'Content-Type': 'application/json',
              },
              body: jsonEncode({}),
            )
            .timeout(_timeout);
      },
    );

    final dynamic decoded = _decodeResponse(response);

    if (response.statusCode != 200) {
      throw Exception(
        _extractErrorMessage(
          decoded,
          fallback: 'Unable to submit property for verification.',
        ),
      );
    }

    if (decoded is! Map) {
      throw const FormatException(
        'Verification submission returned invalid data.',
      );
    }

    return Map<String, dynamic>.from(decoded);
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
        'Your session has expired. Please sign in again.',
      );
    }

    response = await sendRequest(accessToken);

    return response;
  }

  Map<String, String> _authorizationHeaders(
    String accessToken,
  ) {
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
      return jsonDecode(
        utf8.decode(response.bodyBytes),
      );
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

      if (detail != null &&
          detail.toString().trim().isNotEmpty) {
        return detail.toString().trim();
      }

      final messages = <String>[];

      for (final entry in map.entries) {
        final value = entry.value;

        if (value is List) {
          messages.add(
            value.map((item) => item.toString()).join(', '),
          );
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

  void _validateId(
    int value, {
    required String name,
    required String message,
  }) {
    if (value <= 0) {
      throw ArgumentError.value(
        value,
        name,
        message,
      );
    }
  }
}