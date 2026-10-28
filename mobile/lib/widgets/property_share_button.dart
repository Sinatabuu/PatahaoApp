import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:share_plus/share_plus.dart';

import '../models/property.dart';
import '../services/property_service.dart';
import '../services/property_share_service.dart';

typedef PropertyShareLoader = Future<Property> Function(int id);
typedef PropertySharePresenter = Future<void> Function(ShareParams params);

class PropertyShareButton extends StatefulWidget {
  const PropertyShareButton({
    super.key,
    required this.property,
    this.loadProperty,
    this.presentShare,
  });

  final Property property;
  final PropertyShareLoader? loadProperty;
  final PropertySharePresenter? presentShare;

  @override
  State<PropertyShareButton> createState() => _PropertyShareButtonState();
}

class _PropertyShareButtonState extends State<PropertyShareButton> {
  bool _sharing = false;

  Future<void> _share() async {
    if (_sharing) return;
    setState(() => _sharing = true);
    PropertyShareContent? content;
    try {
      // Saved properties can be stale. Recheck through the public API first.
      final fresh = await (widget.loadProperty ?? PropertyService().fetchProperty)(
        widget.property.id,
      );
      if (!mounted) return;
      if (fresh.id != widget.property.id) {
        throw const PropertyShareUnavailable();
      }
      content = propertyShareContent(fresh);
      final box = context.findRenderObject();
      Rect? origin;
      if (box is RenderBox && box.hasSize && !box.size.isEmpty) {
        origin = box.localToGlobal(Offset.zero) & box.size;
      }
      final params = ShareParams(
        text: content.text,
        subject: 'Property on Pata Hao',
        title: 'Share property',
        sharePositionOrigin: origin,
      );
      if (widget.presentShare != null) {
        await widget.presentShare!(params);
      } else {
        await SharePlus.instance.share(params);
      }
    } on PropertyShareUnavailable {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
          content: Text('This listing is no longer available to share.'),
        ));
      }
    } catch (_) {
      if (mounted) {
        final link = content?.uri.toString();
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(link == null
              ? 'Could not check this listing. Check your connection and try again.'
              : 'Could not open sharing. You can copy the property link instead.'),
          action: link == null
              ? null
              : SnackBarAction(
                  label: 'Copy link',
                  onPressed: () => Clipboard.setData(ClipboardData(text: link)),
                ),
        ));
      }
    } finally {
      if (mounted) setState(() => _sharing = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (widget.property.status != 'published') return const SizedBox.shrink();
    return IconButton(
      tooltip: 'Share property',
      onPressed: _sharing ? null : _share,
      icon: _sharing
          ? const SizedBox(
              width: 20,
              height: 20,
              child: CircularProgressIndicator(strokeWidth: 2),
            )
          : const Icon(Icons.share_outlined),
    );
  }
}
