import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/models/partner_dashboard.dart';

void main() {
  group('Partner owner-confirmation status', () {
    test('shows when Pata Hao has sent the secure link', () {
      final viewing = PartnerDashboardViewing.fromJson(<String, dynamic>{
        'id': 91,
        'customer': 4,
        'property': 15,
        'property_title': 'Kioo Property',
        'status': 'completed',
        'deal_id': 9,
        'partner_outcome_submitted': true,
        'owner_confirmation_status': 'sent_to_owner',
        'owner_confirmation_status_label': 'Sent to owner',
      });

      expect(viewing.dealId, 9);
      expect(viewing.ownerConfirmationStatus, 'sent_to_owner');
      expect(viewing.ownerConfirmationStatusLabel, 'Sent to owner');
    });

    test('shows when the owner has confirmed the transaction', () {
      final viewing = PartnerDashboardViewing.fromJson(<String, dynamic>{
        'id': 91,
        'customer': 4,
        'property': 15,
        'property_title': 'Kioo Property',
        'status': 'completed',
        'deal_id': 9,
        'owner_confirmation_status': 'confirmed',
        'owner_confirmation_status_label': 'Owner confirmed transaction',
      });

      expect(viewing.ownerConfirmationStatus, 'confirmed');
      expect(
        viewing.ownerConfirmationStatusLabel,
        'Owner confirmed transaction',
      );
    });

    test('remains compatible when no deal exists yet', () {
      final viewing = PartnerDashboardViewing.fromJson(<String, dynamic>{
        'id': 92,
        'customer': 4,
        'property': 16,
        'status': 'completed',
      });

      expect(viewing.dealId, null);
      expect(viewing.ownerConfirmationStatus, '');
      expect(viewing.ownerConfirmationStatusLabel, '');
    });
  });
}
