import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import 'package:mobile/models/partner_property_photo.dart';
import 'package:mobile/models/property.dart';
import 'package:mobile/services/partner_property_service.dart';
import 'package:mobile/screens/partner_property_mandate_screen.dart';

class PartnerPropertyWorkspaceScreen extends StatefulWidget {
  const PartnerPropertyWorkspaceScreen({super.key, required this.property});

  final Property property;

  @override
  State<PartnerPropertyWorkspaceScreen> createState() {
    return _PartnerPropertyWorkspaceScreenState();
  }
}

class _PartnerPropertyWorkspaceScreenState
    extends State<PartnerPropertyWorkspaceScreen> {
  final ImagePicker _imagePicker = ImagePicker();

  List<PartnerPropertyPhoto> _photos = const [];

  bool _isLoading = true;
  bool _isUploading = false;
  String? _errorMessage;
  bool _isSubmittingForVerification = false;

  Property get property => widget.property;

  @override
  void initState() {
    super.initState();
    _loadPhotos();
  }

  Future<void> _loadPhotos() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final photos = await PartnerPropertyService.instance.fetchPropertyPhotos(
        property.id,
      );

      if (!mounted) {
        return;
      }

      setState(() {
        _photos = photos;
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

  Future<void> _pickAndUploadPhoto() async {
    if (_isUploading) {
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
                leading: const Icon(Icons.photo_camera_outlined),
                title: const Text('Take Photo'),
                subtitle: const Text('Use the camera now'),
                onTap: () {
                  Navigator.of(sheetContext).pop(ImageSource.camera);
                },
              ),
              ListTile(
                leading: const Icon(Icons.photo_library_outlined),
                title: const Text('Choose from Gallery'),
                subtitle: const Text('Select an existing photo'),
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

    final selectedImage = await _imagePicker.pickImage(
      source: source,
      imageQuality: 88,
      maxWidth: 2000,
    );

    if (selectedImage == null) {
      return;
    }

    setState(() {
      _isUploading = true;
    });

    try {
      final imageBytes = await selectedImage.readAsBytes();

      await PartnerPropertyService.instance.uploadPropertyPhoto(
        propertyId: property.id,
        imageBytes: imageBytes,
        fileName: selectedImage.name,
      );

      await _loadPhotos();

      if (!mounted) {
        return;
      }

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            source == ImageSource.camera
                ? 'Camera photo uploaded successfully.'
                : 'Photo uploaded successfully.',
          ),
        ),
      );
    } catch (error) {
      if (!mounted) {
        return;
      }

      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(_cleanError(error))));
    } finally {
      if (mounted) {
        setState(() {
          _isUploading = false;
        });
      }
    }
  }

  Future<void> _setCoverPhoto(PartnerPropertyPhoto photo) async {
    if (photo.isCover) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('This is already the cover photo.')),
      );

      return;
    }

    try {
      await PartnerPropertyService.instance.setCoverPhoto(photo.id);

      await _loadPhotos();

      if (!mounted) {
        return;
      }

      ScaffoldMessenger.of(
        context,
      ).showSnackBar(const SnackBar(content: Text('Cover photo updated.')));
    } catch (error) {
      if (!mounted) {
        return;
      }

      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(_cleanError(error))));
    }
  }

  Future<void> _deletePhoto(PartnerPropertyPhoto photo) async {
    final shouldDelete = await showDialog<bool>(
      context: context,
      builder: (dialogContext) {
        return AlertDialog(
          title: const Text('Delete photo?'),
          content: const Text(
            'This photo will be permanently removed from the property.',
          ),
          actions: [
            TextButton(
              onPressed: () {
                Navigator.of(dialogContext).pop(false);
              },
              child: const Text('Cancel'),
            ),
            FilledButton(
              onPressed: () {
                Navigator.of(dialogContext).pop(true);
              },
              child: const Text('Delete'),
            ),
          ],
        );
      },
    );

    if (shouldDelete != true) {
      return;
    }

    try {
      await PartnerPropertyService.instance.deletePropertyPhoto(photo.id);

      await _loadPhotos();

      if (!mounted) {
        return;
      }

      ScaffoldMessenger.of(
        context,
      ).showSnackBar(const SnackBar(content: Text('Photo deleted.')));
    } catch (error) {
      if (!mounted) {
        return;
      }

      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(_cleanError(error))));
    }
  }

  Future<void> _openPropertyMandate() async {
    final changed = await Navigator.of(context).push<bool>(
      MaterialPageRoute<bool>(
        builder: (_) => PartnerPropertyMandateScreen(property: property),
      ),
    );

    if (!mounted) {
      return;
    }

    if (changed == true) {
      await _loadPhotos();
    }
  }

  Future<void> _showPhotoActions(PartnerPropertyPhoto photo) async {
    await showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      builder: (sheetContext) {
        return SafeArea(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              if (!photo.isCover)
                ListTile(
                  leading: const Icon(Icons.star_outline),
                  title: const Text('Set as cover photo'),
                  onTap: () {
                    Navigator.of(sheetContext).pop();
                    _setCoverPhoto(photo);
                  },
                ),
              ListTile(
                leading: const Icon(Icons.fullscreen),
                title: const Text('View full screen'),
                onTap: () {
                  Navigator.of(sheetContext).pop();
                  _openFullScreenPhoto(photo);
                },
              ),
              ListTile(
                leading: const Icon(Icons.delete_outline),
                title: const Text('Delete photo'),
                onTap: () {
                  Navigator.of(sheetContext).pop();
                  _deletePhoto(photo);
                },
              ),
            ],
          ),
        );
      },
    );
  }

  void _openFullScreenPhoto(PartnerPropertyPhoto photo) {
    Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (context) {
          return _FullScreenPropertyPhoto(photo: photo);
        },
      ),
    );
  }

  Future<void> _submitForVerification() async {
    if (_isSubmittingForVerification) {
      return;
    }

    final property = widget.property;

    final shouldSubmit = await showDialog<bool>(
      context: context,
      builder: (dialogContext) {
        return AlertDialog(
          title: const Text('Submit for Verification?'),
          content: Text(
            'Submit "${property.title}" to Pata Hao for verification? '
            'Make sure the property details and photos are correct.',
          ),
          actions: [
            TextButton(
              onPressed: () {
                Navigator.of(dialogContext).pop(false);
              },
              child: const Text('Cancel'),
            ),
            FilledButton(
              onPressed: () {
                Navigator.of(dialogContext).pop(true);
              },
              child: const Text('Submit'),
            ),
          ],
        );
      },
    );

    if (shouldSubmit != true || !mounted) {
      return;
    }

    setState(() {
      _isSubmittingForVerification = true;
    });

    try {
      final result = await PartnerPropertyService.instance
          .submitPropertyForVerification(property.id);

      if (!mounted) {
        return;
      }

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            result['detail']?.toString() ??
                'Property submitted for verification.',
          ),
        ),
      );

      Navigator.of(context).pop(true);
    } catch (error) {
      if (!mounted) {
        return;
      }

      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(_cleanError(error))));
    } finally {
      if (mounted) {
        setState(() {
          _isSubmittingForVerification = false;
        });
      }
    }
  }

  String _cleanError(Object error) {
    return error.toString().replaceFirst(RegExp(r'^Exception:\s*'), '');
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('PROPERTY WORKSPACE V2')),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _isUploading ? null : _pickAndUploadPhoto,
        icon: _isUploading
            ? const SizedBox(
                width: 20,
                height: 20,
                child: CircularProgressIndicator(strokeWidth: 2),
              )
            : const Icon(Icons.add_photo_alternate_outlined),
        label: Text(_isUploading ? 'Uploading...' : 'Add Photo'),
      ),
      body: RefreshIndicator(
        onRefresh: _loadPhotos,
        child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 100),
          children: [
            _PropertyHeader(property: property),
            if (property.verificationReturnReason.trim().isNotEmpty) ...[
              const SizedBox(height: 16),

              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Row(
                        children: [
                          Icon(Icons.info_outline),
                          SizedBox(width: 8),
                          Text(
                            'Changes requested by Pata Hao',
                            style: TextStyle(
                              fontSize: 17,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 10),
                      Text(property.verificationReturnReason),
                      const SizedBox(height: 10),
                      const Text(
                        'Make the requested changes, then submit '
                        'the property for verification again.',
                      ),
                    ],
                  ),
                ),
              ),
            ],
            if (property.status == 'draft') ...[
              const SizedBox(height: 16),

              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Row(
                        children: [
                          Icon(Icons.assignment_turned_in_outlined),
                          SizedBox(width: 8),
                          Text(
                            'Commercial Authorization',
                            style: TextStyle(
                              fontSize: 17,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 10),
                      const Text(
                        'Complete the owner details, commission terms, '
                        'and digital property mandate before submitting '
                        'this property for verification.',
                      ),
                      const SizedBox(height: 14),
                      SizedBox(
                        width: double.infinity,
                        child: FilledButton.icon(
                          onPressed: _openPropertyMandate,
                          icon: const Icon(Icons.handshake_outlined),
                          label: const Text('Complete Property Mandate'),
                        ),
                      ),
                    ],
                  ),
                ),
              ),

              const SizedBox(height: 16),

              SizedBox(
                width: double.infinity,
                child: FilledButton.icon(
                  onPressed: _isSubmittingForVerification
                      ? null
                      : _submitForVerification,
                  icon: _isSubmittingForVerification
                      ? const SizedBox(
                          width: 18,
                          height: 18,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Icon(Icons.verified_outlined),
                  label: Text(
                    _isSubmittingForVerification
                        ? 'Submitting...'
                        : 'Submit for Verification',
                  ),
                ),
              ),

              const Text(
                'Pata Hao will verify the property only after '
                'the commercial authorization and mandate requirements '
                'are complete.',
                textAlign: TextAlign.center,
              ),
            ],

            const SizedBox(height: 18),

            const Text(
              'Photos',
              style: TextStyle(fontSize: 22, fontWeight: FontWeight.w700),
            ),

            const SizedBox(height: 6),

            const Text(
              'Add clear photos of the exterior, rooms, '
              'kitchen, and bathroom.',
            ),

            const SizedBox(height: 18),

            _buildPhotoContent(),
          ],
        ),
      ),
    );
  }

  Widget _buildPhotoContent() {
    if (_isLoading) {
      return const Padding(
        padding: EdgeInsets.symmetric(vertical: 48),
        child: Center(child: CircularProgressIndicator()),
      );
    }

    if (_errorMessage != null) {
      return _ErrorPanel(message: _errorMessage!, onRetry: _loadPhotos);
    }

    if (_photos.isEmpty) {
      return _EmptyPhotoPanel(onAddPhoto: _pickAndUploadPhoto);
    }

    return GridView.builder(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      itemCount: _photos.length,
      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: 2,
        crossAxisSpacing: 12,
        mainAxisSpacing: 12,
        childAspectRatio: 1.05,
      ),
      itemBuilder: (context, index) {
        final photo = _photos[index];

        return _PhotoCard(
          photo: photo,
          onTap: () => _openFullScreenPhoto(photo),
          onMorePressed: () => _showPhotoActions(photo),
        );
      },
    );
  }
}

class _PropertyHeader extends StatelessWidget {
  const _PropertyHeader({required this.property});

  final Property property;

  @override
  Widget build(BuildContext context) {
    final estate = property.estate.trim();

    final locationParts = <String>[
      if (estate.isNotEmpty) estate,
      property.town,
      property.county,
    ];

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              width: 52,
              height: 52,
              decoration: BoxDecoration(
                color: Theme.of(context).colorScheme.primaryContainer,
                borderRadius: BorderRadius.circular(14),
              ),
              child: Icon(
                Icons.home_work_outlined,
                color: Theme.of(context).colorScheme.onPrimaryContainer,
              ),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    property.title,
                    style: Theme.of(context).textTheme.titleLarge?.copyWith(
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(locationParts.join(', ')),
                  const SizedBox(height: 8),
                  _StatusChip(status: property.status),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _StatusChip extends StatelessWidget {
  const _StatusChip({required this.status});

  final String status;

  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: Alignment.centerLeft,
      child: Chip(
        visualDensity: VisualDensity.compact,
        label: Text(
          status
              .replaceAll('_', ' ')
              .split(' ')
              .map(
                (word) => word.isEmpty
                    ? word
                    : '${word[0].toUpperCase()}${word.substring(1)}',
              )
              .join(' '),
        ),
      ),
    );
  }
}

class _PhotoCard extends StatelessWidget {
  const _PhotoCard({
    required this.photo,
    required this.onTap,
    required this.onMorePressed,
  });

  final PartnerPropertyPhoto photo;
  final VoidCallback onTap;
  final VoidCallback onMorePressed;

  @override
  Widget build(BuildContext context) {
    return Material(
      clipBehavior: Clip.antiAlias,
      borderRadius: BorderRadius.circular(16),
      child: InkWell(
        onTap: onTap,
        child: Stack(
          fit: StackFit.expand,
          children: [
            Image.network(
              photo.imageUrl,
              fit: BoxFit.cover,
              errorBuilder: (context, error, stackTrace) {
                return const ColoredBox(
                  color: Color(0xFFE5E7EB),
                  child: Center(
                    child: Icon(Icons.broken_image_outlined, size: 40),
                  ),
                );
              },
              loadingBuilder: (context, child, loadingProgress) {
                if (loadingProgress == null) {
                  return child;
                }

                return const ColoredBox(
                  color: Color(0xFFF3F4F6),
                  child: Center(child: CircularProgressIndicator()),
                );
              },
            ),
            Positioned(
              top: 8,
              right: 8,
              child: Material(
                color: Colors.black54,
                shape: const CircleBorder(),
                child: IconButton(
                  onPressed: onMorePressed,
                  icon: const Icon(Icons.more_vert, color: Colors.white),
                  tooltip: 'Photo actions',
                ),
              ),
            ),
            if (photo.isCover)
              Positioned(
                left: 8,
                bottom: 8,
                child: Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 10,
                    vertical: 6,
                  ),
                  decoration: BoxDecoration(
                    color: Colors.black87,
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: const Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(Icons.star, size: 16, color: Colors.white),
                      SizedBox(width: 4),
                      Text(
                        'Cover',
                        style: TextStyle(
                          color: Colors.white,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _EmptyPhotoPanel extends StatelessWidget {
  const _EmptyPhotoPanel({required this.onAddPhoto});

  final VoidCallback onAddPhoto;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 40),
        child: Column(
          children: [
            const Icon(Icons.photo_library_outlined, size: 54),
            const SizedBox(height: 14),
            Text(
              'No property photos yet',
              style: Theme.of(
                context,
              ).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: 8),
            const Text(
              'Upload the first photo. It will automatically become the cover photo.',
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 18),
            FilledButton.icon(
              onPressed: onAddPhoto,
              icon: const Icon(Icons.add_photo_alternate_outlined),
              label: const Text('Add First Photo'),
            ),
          ],
        ),
      ),
    );
  }
}

class _ErrorPanel extends StatelessWidget {
  const _ErrorPanel({required this.message, required this.onRetry});

  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          children: [
            const Icon(Icons.error_outline, size: 48),
            const SizedBox(height: 12),
            Text(message, textAlign: TextAlign.center),
            const SizedBox(height: 16),
            FilledButton.icon(
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

class _FullScreenPropertyPhoto extends StatelessWidget {
  const _FullScreenPropertyPhoto({required this.photo});

  final PartnerPropertyPhoto photo;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        backgroundColor: Colors.black,
        foregroundColor: Colors.white,
        title: Text(photo.isCover ? 'Cover Photo' : 'Property Photo'),
      ),
      body: Center(
        child: InteractiveViewer(
          minScale: 0.8,
          maxScale: 4,
          child: Image.network(
            photo.imageUrl,
            fit: BoxFit.contain,
            errorBuilder: (context, error, stackTrace) {
              return const Center(
                child: Icon(
                  Icons.broken_image_outlined,
                  color: Colors.white,
                  size: 64,
                ),
              );
            },
          ),
        ),
      ),
    );
  }
}
