import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/models/partner_dashboard.dart';

void main() {
  group('Partner decline fee-resolution handoff', () {
    test('shows protected customer choice pending without a partner payout', () {
      final viewing = PartnerDashboardViewing.fromJson(<String, dynamic>{
        'id': 71,
        'customer': 4,
        'property': 15,
        'property_title': 'Lowell Mega Property',
        'fee_amount': '2000.00',
        'status': 'scheduling_failed',
        'booking_status': 'scheduling_failed',
        'requires_fee_resolution': true,
      });

      expect(viewing.friendlyStatus, 'Customer fee choice required');
      expect(viewing.requiresFeeResolution, isTrue);
      expect(viewing.formattedFee, 'KES 2000.00');
    });

    test('shows a customer refund request as pending staff action', () {
      final viewing = PartnerDashboardViewing.fromJson(<String, dynamic>{
        'id': 71,
        'customer': 4,
        'property': 15,
        'property_title': 'Lowell Mega Property',
        'fee_amount': '2000.00',
        'status': 'scheduling_failed',
        'booking_status': 'scheduling_failed',
        'fee_resolution_choice': 'refund',
        'fee_resolution_label': 'Full refund',
        'fee_resolution_requested_at': '2026-09-22T18:30:00Z',
        'requires_fee_resolution': false,
      });

      expect(viewing.friendlyStatus, 'Fee resolution pending');
      expect(viewing.feeResolutionChoice, 'refund');
      expect(viewing.feeResolutionLabel, 'Full refund');
      expect(viewing.feeResolutionProcessed, isFalse);
    });
  });
}
