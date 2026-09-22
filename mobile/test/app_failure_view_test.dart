import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/widgets/app_failure_view.dart';

void main() {
  testWidgets('shows a safe recovery view and runs its action', (tester) async {
    var retryCount = 0;

    await tester.pumpWidget(
      MaterialApp(
        home: AppFailureView(
          title: 'Pata Hao needs to recover',
          message: 'No technical details are shown.',
          primaryLabel: 'Try Again',
          onPrimary: () {
            retryCount++;
          },
        ),
      ),
    );

    expect(find.text('Pata Hao needs to recover'), findsOneWidget);
    expect(find.text('No technical details are shown.'), findsOneWidget);
    expect(find.text('Try Again'), findsOneWidget);

    await tester.tap(find.text('Try Again'));
    await tester.pump();

    expect(retryCount, 1);
  });

  testWidgets('supports a message-only startup failure', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: AppFailureView(
          title: 'Pata Hao could not start',
          message: 'Please reopen the app.',
        ),
      ),
    );

    expect(find.text('Pata Hao could not start'), findsOneWidget);
    expect(find.byType(FilledButton), findsNothing);
  });
}
