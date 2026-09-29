import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/screens/customer_dashboard_screen.dart';

void main() {
  testWidgets(
    'dashboard notification tile shows unread count and opens inbox',
    (tester) async {
      var opened = false;

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: CustomerDashboardListTile(
              icon: Icons.notifications_outlined,
              title: 'Notifications',
              subtitle: '3 unread updates. Tap to review.',
              badgeCount: 3,
              onTap: () => opened = true,
            ),
          ),
        ),
      );

      expect(find.text('Notifications'), findsOneWidget);
      expect(find.text('3 unread updates. Tap to review.'), findsOneWidget);
      expect(find.text('3'), findsOneWidget);

      await tester.tap(find.text('Notifications'));

      expect(opened, true);
    },
  );

  testWidgets('dashboard notification tile hides an empty badge', (
    tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: CustomerDashboardListTile(
            icon: Icons.notifications_outlined,
            title: 'Notifications',
            subtitle: 'Viewing confirmations and important updates.',
            onTap: () {},
          ),
        ),
      ),
    );

    expect(find.text('Notifications'), findsOneWidget);
    expect(
      find.text('Viewing confirmations and important updates.'),
      findsOneWidget,
    );
    expect(find.text('0'), findsNothing);
  });
}
