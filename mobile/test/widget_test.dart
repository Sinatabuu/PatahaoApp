import 'package:flutter_test/flutter_test.dart';

import 'package:mobile/main.dart';

void main() {
  testWidgets('Pata Hao app loads', (WidgetTester tester) async {
    await tester.pumpWidget(const PataHaoApp());

    expect(find.byType(PataHaoApp), findsOneWidget);
  });
}
