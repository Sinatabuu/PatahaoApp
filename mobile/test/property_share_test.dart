import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/models/property.dart';
import 'package:mobile/services/property_share_service.dart';
import 'package:mobile/widgets/property_share_button.dart';
import 'package:share_plus/share_plus.dart';

Property listing({String status = 'published', String title = 'Roysambu home'}) =>
    Property.fromJson({
      'id': 42, 'title': title, 'status': status, 'listing_type': 'rent',
      'price': '25000', 'town': 'Roysambu', 'county': 'Nairobi',
      'address': 'Private address', 'verification_return_reason': 'Private staff note',
      'partner': {'id': 1, 'phone_number': '0712345678'},
    });
Widget host(PropertyShareButton button) => MaterialApp(
      home: Scaffold(appBar: AppBar(actions: [button])),
    );

void main() {
  test('shares clean public details without credentials or private fields', () {
    final content = propertyShareContent(listing());
    expect(content.uri.toString(), 'https://patahao.app/p/42/');
    expect(content.uri.hasQuery, isFalse);
    expect(content.text, contains('KES 25,000 / month'));
    expect(content.text, contains('Roysambu, Nairobi'));
    expect(content.text, isNot(contains('Private')));
    expect(content.text, isNot(contains('0712345678')));
  });
  test('draft and closed listings cannot be shared', () {
    for (final state in ['draft', 'pending', 'reserved', 'sold', 'rented', 'archived']) {
      expect(() => propertyShareContent(listing(status: state)), throwsA(isA<PropertyShareUnavailable>()));
    }
  });
  testWidgets('rechecks listing and anchors the native share sheet', (tester) async {
    ShareParams? captured;
    await tester.pumpWidget(host(PropertyShareButton(
      property: listing(title: 'Old title'),
      loadProperty: (id) async { expect(id, 42); return listing(title: 'Current title'); },
      presentShare: (params) async { captured = params; },
    )));
    await tester.tap(find.byTooltip('Share property'));
    await tester.pumpAndSettle();
    expect(captured!.text, contains('Current title'));
    expect(captured!.text, isNot(contains('Old title')));
    expect(captured!.sharePositionOrigin!.isEmpty, isFalse);
  });
  testWidgets('prevents repeat taps while checking availability', (tester) async {
    final pending = Completer<Property>();
    var checks = 0; var shares = 0;
    await tester.pumpWidget(host(PropertyShareButton(
      property: listing(),
      loadProperty: (_) { checks++; return pending.future; },
      presentShare: (_) async { shares++; },
    )));
    await tester.tap(find.byTooltip('Share property'));
    await tester.pump();
    expect(tester.widget<IconButton>(find.byType(IconButton)).onPressed, isNull);
    expect(checks, 1);
    pending.complete(listing()); await tester.pumpAndSettle();
    expect(shares, 1);
  });
  testWidgets('stale saved listing never opens sharing', (tester) async {
    var shares = 0;
    await tester.pumpWidget(host(PropertyShareButton(
      property: listing(), loadProperty: (_) async => listing(status: 'sold'),
      presentShare: (_) async { shares++; },
    )));
    await tester.tap(find.byTooltip('Share property')); await tester.pumpAndSettle();
    expect(shares, 0);
    expect(find.text('This listing is no longer available to share.'), findsOneWidget);
  });
  testWidgets('native failure offers validated public link for copying', (tester) async {
    await tester.pumpWidget(host(PropertyShareButton(
      property: listing(), loadProperty: (_) async => listing(),
      presentShare: (_) async => throw PlatformException(code: 'unavailable'),
    )));
    await tester.tap(find.byTooltip('Share property')); await tester.pumpAndSettle();
    expect(find.text('Copy link'), findsOneWidget);
    await tester.tap(find.text('Copy link')); await tester.pump();
    expect((await Clipboard.getData(Clipboard.kTextPlain))!.text, 'https://patahao.app/p/42/');
  });
  testWidgets('failed availability check exposes no link', (tester) async {
    await tester.pumpWidget(host(PropertyShareButton(
      property: listing(), loadProperty: (_) async => throw Exception('network'),
    )));
    await tester.tap(find.byTooltip('Share property')); await tester.pumpAndSettle();
    expect(find.text('Copy link'), findsNothing);
    expect(find.textContaining('Check your connection'), findsOneWidget);
  });
  testWidgets('unpublished listings have no share control', (tester) async {
    await tester.pumpWidget(host(PropertyShareButton(property: listing(status: 'draft'))));
    expect(find.byTooltip('Share property'), findsNothing);
  });
}
