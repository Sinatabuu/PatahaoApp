import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/models/notification.dart';
import 'package:mobile/models/viewing.dart';
import 'package:mobile/widgets/customer_viewing_action_alert.dart';

void main() {
  group('Customer viewing action communication', () {
    test('parses an actionable viewing notification', () {
      final notification = AppNotification.fromJson(<String, dynamic>{
        'id': 71,
        'title': 'Action required: viewing time changed',
        'message': 'Review the new time.',
        'notification_type': 'viewing',
        'notification_type_label': 'Viewing',
        'viewing': 41,
        'action_label': 'Review new viewing time',
        'requires_action': true,
        'is_read': false,
        'created_at': '2026-09-25T12:00:00Z',
      });

      expect(notification.hasViewingAction, true);
      expect(notification.viewingId, 41);
      expect(notification.requiresAction, true);
      expect(notification.actionLabel, 'Review new viewing time');
    });

    testWidgets('persistent alert explains the new time and protected fee', (
      tester,
    ) async {
      var reviewed = false;
      final viewing = _rescheduledViewing();

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: SingleChildScrollView(
              child: CustomerViewingActionAlert(
                viewing: viewing,
                totalActions: 1,
                onReview: () => reviewed = true,
              ),
            ),
          ),
        ),
      );

      expect(find.text('Action required'), findsOneWidget);
      expect(find.text('Viewing time changed for Kioo'), findsOneWidget);
      expect(find.textContaining('12 February 2027'), findsOneWidget);
      expect(find.textContaining('payment remains protected'), findsOneWidget);

      await tester.tap(find.text('Review New Time'));
      expect(reviewed, true);
    });

    testWidgets('startup dialog compares old and proposed schedules', (
      tester,
    ) async {
      bool? shouldReview;
      final viewing = _rescheduledViewing();

      await tester.pumpWidget(
        MaterialApp(
          home: Builder(
            builder: (context) {
              return Scaffold(
                body: Center(
                  child: FilledButton(
                    onPressed: () async {
                      shouldReview = await showCustomerViewingActionDialog(
                        context,
                        viewing: viewing,
                      );
                    },
                    child: const Text('Show alert'),
                  ),
                ),
              );
            },
          ),
        ),
      );

      await tester.tap(find.text('Show alert'));
      await tester.pumpAndSettle();

      expect(find.text('Your viewing time changed'), findsOneWidget);
      expect(find.text('Original time'), findsOneWidget);
      expect(find.text('Proposed time'), findsOneWidget);
      expect(
        find.textContaining('paid viewing remains protected'),
        findsOneWidget,
      );

      await tester.tap(find.text('Review Now'));
      await tester.pumpAndSettle();

      expect(shouldReview, true);
    });

    testWidgets('fee-resolution alert keeps the money choice prominent', (
      tester,
    ) async {
      final viewing = Viewing.fromJson(<String, dynamic>{
        'id': 42,
        'customer': 2,
        'property': 10,
        'property_title': 'Hyatt',
        'status': 'scheduling_failed',
        'booking_status': 'scheduling_failed',
        'fee_amount': '2000.00',
        'requires_fee_resolution': true,
      });

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: CustomerViewingActionAlert(
              viewing: viewing,
              totalActions: 1,
              onReview: () {},
            ),
          ),
        ),
      );

      expect(find.text('Protect your viewing fee for Hyatt'), findsOneWidget);
      expect(find.textContaining('payment remains protected'), findsOneWidget);
      expect(find.text('Choose Credit or Refund'), findsOneWidget);
    });
  });
}

Viewing _rescheduledViewing() {
  return Viewing.fromJson(<String, dynamic>{
    'id': 41,
    'customer': 2,
    'property': 9,
    'property_title': 'Kioo',
    'requested_date': '2027-02-10',
    'requested_time': '10:00:00',
    'status': 'reschedule_proposed',
    'booking_status': 'reschedule_proposed',
    'proposed_date': '2027-02-12',
    'proposed_time': '16:00:00',
    'partner_response_message': 'The owner is available later.',
    'fee_amount': '400.00',
    'reschedule_decline_count': 0,
    'remaining_reschedule_proposals': 2,
    'requires_fee_resolution': false,
  });
}
