import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import 'package:mobile/models/property.dart';
import 'package:mobile/screens/property_video_screen.dart';
import 'package:mobile/services/partner_property_service.dart';

class PartnerPropertyVideoScreen extends StatefulWidget {
  const PartnerPropertyVideoScreen({super.key, required this.property});

  final Property property;

  @override
  State<PartnerPropertyVideoScreen> createState() =>
      _PartnerPropertyVideoScreenState();
}

class _PartnerPropertyVideoScreenState
    extends State<PartnerPropertyVideoScreen> {
  static const int _maximumVideoBytes = 100 * 1024 * 1024;

  final ImagePicker _picker = ImagePicker();
  List<PropertyVideo> _videos = const [];
  bool _isLoading = true;
  bool _isUploading = false;
  String? _errorMessage;
  XFile? _retryVideo;
  String _retryTitle = '';
  String _retryDescription = '';

  bool get _canManage {
    return {'draft', 'pending', 'published'}.contains(widget.property.status);
  }

  bool get _canUpload {
    return !_isUploading && _videos.length < 3 && _canManage;
  }

  @override
  void initState() {
    super.initState();
    _loadVideos();
  }

  Future<void> _loadVideos() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final videos = await PartnerPropertyService.instance.fetchPropertyVideos(
        widget.property.id,
      );

      if (!mounted) {
        return;
      }

      setState(() {
        _videos = videos;
        _isLoading = false;
      });
    } catch (error) {
      if (!mounted) {
        return;
      }

      setState(() {
        _isLoading = false;
        _errorMessage = _cleanError(error);
      });
    }
  }

  Future<void> _chooseVideo() async {
    if (!_canUpload) {
      return;
    }

    final source = await showModalBottomSheet<ImageSource>(
      context: context,
      showDragHandle: true,
      builder: (sheetContext) {
        return SafeArea(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              ListTile(
                leading: const Icon(Icons.videocam_outlined),
                title: const Text('Record walkthrough'),
                subtitle: const Text('Record up to two minutes'),
                onTap: () {
                  Navigator.of(sheetContext).pop(ImageSource.camera);
                },
              ),
              ListTile(
                leading: const Icon(Icons.video_library_outlined),
                title: const Text('Choose from gallery'),
                subtitle: const Text('Select an existing MP4 video'),
                onTap: () {
                  Navigator.of(sheetContext).pop(ImageSource.gallery);
                },
              ),
            ],
          ),
        );
      },
    );

    if (source == null || !mounted) {
      return;
    }

    final selected = await _picker.pickVideo(
      source: source,
      maxDuration: const Duration(minutes: 2),
    );

    if (selected == null || !mounted) {
      return;
    }

    if (!selected.name.toLowerCase().endsWith('.mp4')) {
      _showMessage('Choose an MP4 video encoded with H.264.');
      return;
    }

    final fileSize = await selected.length();

    if (fileSize > _maximumVideoBytes) {
      _showMessage('The video must be 100 MB or smaller.');
      return;
    }

    final details = await _requestVideoDetails();

    if (details == null || !mounted) {
      return;
    }

    await _uploadVideo(selected, title: details.$1, description: details.$2);
  }

  Future<(String, String)?> _requestVideoDetails({
    String? title,
    String? description,
  }) async {
    final titleController = TextEditingController(
      text: title ?? '${widget.property.title} walkthrough',
    );
    final descriptionController = TextEditingController(
      text: description ?? '',
    );

    final result = await showDialog<(String, String)>(
      context: context,
      builder: (dialogContext) {
        return AlertDialog(
          title: const Text('Walkthrough details'),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextField(
                  controller: titleController,
                  maxLength: 255,
                  decoration: const InputDecoration(
                    labelText: 'Title',
                    hintText: 'Example: Full apartment tour',
                  ),
                ),
                TextField(
                  controller: descriptionController,
                  minLines: 2,
                  maxLines: 4,
                  decoration: const InputDecoration(
                    labelText: 'Description (optional)',
                  ),
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(dialogContext).pop(),
              child: const Text('Cancel'),
            ),
            FilledButton(
              onPressed: () {
                Navigator.of(dialogContext).pop((
                  titleController.text.trim(),
                  descriptionController.text.trim(),
                ));
              },
              child: const Text('Continue'),
            ),
          ],
        );
      },
    );

    titleController.dispose();
    descriptionController.dispose();
    return result;
  }

  Future<void> _uploadVideo(
    XFile video, {
    required String title,
    required String description,
  }) async {
    var uploadCompleted = false;

    setState(() {
      _isUploading = true;
      _retryVideo = null;
    });

    try {
      await PartnerPropertyService.instance.uploadPropertyVideo(
        propertyId: widget.property.id,
        filePath: video.path,
        fileName: video.name,
        title: title,
        description: description,
      );
      uploadCompleted = true;
      await _loadVideos();

      if (!mounted) {
        return;
      }

      _showMessage(
        'Video uploaded. It will appear to customers after staff approval.',
      );
    } catch (error) {
      if (!mounted) {
        return;
      }

      if (!uploadCompleted) {
        setState(() {
          _retryVideo = video;
          _retryTitle = title;
          _retryDescription = description;
        });
      }
      _showMessage(
        uploadCompleted
            ? 'Video uploaded, but the list could not refresh. '
                  'Pull down to reload.'
            : _cleanError(error),
        action: uploadCompleted
            ? null
            : SnackBarAction(label: 'Retry', onPressed: _retryUpload),
      );
    } finally {
      if (mounted) {
        setState(() {
          _isUploading = false;
        });
      }
    }
  }

  void _retryUpload() {
    final video = _retryVideo;

    if (video == null || _isUploading) {
      return;
    }

    _uploadVideo(video, title: _retryTitle, description: _retryDescription);
  }

  Future<void> _editVideo(PropertyVideo video) async {
    final details = await _requestVideoDetails(
      title: video.title,
      description: video.description,
    );

    if (details == null || !mounted) {
      return;
    }

    try {
      await PartnerPropertyService.instance.updatePropertyVideo(
        videoId: video.id,
        title: details.$1,
        description: details.$2,
      );
      await _loadVideos();
      _showMessage('Walkthrough details updated.');
    } catch (error) {
      _showMessage(_cleanError(error));
    }
  }

  Future<void> _setFeatured(PropertyVideo video) async {
    try {
      await PartnerPropertyService.instance.updatePropertyVideo(
        videoId: video.id,
        isFeatured: true,
      );
      await _loadVideos();
      _showMessage('Featured walkthrough updated.');
    } catch (error) {
      _showMessage(_cleanError(error));
    }
  }

  Future<void> _deleteVideo(PropertyVideo video) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) {
        return AlertDialog(
          title: const Text('Delete walkthrough?'),
          content: const Text(
            'This video and its staff review record will be permanently removed.',
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(dialogContext).pop(false),
              child: const Text('Cancel'),
            ),
            FilledButton(
              onPressed: () => Navigator.of(dialogContext).pop(true),
              child: const Text('Delete'),
            ),
          ],
        );
      },
    );

    if (confirmed != true || !mounted) {
      return;
    }

    try {
      await PartnerPropertyService.instance.deletePropertyVideo(video.id);
      await _loadVideos();
      _showMessage('Walkthrough deleted.');
    } catch (error) {
      _showMessage(_cleanError(error));
    }
  }

  void _preview(PropertyVideo video) {
    if (video.video.trim().isEmpty) {
      _showMessage('This video is not available for preview.');
      return;
    }

    Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder: (_) =>
            PropertyVideoScreen(videoUrl: video.video, title: video.title),
      ),
    );
  }

  Future<void> _showActions(PropertyVideo video) async {
    await showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      builder: (sheetContext) {
        return SafeArea(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              ListTile(
                leading: const Icon(Icons.play_circle_outline),
                title: const Text('Preview video'),
                onTap: () {
                  Navigator.of(sheetContext).pop();
                  _preview(video);
                },
              ),
              if (!video.isFeatured)
                ListTile(
                  leading: const Icon(Icons.star_outline),
                  title: const Text('Set as featured'),
                  onTap: () {
                    Navigator.of(sheetContext).pop();
                    _setFeatured(video);
                  },
                ),
              ListTile(
                leading: const Icon(Icons.edit_outlined),
                title: const Text('Edit title and description'),
                onTap: () {
                  Navigator.of(sheetContext).pop();
                  _editVideo(video);
                },
              ),
              ListTile(
                leading: const Icon(Icons.delete_outline),
                title: const Text('Delete video'),
                onTap: () {
                  Navigator.of(sheetContext).pop();
                  _deleteVideo(video);
                },
              ),
            ],
          ),
        );
      },
    );
  }

  String _cleanError(Object error) {
    return error.toString().replaceFirst(RegExp(r'^Exception:\s*'), '');
  }

  void _showMessage(String message, {SnackBarAction? action}) {
    if (!mounted) {
      return;
    }

    ScaffoldMessenger.of(
      context,
    ).showSnackBar(SnackBar(content: Text(message), action: action));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Walkthrough videos'),
        backgroundColor: const Color(0xFF14532D),
        foregroundColor: Colors.white,
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _canUpload ? _chooseVideo : null,
        icon: _isUploading
            ? const SizedBox(
                width: 20,
                height: 20,
                child: CircularProgressIndicator(strokeWidth: 2),
              )
            : const Icon(Icons.video_call_outlined),
        label: Text(_isUploading ? 'Uploading...' : 'Add Video'),
      ),
      body: RefreshIndicator(
        onRefresh: _loadVideos,
        child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 100),
          children: [
            _VideoRulesCard(videoCount: _videos.length),
            if (_isUploading) ...[
              const SizedBox(height: 12),
              const LinearProgressIndicator(),
              const SizedBox(height: 8),
              const Text(
                'Uploading and checking the video. Keep this page open.',
                textAlign: TextAlign.center,
              ),
            ],
            const SizedBox(height: 16),
            if (_isLoading)
              const Padding(
                padding: EdgeInsets.symmetric(vertical: 48),
                child: Center(child: CircularProgressIndicator()),
              )
            else if (_errorMessage != null)
              _VideoErrorPanel(message: _errorMessage!, onRetry: _loadVideos)
            else if (_videos.isEmpty)
              const _EmptyVideoPanel()
            else
              for (final video in _videos) ...[
                _PartnerVideoCard(
                  video: video,
                  onPreview: () => _preview(video),
                  onMore: _canManage ? () => _showActions(video) : null,
                ),
                const SizedBox(height: 12),
              ],
          ],
        ),
      ),
    );
  }
}

class _VideoRulesCard extends StatelessWidget {
  const _VideoRulesCard({required this.videoCount});

  final int videoCount;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.hd_outlined, color: Color(0xFF166534)),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    'HD walkthroughs · $videoCount/3',
                    style: const TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 10),
            const Text(
              'MP4 (H.264), 480p–1080p, 5 seconds–2 minutes, and no more '
              'than 100 MB. Hold the phone steady and show rooms in a '
              'natural order.',
            ),
            const SizedBox(height: 8),
            const Text(
              'Standard walkthroughs are supported now. Interactive 360° '
              'video will be added after launch.',
              style: TextStyle(color: Color(0xFF4B5563)),
            ),
          ],
        ),
      ),
    );
  }
}

class _PartnerVideoCard extends StatelessWidget {
  const _PartnerVideoCard({
    required this.video,
    required this.onPreview,
    required this.onMore,
  });

  final PropertyVideo video;
  final VoidCallback onPreview;
  final VoidCallback? onMore;

  @override
  Widget build(BuildContext context) {
    final (statusLabel, statusColor, statusIcon) = switch (video.reviewStatus) {
      'approved' => (
        'Approved',
        const Color(0xFF166534),
        Icons.verified_outlined,
      ),
      'rejected' => (
        'Replace video',
        const Color(0xFFB91C1C),
        Icons.error_outline,
      ),
      _ => (
        'Awaiting staff review',
        const Color(0xFFB45309),
        Icons.schedule_outlined,
      ),
    };

    return Card(
      clipBehavior: Clip.antiAlias,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          InkWell(
            onTap: onPreview,
            child: AspectRatio(
              aspectRatio: 16 / 9,
              child: Stack(
                fit: StackFit.expand,
                children: [
                  if (video.thumbnail.trim().isNotEmpty)
                    Image.network(
                      video.thumbnail,
                      fit: BoxFit.cover,
                      errorBuilder: (_, _, _) => const _VideoPlaceholder(),
                    )
                  else
                    const _VideoPlaceholder(),
                  Container(color: Colors.black26),
                  const Center(
                    child: CircleAvatar(
                      radius: 28,
                      backgroundColor: Colors.black54,
                      child: Icon(
                        Icons.play_arrow_rounded,
                        color: Colors.white,
                        size: 40,
                      ),
                    ),
                  ),
                  if (video.isFeatured)
                    const Positioned(
                      left: 10,
                      top: 10,
                      child: Chip(
                        avatar: Icon(Icons.star, size: 17),
                        label: Text('Featured'),
                      ),
                    ),
                ],
              ),
            ),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 12, 8, 14),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        video.title.trim().isEmpty
                            ? 'Property walkthrough'
                            : video.title,
                        style: const TextStyle(
                          fontSize: 17,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                    if (onMore != null)
                      IconButton(
                        tooltip: 'Video actions',
                        onPressed: onMore,
                        icon: const Icon(Icons.more_vert),
                      ),
                  ],
                ),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    Chip(
                      avatar: Icon(statusIcon, size: 17, color: statusColor),
                      label: Text(statusLabel),
                    ),
                    if (video.duration > 0)
                      Chip(label: Text(video.durationLabel)),
                    if (video.resolutionLabel.isNotEmpty)
                      Chip(label: Text(video.resolutionLabel)),
                    if (video.fileSizeLabel.isNotEmpty)
                      Chip(label: Text(video.fileSizeLabel)),
                  ],
                ),
                if (video.isRejected &&
                    video.rejectionReason.trim().isNotEmpty) ...[
                  const SizedBox(height: 10),
                  Text(
                    video.rejectionReason,
                    style: const TextStyle(color: Color(0xFF991B1B)),
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _VideoPlaceholder extends StatelessWidget {
  const _VideoPlaceholder();

  @override
  Widget build(BuildContext context) {
    return const ColoredBox(
      color: Color(0xFFE5E7EB),
      child: Center(
        child: Icon(Icons.movie_outlined, size: 54, color: Color(0xFF4B5563)),
      ),
    );
  }
}

class _EmptyVideoPanel extends StatelessWidget {
  const _EmptyVideoPanel();

  @override
  Widget build(BuildContext context) {
    return const Card(
      child: Padding(
        padding: EdgeInsets.all(28),
        child: Column(
          children: [
            Icon(Icons.video_library_outlined, size: 52),
            SizedBox(height: 12),
            Text(
              'No walkthrough videos yet',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700),
            ),
            SizedBox(height: 6),
            Text(
              'Add a clear tour to help customers understand the property '
              'before they request a viewing.',
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }
}

class _VideoErrorPanel extends StatelessWidget {
  const _VideoErrorPanel({required this.message, required this.onRetry});

  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          children: [
            const Icon(Icons.error_outline, size: 44),
            const SizedBox(height: 10),
            Text(message, textAlign: TextAlign.center),
            const SizedBox(height: 12),
            OutlinedButton.icon(
              onPressed: onRetry,
              icon: const Icon(Icons.refresh),
              label: const Text('Try Again'),
            ),
          ],
        ),
      ),
    );
  }
}
