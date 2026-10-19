import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:url_launcher/url_launcher.dart';

/// Every recruitment entry opens the same public onboarding destination.
class PartnerApplicationLink extends StatelessWidget {
  const PartnerApplicationLink({super.key});

  static final Uri applicationUrl = Uri.https(
    'patahao.app',
    '/become-a-partner/',
  );

  Future<void> _open(BuildContext context) async {
    try {
      if (await launchUrl(applicationUrl, mode: LaunchMode.externalApplication)) {
        return;
      }
    } catch (_) {
      // Offer a copyable URL when no browser can handle the request.
    }
    if (!context.mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: const Text('Could not open your browser. Copy the application link.'),
        action: SnackBarAction(
          label: 'Copy link',
          onPressed: () async {
            await Clipboard.setData(ClipboardData(text: applicationUrl.toString()));
          },
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 12),
      child: Column(
        children: [
          const Text('Want to work with Pata Hao?', textAlign: TextAlign.center),
          TextButton.icon(
            onPressed: () => _open(context),
            icon: const Icon(Icons.open_in_new, size: 18),
            label: const Text('Become a Partner'),
          ),
          const Text(
            'Apply online. Complete onboarding and training at our office.',
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 12, color: Colors.black54),
          ),
        ],
      ),
    );
  }
}
