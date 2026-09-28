import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/models/viewing.dart';

Viewing _viewingWithStatus(String status) {
  return Viewing.fromJson(<String, dynamic>{
    'id': 9,
    'status': status,
    'booking_status': status,
  });
}

void main() {
  test('customer payment actions cover every recoverable payment state', () {
    final pending = _viewingWithStatus('pending_payment');
    final legacyPending = _viewingWithStatus('payment_pending');
    final processing = _viewingWithStatus('payment_processing');
    final failed = _viewingWithStatus('payment_failed');

    expect(pending.requiresPaymentAction, true);
    expect(pending.paymentActionLabel, 'Continue to Payment');
    expect(legacyPending.requiresPaymentAction, true);
    expect(legacyPending.paymentActionLabel, 'Continue to Payment');
    expect(processing.requiresPaymentAction, true);
    expect(processing.paymentActionLabel, 'Resume Payment');
    expect(failed.requiresPaymentAction, true);
    expect(failed.paymentActionLabel, 'Retry Payment');
  });

  test('completed viewing does not offer another payment action', () {
    final completed = _viewingWithStatus('completed');

    expect(completed.requiresPaymentAction, false);
  });
}
