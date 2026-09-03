import 'dart:convert';

import 'package:http/http.dart' as http;

import 'package:mobile/services/auth_service.dart';
import 'package:mobile/services/property_service.dart';

class StaffCommissionReportService {
  StaffCommissionReportService._();

  static final StaffCommissionReportService instance =
      StaffCommissionReportService._();

  static const Duration _timeout = Duration(seconds: 30);

  Future<StaffCommissionReport> fetchReport({
    String search = '',
    String dealType = '',
    String settlementStatus = '',
    String payoutState = '',
    String closedFrom = '',
    String closedTo = '',
    String sort = 'newest_closed',
    int page = 1,
    int pageSize = 50,
  }) async {
    final uri =
        Uri.parse(
          '${PropertyService.baseUrl}/api/admin/commission-report/',
        ).replace(
          queryParameters: {
            if (search.trim().isNotEmpty) 'search': search.trim(),
            if (dealType.trim().isNotEmpty) 'deal_type': dealType.trim(),
            if (settlementStatus.trim().isNotEmpty)
              'settlement_status': settlementStatus.trim(),
            if (payoutState.trim().isNotEmpty)
              'payout_state': payoutState.trim(),
            if (closedFrom.trim().isNotEmpty) 'closed_from': closedFrom.trim(),
            if (closedTo.trim().isNotEmpty) 'closed_to': closedTo.trim(),
            'sort': sort,
            'page': page.toString(),
            'page_size': pageSize.toString(),
          },
        );

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
          fallback: 'Unable to load commission reporting.',
        ),
      );
    }

    if (decoded is! Map) {
      throw const FormatException(
        'The commission report API returned invalid data.',
      );
    }

    return StaffCommissionReport.fromJson(Map<String, dynamic>.from(decoded));
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

class StaffCommissionReport {
  const StaffCommissionReport({
    required this.currency,
    required this.completedDeals,
    required this.fullySettledDeals,
    required this.grossCommission,
    required this.pataHaoRetainedRevenue,
    required this.externalAllocations,
    required this.externalPayouts,
    required this.outstandingPayouts,
    required this.count,
    required this.page,
    required this.pageSize,
    required this.totalPages,
    required this.hasNext,
    required this.hasPrevious,
    required this.recentDeals,
  });

  final String currency;
  final int completedDeals;
  final int fullySettledDeals;
  final String grossCommission;
  final String pataHaoRetainedRevenue;
  final String externalAllocations;
  final String externalPayouts;
  final String outstandingPayouts;

  final int count;
  final int page;
  final int pageSize;
  final int totalPages;
  final bool hasNext;
  final bool hasPrevious;

  final List<StaffCommissionReportDeal> recentDeals;

  factory StaffCommissionReport.fromJson(Map<String, dynamic> json) {
    final recentDeals = <StaffCommissionReportDeal>[];

    final rawDeals = json['recent_deals'];

    if (rawDeals is List) {
      for (final item in rawDeals) {
        if (item is Map) {
          recentDeals.add(
            StaffCommissionReportDeal.fromJson(Map<String, dynamic>.from(item)),
          );
        }
      }
    }

    return StaffCommissionReport(
      currency: json['currency']?.toString() ?? 'KES',
      completedDeals: _parseInt(json['completed_deals']),
      fullySettledDeals: _parseInt(json['fully_settled_deals']),
      grossCommission: json['gross_commission']?.toString() ?? '0.00',
      pataHaoRetainedRevenue:
          json['pata_hao_retained_revenue']?.toString() ?? '0.00',
      externalAllocations: json['external_allocations']?.toString() ?? '0.00',
      externalPayouts: json['external_payouts']?.toString() ?? '0.00',
      outstandingPayouts: json['outstanding_payouts']?.toString() ?? '0.00',
      count: _parseInt(json['count']),
      page: _parseInt(json['page']),
      pageSize: _parseInt(json['page_size']),
      totalPages: _parseInt(json['total_pages']),
      hasNext: json['has_next'] == true,
      hasPrevious: json['has_previous'] == true,
      recentDeals: recentDeals,
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

class StaffCommissionReportDeal {
  const StaffCommissionReportDeal({
    required this.dealId,
    required this.dealNumber,
    required this.propertyTitle,
    required this.customerName,
    required this.partnerName,
    required this.ownerName,
    required this.invoiceNumber,
    required this.dealType,
    required this.dealStatus,
    required this.settlementStatus,
    required this.currency,
    required this.grossCommission,
    required this.pataHaoRetainedRevenue,
    required this.externalPayouts,
    required this.outstandingPayouts,
    required this.completedAt,
    required this.closedAt,
  });

  final int dealId;
  final String dealNumber;
  final String propertyTitle;
  final String customerName;
  final String partnerName;
  final String ownerName;
  final String invoiceNumber;
  final String dealType;
  final String dealStatus;
  final String settlementStatus;
  final String currency;
  final String grossCommission;
  final String pataHaoRetainedRevenue;
  final String externalPayouts;
  final String outstandingPayouts;
  final String completedAt;
  final String closedAt;

  factory StaffCommissionReportDeal.fromJson(Map<String, dynamic> json) {
    return StaffCommissionReportDeal(
      dealId: StaffCommissionReport._parseInt(json['deal_id']),
      dealNumber: json['deal_number']?.toString() ?? '',
      propertyTitle: json['property_title']?.toString() ?? '',
      customerName: json['customer_name']?.toString() ?? '',
      partnerName: json['partner_name']?.toString() ?? '',
      ownerName: json['owner_name']?.toString() ?? '',
      invoiceNumber: json['invoice_number']?.toString() ?? '',
      dealType: json['deal_type']?.toString() ?? '',
      dealStatus: json['deal_status']?.toString() ?? '',
      settlementStatus: json['settlement_status']?.toString() ?? '',
      currency: json['currency']?.toString() ?? 'KES',
      grossCommission: json['gross_commission']?.toString() ?? '0.00',
      pataHaoRetainedRevenue:
          json['pata_hao_retained_revenue']?.toString() ?? '0.00',
      externalPayouts: json['external_payouts']?.toString() ?? '0.00',
      outstandingPayouts: json['outstanding_payouts']?.toString() ?? '0.00',
      completedAt: json['completed_at']?.toString() ?? '',
      closedAt: json['closed_at']?.toString() ?? '',
    );
  }
}
