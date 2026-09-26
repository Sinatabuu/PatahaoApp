import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/models/payment.dart';
import 'package:mobile/models/viewing.dart';
import 'package:mobile/models/viewing_credit.dart';
import 'package:mobile/screens/payment_screen.dart';
import 'package:mobile/screens/payment_success_screen.dart';
import 'package:mobile/services/payment_service.dart';

class _CreditPaymentService extends PaymentService {
  _CreditPaymentService(this.balance, {this.existingPayment});

  final ViewingCreditBalance balance;
  final Payment? existingPayment;

  @override
  Future<ViewingCreditBalance> fetchViewingCreditBalance() async => balance;

  @override
  Future<Payment?> fetchViewingPayment({required int viewingId}) async {
    return existingPayment;
  }
}

const _viewing = Viewing(
  id: 41,
  customerId: 7,
  customerName: 'Test Customer',
  propertyId: 12,
  propertyTitle: 'Kioo Apartments',
  requestedDate: '2026-09-28',
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
  createdAt: '2026-09-26T10:00:00Z',
  updatedAt: '2026-09-26T10:00:00Z',
);

void main() {
  test('credit balance parses the available amount and source credits', () {
    final balance = ViewingCreditBalance.fromJson(<String, dynamic>{
      'currency': 'KES',
      'available_amount': '2000.00',
      'credits': <Map<String, dynamic>>[
        <String, dynamic>{
          'id': 9,
          'credit_reference': 'PHVC-ABC123',
          'property_title': 'Kioo Apartments',
          'amount': '2000.00',
          'remaining_amount': '2000.00',
          'currency': 'KES',
          'status': 'active',
          'issued_at': '2026-09-26T10:00:00Z',
        },
      ],
    });

    expect(balance.hasCredit, true);
    expect(balance.availableAmount, 2000);
    expect(balance.credits.single.reference, 'PHVC-ABC123');
  });

  testWidgets('customer sees the credit deduction and remaining balance', (
    tester,
  ) async {
    final service = _CreditPaymentService(
      const ViewingCreditBalance(
        currency: 'KES',
        availableAmount: 2000,
        credits: <ViewingCredit>[],
      ),
    );

    await tester.pumpWidget(
      MaterialApp(
        home: PaymentScreen(viewing: _viewing, paymentService: service),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.textContaining('KES 2000 available'), findsOneWidget);
    expect(find.text('Pay KES 400'), findsOneWidget);
    expect(find.text('M-Pesa phone number'), findsOneWidget);
    expect(
      find.text('Your credit will stay available for a future viewing.'),
      findsOneWidget,
    );

    await tester.tap(find.byType(Switch));
    await tester.pumpAndSettle();

    expect(
      find.text('KES 400 will be used. KES 1600 will remain.'),
      findsOneWidget,
    );
    expect(find.text('Use KES 400 Credit'), findsOneWidget);
    expect(find.text('M-Pesa phone number'), findsNothing);

    await tester.tap(find.byType(Switch));
    await tester.pumpAndSettle();

    expect(find.text('Pay KES 400'), findsOneWidget);
    expect(find.text('M-Pesa phone number'), findsOneWidget);
    expect(
      find.text('Your credit will stay available for a future viewing.'),
      findsOneWidget,
    );
  });

  testWidgets('partial credit clearly shows the M-Pesa difference', (
    tester,
  ) async {
    final service = _CreditPaymentService(
      const ViewingCreditBalance(
        currency: 'KES',
        availableAmount: 250,
        credits: <ViewingCredit>[],
      ),
    );

    await tester.pumpWidget(
      MaterialApp(
        home: PaymentScreen(viewing: _viewing, paymentService: service),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.byType(Switch));
    await tester.pumpAndSettle();

    expect(find.text('Use KES 250 + Pay KES 150'), findsOneWidget);
    expect(find.text('M-Pesa phone number'), findsOneWidget);
    expect(
      find.textContaining('an M-Pesa request for KES 150'),
      findsOneWidget,
    );
  });

  testWidgets('resume keeps previously applied credit attached', (
    tester,
  ) async {
    final existingPayment = Payment.fromJson(<String, dynamic>{
      'id': 56,
      'viewing': 41,
      'payer': 7,
      'amount': '400.00',
      'credit_applied_amount': '250.00',
      'cash_amount': '150.00',
      'currency': 'KES',
      'phone_number': '254712345678',
      'provider': 'mpesa',
      'purpose': 'viewing_fee',
      'status': 'failed',
      'payment_reference': 'PHPAY-RETRY',
    });
    final service = _CreditPaymentService(
      const ViewingCreditBalance(
        currency: 'KES',
        availableAmount: 0,
        credits: <ViewingCredit>[],
      ),
      existingPayment: existingPayment,
    );
    const processingViewing = Viewing(
      id: 41,
      customerId: 7,
      customerName: 'Test Customer',
      propertyId: 12,
      propertyTitle: 'Kioo Apartments',
      requestedDate: '2026-09-28',
      requestedTime: '10:00:00',
      customerMessage: '',
      feeAmount: 400,
      status: 'payment_processing',
      bookingStatus: 'payment_processing',
      operationalStatus: 'idle',
      paymentReference: 'PHPAY-RETRY',
      partnerResponseMessage: '',
      completionNotes: '',
      events: <ViewingEvent>[],
      createdAt: '2026-09-26T10:00:00Z',
      updatedAt: '2026-09-26T10:00:00Z',
    );

    await tester.pumpWidget(
      MaterialApp(
        home: PaymentScreen(
          viewing: processingViewing,
          paymentService: service,
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(
      find.text('Viewing credit already applied (KES 250)'),
      findsOneWidget,
    );
    expect(
      find.text(
        'This credit is protected in this payment. KES 0 remains available.',
      ),
      findsOneWidget,
    );
    expect(find.text('Resume M-Pesa · KES 150'), findsOneWidget);
    expect(find.text('M-Pesa phone number'), findsOneWidget);
  });

  testWidgets('receipt explains a fully credit-funded viewing', (tester) async {
    final payment = Payment.fromJson(<String, dynamic>{
      'id': 55,
      'viewing': 41,
      'payer': 7,
      'amount': '400.00',
      'credit_applied_amount': '400.00',
      'cash_amount': '0.00',
      'currency': 'KES',
      'provider': 'viewing_credit',
      'purpose': 'viewing_fee',
      'status': 'successful',
      'payment_reference': 'PHPAY-ABC123',
      'receipt_number': 'PHRCPT-ABC123',
      'provider_transaction_id': '',
      'provider_receipt_number': '',
      'failure_reason': '',
      'paid_at': '2026-09-26T10:00:00Z',
      'created_at': '2026-09-26T10:00:00Z',
      'updated_at': '2026-09-26T10:00:00Z',
      'credit_redemptions': <Map<String, dynamic>>[
        <String, dynamic>{
          'reference': 'PHCR-ABC123',
          'credit_reference': 'PHVC-ABC123',
          'amount': '400.00',
        },
      ],
    });

    await tester.pumpWidget(
      MaterialApp(
        home: PaymentSuccessScreen(viewing: _viewing, payment: payment),
      ),
    );

    expect(payment.fullyCoveredByCredit, true);
    expect(
      find.textContaining('No M-Pesa payment was needed.'),
      findsOneWidget,
    );
    expect(find.text('Viewing credit applied'), findsOneWidget);
    expect(find.text('KES 400.00'), findsNWidgets(2));
    expect(find.text('M-Pesa amount'), findsOneWidget);
    expect(find.text('KES 0.00'), findsOneWidget);
  });
}
