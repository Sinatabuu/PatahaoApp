import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/models/viewing.dart';
import 'package:mobile/models/viewing_credit.dart';
import 'package:mobile/screens/payment_screen.dart';
import 'package:mobile/services/payment_service.dart';

class _NoCreditPaymentService extends PaymentService {
  @override
  Future<ViewingCreditBalance> fetchViewingCreditBalance() async {
    return const ViewingCreditBalance(
      currency: 'KES',
      availableAmount: 0,
      credits: <ViewingCredit>[],
    );
  }
}

void main() {
  testWidgets('development payment option is clearly marked', (tester) async {
    const viewing = Viewing(
      id: 41,
      customerId: 7,
      customerName: 'Test Customer',
      propertyId: 12,
      propertyTitle: 'Dracut North',
      requestedDate: '2026-09-15',
      requestedTime: '10:00:00',
      customerMessage: '',
      feeAmount: 400,
      status: 'pending_payment',
      bookingStatus: 'pending_payment',
      operationalStatus: 'idle',
      paymentReference: '',
      partnerResponseMessage: '',
      completionNotes: '',
      events: <ViewingEvent>[],
      createdAt: '2026-09-10T10:00:00Z',
      updatedAt: '2026-09-10T10:00:00Z',
    );

    await tester.pumpWidget(
      MaterialApp(
        home: PaymentScreen(
          viewing: viewing,
          paymentService: _NoCreditPaymentService(),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Viewing Payment'), findsOneWidget);
    expect(find.text('Pay KES 400'), findsOneWidget);
    expect(find.text('Complete Test Payment'), findsOneWidget);
    expect(
      find.text('Development only — no M-Pesa request is sent.'),
      findsOneWidget,
    );
  });
}
