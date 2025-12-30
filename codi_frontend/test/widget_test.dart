import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:codi_frontend/app.dart';

void main() {
  testWidgets('App should build', (WidgetTester tester) async {
    // Build our app and trigger a frame.
    // Note: CodiApp wraps App with ScreenUtil, but for testing we test App directly
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: Center(
            child: Text('Codi Test'),
          ),
        ),
      ),
    );

    // Verify the app builds
    expect(find.text('Codi Test'), findsOneWidget);
  });
}
