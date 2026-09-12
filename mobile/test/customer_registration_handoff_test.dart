import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/screens/welcome_screen.dart';

void main() {
  testWidgets('welcome create account opens customer registration', (
    tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        home: WelcomeScreen(onLoginSuccess: () {}),
      ),
    );

    expect(
      find.text('Account registration is coming next.'),
      findsNothing,
    );

    await tester.tap(find.text('Create Account'));
    await tester.pumpAndSettle();

    expect(find.text('Create your Pata Hao account'), findsOneWidget);
    expect(find.text('Full Name'), findsOneWidget);
    expect(find.text('Username'), findsOneWidget);
    expect(find.text('Email'), findsOneWidget);
    expect(find.text('Password'), findsOneWidget);
    expect(find.text('Confirm Password'), findsOneWidget);
  });
}
