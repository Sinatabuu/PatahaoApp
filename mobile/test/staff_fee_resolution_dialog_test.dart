import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/widgets/staff_fee_resolution_dialog.dart';

void main() {
  testWidgets('credit dialog closes cleanly and returns the decision', (
    tester,
  ) async {
    StaffFeeResolutionDecision? decision;

    await tester.pumpWidget(
      MaterialApp(
        home: Builder(
          builder: (context) {
            return Scaffold(
              body: ElevatedButton(
                onPressed: () async {
                  decision = await showStaffFeeResolutionDialog(
                    context,
                    isRefund: false,
                  );
                },
                child: const Text('Open'),
              ),
            );
          },
        ),
      ),
    );

    await tester.tap(find.text('Open'));
    await tester.pumpAndSettle();
    await tester.enterText(
      find.byType(TextFormField),
      'Customer selected viewing credit',
    );
    await tester.tap(find.text('Issue Credit'));
    await tester.pumpAndSettle();

    expect(tester.takeException(), null);
    expect(decision != null, true);
    expect(decision!.providerReference, '');
    expect(decision!.notes, 'Customer selected viewing credit');
  });

  testWidgets('refund dialog requires the provider evidence reference', (
    tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Builder(
          builder: (context) {
            return Scaffold(
              body: ElevatedButton(
                onPressed: () {
                  showStaffFeeResolutionDialog(context, isRefund: true);
                },
                child: const Text('Open'),
              ),
            );
          },
        ),
      ),
    );

    await tester.tap(find.text('Open'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Record Refund'));
    await tester.pump();

    expect(find.text('Enter the completed refund reference.'), findsOneWidget);
  });
}
