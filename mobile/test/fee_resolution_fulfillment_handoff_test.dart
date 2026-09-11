import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/models/payment.dart';
import 'package:mobile/models/viewing.dart';

void main() {
  group('Viewing fee resolution fulfillment contract', () {
    test('parses a completed full refund and its evidence', () {
      final viewing = Viewing.fromJson(<String, dynamic>{
        'id': 51,
        'customer': 2,
        'property': 9,
        'status': 'refunded',
        'booking_status': 'refunded',
        'fee_resolution_choice': 'refund',
        'fee_resolution_label': 'Full refund',
        'fee_resolution_reference': 'MPESA-REFUND-0051',
        'fee_resolution_processed_at': '2026-09-11T16:30:00Z',
        'fee_resolution_processed_by': 4,
        'fee_resolution_processed': true,
        'requires_fee_resolution': false,
      });

      expect(viewing.friendlyStatus, 'Refunded');
      expect(viewing.feeResolutionProcessed, isTrue);
      expect(viewing.feeResolutionReference, 'MPESA-REFUND-0051');
      expect(viewing.feeResolutionProcessedBy, 4);
      expect(viewing.requiresFeeResolution, isFalse);
    });

    test('parses an issued transferable viewing credit', () {
      final viewing = Viewing.fromJson(<String, dynamic>{
        'id': 52,
        'customer': 2,
        'property': 10,
        'status': 'credit_issued',
        'booking_status': 'credit_issued',
        'fee_resolution_choice': 'credit',
        'fee_resolution_label': 'Transferable viewing credit',
        'fee_resolution_reference': 'PHC-2026-A1B2C3D4E5',
        'fee_resolution_processed_at': '2026-09-11T16:40:00Z',
        'fee_resolution_processed': true,
        'requires_fee_resolution': false,
      });

      expect(viewing.friendlyStatus, 'Viewing credit issued');
      expect(viewing.feeResolutionProcessed, isTrue);
      expect(viewing.feeResolutionReference, 'PHC-2026-A1B2C3D4E5');
      expect(viewing.requiresFeeResolution, isFalse);
    });

    test('keeps a refunded payment receipt and refund evidence available', () {
      final payment = Payment.fromJson(<String, dynamic>{
        'id': 12,
        'viewing': 51,
        'payer': 2,
        'amount': '400.00',
        'currency': 'KES',
        'status': 'refunded',
        'payment_reference': 'PH-2026-PAID0051',
        'receipt_number': 'PHR-2026-PAID0051',
        'refund_reference': 'MPESA-REFUND-0051',
        'refund_notes': 'Confirmed in provider portal.',
        'refunded_at': '2026-09-11T16:30:00Z',
        'refunded_by': 4,
      });

      expect(payment.isRefunded, isTrue);
      expect(payment.hasReceipt, isTrue);
      expect(payment.refundReference, 'MPESA-REFUND-0051');
      expect(payment.refundedBy, 4);
    });
  });
}
