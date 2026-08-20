import 'package:flutter/material.dart';

import '../widgets/pata_hao_network_image.dart';

class PropertyPhotoViewerScreen extends StatefulWidget {
  const PropertyPhotoViewerScreen({
    super.key,
    required this.imageUrls,
    required this.initialIndex,
    required this.title,
  });

  final List<String> imageUrls;
  final int initialIndex;
  final String title;

  @override
  State<PropertyPhotoViewerScreen> createState() {
    return _PropertyPhotoViewerScreenState();
  }
}

class _PropertyPhotoViewerScreenState extends State<PropertyPhotoViewerScreen> {
  late final PageController _pageController;
  late int _currentIndex;

  @override
  void initState() {
    super.initState();

    final safeIndex = widget.imageUrls.isEmpty
        ? 0
        : widget.initialIndex.clamp(0, widget.imageUrls.length - 1);

    _currentIndex = safeIndex;

    _pageController = PageController(initialPage: safeIndex);
  }

  @override
  void dispose() {
    _pageController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        backgroundColor: Colors.black,
        foregroundColor: Colors.white,
        title: Text(widget.title, maxLines: 1, overflow: TextOverflow.ellipsis),
        actions: [
          if (widget.imageUrls.length > 1)
            Padding(
              padding: const EdgeInsets.only(right: 16),
              child: Center(
                child: Text(
                  '${_currentIndex + 1} / ${widget.imageUrls.length}',
                  style: const TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
            ),
        ],
      ),
      body: widget.imageUrls.isEmpty
          ? const Center(
              child: Icon(
                Icons.image_not_supported_outlined,
                size: 72,
                color: Colors.white54,
              ),
            )
          : PageView.builder(
              controller: _pageController,
              itemCount: widget.imageUrls.length,
              onPageChanged: (index) {
                setState(() {
                  _currentIndex = index;
                });
              },
              itemBuilder: (context, index) {
                return InteractiveViewer(
                  minScale: 1,
                  maxScale: 4,
                  child: Center(
                    child: PataHaoNetworkImage(
                      imageUrl: widget.imageUrls[index],
                      width: double.infinity,
                      height: double.infinity,
                      fit: BoxFit.contain,
                    ),
                  ),
                );
              },
            ),
    );
  }
}
