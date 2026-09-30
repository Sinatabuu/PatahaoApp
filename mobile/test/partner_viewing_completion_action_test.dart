import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/models/partner_dashboard.dart';

void main() {
  group('Partner viewing completion action', () {
    PartnerDashboardViewing viewing({
      required String status,
      required String scheduledDate,
    }) {
      return PartnerDashboardViewing.fromJson(<String, dynamic>{
        'id': 28,
        'customer': 4,
        'property': 15,
        'property_title': 'Mason',
        'fee_amount': '400.00',
        'status': status,
        'booking_status': status,
        'confirmed_date': scheduledDate,
        'confirmed_time': '14:00:00',
      });
    }

    test('confirmed viewing can be completed on its scheduled date', () {
      final mason = viewing(
        status: 'confirmed',
        scheduledDate: '2026-10-02',
      );

      expect(mason.canCompleteOn(DateTime(2026, 10, 2)), isTrue);
    });

    test('confirmed viewing cannot be completed before its scheduled date', () {
      final mason = viewing(
        status: 'confirmed',
        scheduledDate: '2026-10-02',
      );

      expect(mason.canCompleteOn(DateTime(2026, 10, 1)), isFalse);
    });

    test('only a confirmed viewing exposes completion', () {
      final completed = viewing(
        status: 'completed',
        scheduledDate: '2026-10-02',
      );

      expect(completed.canCompleteOn(DateTime(2026, 10, 2)), isFalse);
    });
  });
}
