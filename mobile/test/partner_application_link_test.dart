import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/widgets/partner_application_link.dart';

void main() {
  testWidgets('opens public onboarding without customer credentials', (tester) async {
    Uri? opened;
    await tester.pumpWidget(MaterialApp(
      home: Scaffold(body: PartnerApplicationLink(openUrl: (uri) async {
        opened = uri;
        return true;
      })),
    ));
    await tester.tap(find.text('Become a Partner'));
    await tester.pumpAndSettle();
    expect(opened.toString(), 'https://patahao.app/become-a-partner/');
    expect(opened!.hasQuery, isFalse);
    expect(find.text('Open the partner application'), findsNothing);
  });

  testWidgets('offers a selectable URL when browser opening fails', (tester) async {
    await tester.pumpWidget(MaterialApp(
      home: Scaffold(body: PartnerApplicationLink(openUrl: (_) async => false)),
    ));
    await tester.tap(find.text('Become a Partner'));
    await tester.pumpAndSettle();
    expect(find.text('Open the partner application'), findsOneWidget);
    expect(find.text('Copy link'), findsOneWidget);
    expect(find.byType(SelectableText), findsOneWidget);
  });

  testWidgets('prevents duplicate launches while browser is opening', (tester) async {
    final pending = Completer<bool>();
    var launches = 0;
    await tester.pumpWidget(MaterialApp(
      home: Scaffold(body: PartnerApplicationLink(openUrl: (_) {
        launches++;
        return pending.future;
      })),
    ));
    await tester.tap(find.text('Become a Partner'));
    await tester.pump();
    expect(tester.widget<TextButton>(find.byWidgetPredicate((widget) => widget is TextButton)).onPressed, isNull);
    expect(launches, 1);
    pending.complete(true);
    await tester.pumpAndSettle();
    expect(find.text('Become a Partner'), findsOneWidget);
  });

  testWidgets('profile entry opens the same application page', (tester) async {
    Uri? opened;
    await tester.pumpWidget(MaterialApp(
      home: Scaffold(body: PartnerApplicationLink(compact: true, openUrl: (uri) async {
        opened = uri;
        return true;
      })),
    ));
    await tester.tap(find.text('Become a Partner'));
    await tester.pumpAndSettle();
    expect(opened.toString(), 'https://patahao.app/become-a-partner/');
  });
}
