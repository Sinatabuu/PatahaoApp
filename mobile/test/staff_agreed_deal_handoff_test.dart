import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/screens/staff_deal_detail_screen.dart';

void main() {
  testWidgets('agreed rental exposes controlled staff verification', (
    tester,
  ) async {
    var completionRequested = false;

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: StaffDealTransactionCompletionCard(
            dealStatus: 'agreed',
            isSale: false,
            completedAt: 'Not recorded',
            isSubmitting: false,
            onComplete: () {
              completionRequested = true;
            },
          ),
        ),
      ),
    );

    expect(find.text('Transaction Verification'), findsOneWidget);
    expect(find.text('Verify Rental Completed'), findsOneWidget);
    expect(find.textContaining('All three parties confirmed'), findsOneWidget);

    await tester.tap(find.text('Verify Rental Completed'));

    expect(completionRequested, isTrue);
  });

  testWidgets('agreed sale uses sale-specific verification language', (
    tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: StaffDealTransactionCompletionCard(
            dealStatus: 'agreed',
            isSale: true,
            completedAt: 'Not recorded',
            isSubmitting: false,
            onComplete: () {},
          ),
        ),
      ),
    );

    expect(find.text('Verify Sale Completed'), findsOneWidget);
    expect(find.textContaining('marked sold'), findsOneWidget);
  });

  testWidgets('verified transaction no longer offers completion again', (
    tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: StaffDealTransactionCompletionCard(
            dealStatus: 'commission_due',
            isSale: false,
            completedAt: '2026-09-11  12:30',
            isSubmitting: false,
            onComplete: () {},
          ),
        ),
      ),
    );

    expect(find.text('Verify Rental Completed'), findsNothing);
    expect(
      find.textContaining('commission obligation was activated'),
      findsOneWidget,
    );
    expect(find.text('Verified: 2026-09-11  12:30'), findsOneWidget);
  });

  testWidgets('commission receipt action invokes the controlled handoff', (
    tester,
  ) async {
    var receiptRequested = false;

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: StaffCommissionReceiptAction(
            isSubmitting: false,
            onPressed: () {
              receiptRequested = true;
            },
          ),
        ),
      ),
    );

    expect(find.text('Record Commission Payment'), findsOneWidget);

    await tester.tap(find.text('Record Commission Payment'));

    expect(receiptRequested, isTrue);
  });
}
