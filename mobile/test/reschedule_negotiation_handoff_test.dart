import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/models/viewing.dart';

void main() {
  group('Viewing reschedule negotiation contract', () {
    test('parses the final remaining partner proposal', () {
      final viewing = Viewing.fromJson(<String, dynamic>{
        'id': 41,
        'customer': 2,
        'property': 9,
        'status': 'reschedule_proposed',
        'booking_status': 'reschedule_proposed',
        'reschedule_decline_count': 1,
        'remaining_reschedule_proposals': 1,
        'requires_fee_resolution': false,
      });

      expect(viewing.canRespondToReschedule, isTrue);
      expect(viewing.rescheduleDeclineCount, 1);
      expect(viewing.remainingRescheduleProposals, 1);
      expect(viewing.friendlyStatus, 'New schedule proposed');
    });

    test('requires a fee choice after scheduling fails', () {
      final viewing = Viewing.fromJson(<String, dynamic>{
        'id': 41,
        'customer': 2,
        'property': 9,
        'status': 'scheduling_failed',
        'booking_status': 'scheduling_failed',
        'reschedule_decline_count': 2,
        'remaining_reschedule_proposals': 0,
        'requires_fee_resolution': true,
      });

      expect(viewing.canRespondToReschedule, isFalse);
      expect(viewing.requiresFeeResolution, isTrue);
      expect(viewing.hasFeeResolutionChoice, isFalse);
      expect(viewing.friendlyStatus, 'Scheduling could not be agreed');
    });

    test('requires the same protected fee choice after partner decline', () {
      final viewing = Viewing.fromJson(<String, dynamic>{
        'id': 44,
        'customer': 2,
        'property': 12,
        'status': 'scheduling_failed',
        'booking_status': 'scheduling_failed',
        'partner_response_message': 'The seller withdrew access.',
        'reschedule_decline_count': 0,
        'requires_fee_resolution': true,
      });

      expect(viewing.requiresFeeResolution, isTrue);
      expect(viewing.hasFeeResolutionChoice, isFalse);
      expect(viewing.partnerResponseMessage, 'The seller withdrew access.');
      expect(viewing.friendlyStatus, 'Scheduling could not be agreed');
    });

    test('shows a recorded refund without asking again', () {
      final viewing = Viewing.fromJson(<String, dynamic>{
        'id': 41,
        'customer': 2,
        'property': 9,
        'status': 'scheduling_failed',
        'booking_status': 'scheduling_failed',
        'reschedule_decline_count': 2,
        'remaining_reschedule_proposals': 0,
        'fee_resolution_choice': 'refund',
        'fee_resolution_label': 'Full refund',
        'fee_resolution_requested_at': '2026-09-10T18:30:00Z',
        'requires_fee_resolution': false,
      });

      expect(viewing.hasFeeResolutionChoice, isTrue);
      expect(viewing.requiresFeeResolution, isFalse);
      expect(viewing.feeResolutionLabel, 'Full refund');
      expect(viewing.friendlyStatus, 'Fee resolution requested');
    });
  });
}
