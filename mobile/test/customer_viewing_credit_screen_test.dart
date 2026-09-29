import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/models/viewing_credit.dart';
import 'package:mobile/screens/customer_viewing_credit_screen.dart';

const _balance = ViewingCreditBalance(
  currency: 'KES',
  availableAmount: 1600,
  credits: <ViewingCredit>[
    ViewingCredit(
      id: 9,
      reference: 'PHVC-KIOO',
      propertyTitle: 'Kioo',
      amount: 2000,
      remainingAmount: 1600,
      currency: 'KES',
      status: 'active',
      issuedAt: '2026-09-26T10:00:00Z',
    ),
  ],
);

void main() {
  test('fully used credit remains recognizable in activity history', () {
    const credit = ViewingCredit(
      id: 10,
      reference: 'PHVC-USED',
      propertyTitle: 'Used credit property',
      amount: 2000,
      remainingAmount: 0,
      currency: 'KES',
      status: 'consumed',
      issuedAt: '2026-09-25T10:00:00Z',
    );

    expect(credit.usedAmount, 2000);
    expect(credit.isConsumed, true);
  });

  testWidgets('dashboard credit card shows the persistent available balance', (
    tester,
  ) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(body: ViewingCreditSummaryCard(balance: _balance)),
      ),
    );

    expect(find.text('Viewing Credit'), findsOneWidget);
    expect(find.text('KES 1600'), findsOneWidget);
    expect(
      find.text('Available for your next property viewing.'),
      findsOneWidget,
    );
  });

  testWidgets('credit activity explains issued used and remaining amounts', (
    tester,
  ) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: CustomerViewingCreditScreen(initialBalance: _balance),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Credit activity'), findsOneWidget);
    expect(find.text('Kioo'), findsOneWidget);
    expect(find.text('Credit issued'), findsOneWidget);
    expect(find.text('KES 2000'), findsOneWidget);
    expect(find.text('Credit used'), findsOneWidget);
    expect(find.text('KES 400'), findsOneWidget);
    expect(find.text('Remaining'), findsOneWidget);
    expect(find.text('KES 1600'), findsNWidgets(2));
    expect(find.text('Credit reference: PHVC-KIOO'), findsOneWidget);
  });
}
