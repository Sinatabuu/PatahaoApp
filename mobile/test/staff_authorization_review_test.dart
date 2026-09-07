import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/models/staff_authorization_review.dart';

void main() {
  test('parses an authorization review waiting for staff', () {
    final review = StaffAuthorizationReview.fromJson({
      'id': 17,
      'mandate_number': 'PH-MAN-2026-TEST',
      'property': 8,
      'property_title': 'Green View Home',
      'partner_name': 'Trusted Partner',
      'status': 'under_review',
      'status_display': 'Under review',
      'authorization_method_display': 'Written authorization',
      'submitted_at': '2026-09-07T10:30:00Z',
      'owner_detail': {
        'legal_name': 'Property Owner',
        'phone_number': '0700000000',
      },
      'commission_detail': {
        'agreement_number': 'PH-COM-2026-TEST',
        'commission_method_display': 'Percentage',
        'expected_total_commission': '300000.00',
        'currency': 'KES',
      },
    });

    expect(review.id, 17);
    expect(review.propertyTitle, 'Green View Home');
    expect(review.partnerName, 'Trusted Partner');
    expect(review.ownerName, 'Property Owner');
    expect(review.status, 'under_review');
    expect(review.expectedCommission, '300000.00');
  });

  test('parses immutable evidence metadata for staff review', () {
    final evidence = StaffAuthorizationEvidence.fromStep({
      'label': 'Ownership proof',
      'document': {
        'id': 42,
        'original_filename': 'title-deed.pdf',
        'status_display': 'Under review',
        'file_size': 2048,
        'file_hash': '1234567890abcdef',
      },
    });

    expect(evidence.id, 42);
    expect(evidence.label, 'Ownership proof');
    expect(evidence.filename, 'title-deed.pdf');
    expect(evidence.status, 'Under review');
    expect(evidence.fileSizeLabel, '2.0 KB');
    expect(evidence.shortHash, '1234567890ab');
    expect(evidence.isProvided, isTrue);
    expect(evidence.fileExtension, 'pdf');
  });

  test('marks a missing evidence step as unavailable', () {
    final evidence = StaffAuthorizationEvidence.fromStep({
      'label': 'Owner identity',
      'document': null,
    });

    expect(evidence.id, 0);
    expect(evidence.filename, 'Not provided');
    expect(evidence.isProvided, isFalse);
    expect(evidence.fileExtension, '');
  });
}
