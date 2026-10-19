import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:url_launcher/url_launcher.dart';

/// Shared recruitment entry: no customer credentials are passed to the website.
class PartnerApplicationLink extends StatefulWidget {
  const PartnerApplicationLink({super.key, this.compact = false, this.openUrl});

  final bool compact;
  final Future<bool> Function(Uri)? openUrl;

  static final Uri applicationUrl = Uri.https(
    'patahao.app',
    '/become-a-partner/',
  );

  @override
  State<PartnerApplicationLink> createState() => _PartnerApplicationLinkState();
}

class _PartnerApplicationLinkState extends State<PartnerApplicationLink> {
  bool _opening = false;

  Future<void> _open() async {
    if (_opening) return;
    setState(() => _opening = true);
    var opened = false;
    try {
      opened = await (widget.openUrl?.call(PartnerApplicationLink.applicationUrl) ??
          launchUrl(
            PartnerApplicationLink.applicationUrl,
            mode: LaunchMode.externalApplication,
          ));
    } catch (_) {
      // Fall back to a copyable link when the browser is unavailable.
    } finally {
      if (mounted) setState(() => _opening = false);
    }
    if (!mounted || opened) return;
    showDialog<void>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('Open the partner application'),
        content: SelectableText(
          'We could not open your browser. Copy this link and open it in '
          'your browser:\n\n${PartnerApplicationLink.applicationUrl}',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext),
            child: const Text('Close'),
          ),
          TextButton(
            onPressed: () async {
              try {
                await Clipboard.setData(
                  ClipboardData(
                    text: PartnerApplicationLink.applicationUrl.toString(),
                  ),
                );
                if (!dialogContext.mounted) return;
                Navigator.pop(dialogContext);
              } catch (_) {
                // The selectable URL remains available for manual copying.
              }
            },
            child: const Text('Copy link'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (widget.compact) {
      return Card(
        child: ListTile(
          leading: const Icon(Icons.handshake_outlined),
          title: const Text('Become a Partner'),
          subtitle: const Text(
            'Apply online. Office training and approval are required.',
          ),
          trailing: _opening
              ? const SizedBox(
                  width: 20,
                  height: 20,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              : const Icon(Icons.open_in_new, size: 20),
          onTap: _opening ? null : _open,
        ),
      );
    }
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 12),
      child: Column(
        children: [
          const Text('Want to work with Pata Hao?', textAlign: TextAlign.center),
          TextButton.icon(
            onPressed: _opening ? null : _open,
            icon: _opening
                ? const SizedBox(
                    width: 18,
                    height: 18,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Icon(Icons.open_in_new, size: 18),
            label: Text(_opening ? 'Opening application…' : 'Become a Partner'),
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
