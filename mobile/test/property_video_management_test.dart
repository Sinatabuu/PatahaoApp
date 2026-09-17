import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/models/property.dart';
import 'package:mobile/screens/partner_property_video_screen.dart';

void main() {
  group('Partner property video metadata', () {
    test('parses moderation and quality details', () {
      final video = PropertyVideo.fromJson({
        'id': 17,
        'video_url': 'https://media.example.test/walkthrough.mp4',
        'thumbnail_url': 'https://media.example.test/thumbnail.jpg',
        'title': 'Full apartment tour',
        'description': 'A room-by-room walkthrough.',
        'duration': 75,
        'width': 1920,
        'height': 1080,
        'file_size': 52428800,
        'video_codec': 'h264',
        'audio_codec': 'aac',
        'is_featured': true,
        'review_status': 'pending',
        'rejection_reason': '',
      });

      expect(video.video, endsWith('walkthrough.mp4'));
      expect(video.thumbnail, endsWith('thumbnail.jpg'));
      expect(video.isFeatured, isTrue);
      expect(video.isPendingReview, isTrue);
      expect(video.durationLabel, '1:15');
      expect(video.resolutionLabel, '1920 × 1080');
      expect(video.fileSizeLabel, '50.0 MB');
    });

    test('parses returned video instructions', () {
      final video = PropertyVideo.fromJson({
        'id': 18,
        'video': '/media/property_videos/returned.mp4',
        'title': 'Dark walkthrough',
        'review_status': 'rejected',
        'rejection_reason': 'The rooms are too dark.',
      });

      expect(video.isRejected, isTrue);
      expect(video.isApproved, isFalse);
      expect(video.rejectionReason, 'The rooms are too dark.');
    });

    test('legacy public video remains safely approved', () {
      final video = PropertyVideo.fromJson({
        'id': 19,
        'video': '/media/property_videos/legacy.mp4',
      });

      expect(video.isApproved, isTrue);
      expect(video.isPendingReview, isFalse);
    });
  });

  testWidgets('walkthrough details close without a controller lifecycle error', (
    tester,
  ) async {
    (String, String)? submittedDetails;

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: Builder(
            builder: (context) {
              return FilledButton(
                onPressed: () async {
                  submittedDetails = await showDialog<(String, String)>(
                    context: context,
                    builder: (_) => const PartnerPropertyVideoDetailsDialog(
                      initialTitle: 'Original walkthrough',
                    ),
                  );
                },
                child: const Text('Open details'),
              );
            },
          ),
        ),
      ),
    );

    await tester.tap(find.text('Open details'));
    await tester.pumpAndSettle();

    final fields = find.byType(TextFormField);
    expect(fields, findsNWidgets(2));

    await tester.enterText(fields.at(0), '  Bright apartment tour  ');
    await tester.enterText(fields.at(1), '  Every room included.  ');
    await tester.tap(find.text('Continue'));
    await tester.pumpAndSettle();

    expect(tester.takeException(), isNull);
    expect(
      submittedDetails,
      ('Bright apartment tour', 'Every room included.'),
    );
  });
}
