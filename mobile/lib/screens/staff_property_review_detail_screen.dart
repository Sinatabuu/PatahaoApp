import 'package:flutter/material.dart';

import 'package:mobile/screens/property_video_screen.dart';
import 'package:mobile/services/staff_property_review_service.dart';

class StaffPropertyReviewDetailScreen extends StatefulWidget {
  const StaffPropertyReviewDetailScreen({super.key, required this.propertyId});

  final int propertyId;

  @override
  State<StaffPropertyReviewDetailScreen> createState() {
    return _StaffPropertyReviewDetailScreenState();
  }
}

class _StaffPropertyReviewDetailScreenState
    extends State<StaffPropertyReviewDetailScreen> {
  bool _isLoading = true;
  bool _isProcessing = false;
  bool _hasChanged = false;

  String? _errorMessage;

  Map<String, dynamic> _review = <String, dynamic>{};

  @override
  void initState() {
    super.initState();
    _loadReview();
  }

  Future<void> _loadReview() async {
    if (!mounted) {
      return;
    }

    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final review = await StaffPropertyReviewService.instance
          .fetchPropertyReview(widget.propertyId);

      if (!mounted) {
        return;
      }

      setState(() {
        _review = review;
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

  Future<void> _runReviewAction({
    required String confirmationTitle,
    required String confirmationMessage,
    required String successMessage,
    required Future<Map<String, dynamic>> Function() action,
    bool closeAfterSuccess = false,
  }) async {
    if (_isProcessing) {
      return;
    }

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) {
        return AlertDialog(
          title: Text(confirmationTitle),
          content: Text(confirmationMessage),
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
              child: const Text('Continue'),
            ),
          ],
        );
      },
    );

    if (confirmed != true || !mounted) {
      return;
    }

    setState(() {
      _isProcessing = true;
      _errorMessage = null;
    });

    try {
      final result = await action();

      if (!mounted) {
        return;
      }

      setState(() {
        _review = result;
        _hasChanged = true;
      });

      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(successMessage)));

      if (closeAfterSuccess && mounted) {
        Navigator.of(context).pop(true);
      }
    } catch (error) {
      if (!mounted) {
        return;
      }

      setState(() {
        _errorMessage = _cleanError(error);
      });

      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(_cleanError(error))));
    } finally {
      if (mounted) {
        setState(() {
          _isProcessing = false;
        });
      }
    }
  }

  Future<void> _verifyCommission() async {
    await _runReviewAction(
      confirmationTitle: 'Verify Commission Agreement?',
      confirmationMessage:
          'Confirm that the commission terms have been reviewed and are acceptable to Pata Hao.',
      successMessage: 'Commission agreement verified.',
      action: () {
        return StaffPropertyReviewService.instance.verifyCommission(
          widget.propertyId,
        );
      },
    );
  }

  Future<void> _lockCommission() async {
    await _runReviewAction(
      confirmationTitle: 'Lock Commission Agreement?',
      confirmationMessage:
          'Locking prevents further commercial changes to this commission agreement.',
      successMessage: 'Commission agreement locked.',
      action: () {
        return StaffPropertyReviewService.instance.lockCommission(
          widget.propertyId,
        );
      },
    );
  }

  Future<void> _approveMandate() async {
    await _runReviewAction(
      confirmationTitle: 'Approve Digital Mandate?',
      confirmationMessage:
          'Confirm that the partner declaration and property authority information have been reviewed.',
      successMessage: 'Digital mandate approved.',
      action: () {
        return StaffPropertyReviewService.instance.approveMandate(
          widget.propertyId,
        );
      },
    );
  }

  Future<void> _approvePendingVideo(int videoId) async {
    await _runReviewAction(
      confirmationTitle: 'Approve Walkthrough Video?',
      confirmationMessage:
          'This replacement will become the one customer-visible walkthrough. '
          'The previous approved video will be removed after approval.',
      successMessage: 'Walkthrough video approved.',
      closeAfterSuccess: true,
      action: () {
        return StaffPropertyReviewService.instance.approveVideo(
          propertyId: widget.propertyId,
          videoId: videoId,
        );
      },
    );
  }

  Future<void> _publishProperty() async {
    if (_isProcessing) {
      return;
    }

    final hasPendingVideo = _pendingVideo(_review['videos']) != null;

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) {
        return AlertDialog(
          title: Text(
            hasPendingVideo
                ? 'Approve Property and Video?'
                : 'Publish Property?',
          ),
          content: Text(
            hasPendingVideo
                ? 'The property and its pending walkthrough will be approved '
                      'together and become visible to customers. Final '
                      'publication checks will still run.'
                : 'This property will become visible to customers. The '
                      'backend will perform the final publication checks '
                      'before publishing.',
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
              child: Text(hasPendingVideo ? 'Approve & Publish' : 'Publish'),
            ),
          ],
        );
      },
    );

    if (confirmed != true || !mounted) {
      return;
    }

    setState(() {
      _isProcessing = true;
      _errorMessage = null;
    });

    try {
      await StaffPropertyReviewService.instance.publishProperty(
        widget.propertyId,
      );

      if (!mounted) {
        return;
      }

      _hasChanged = true;

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            hasPendingVideo
                ? 'Property and walkthrough approved and published.'
                : 'Property approved and published.',
          ),
        ),
      );

      Navigator.of(context).pop(true);
    } catch (error) {
      if (!mounted) {
        return;
      }

      setState(() {
        _errorMessage = _cleanError(error);
      });

      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(_cleanError(error))));
    } finally {
      if (mounted) {
        setState(() {
          _isProcessing = false;
        });
      }
    }
  }

  Future<void> _returnToPartner() async {
    if (_isProcessing) {
      return;
    }

    final controller = TextEditingController();

    final reason = await showDialog<String>(
      context: context,
      builder: (dialogContext) {
        String? validationMessage;

        return StatefulBuilder(
          builder: (context, setDialogState) {
            return AlertDialog(
              title: const Text('Return to Partner'),
              content: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Explain what the partner needs to correct before resubmitting.',
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: controller,
                    maxLines: 4,
                    decoration: InputDecoration(
                      labelText: 'Reason',
                      border: const OutlineInputBorder(),
                      errorText: validationMessage,
                    ),
                  ),
                ],
              ),
              actions: [
                TextButton(
                  onPressed: () {
                    Navigator.of(dialogContext).pop();
                  },
                  child: const Text('Cancel'),
                ),
                FilledButton(
                  onPressed: () {
                    final cleanReason = controller.text.trim();

                    if (cleanReason.isEmpty) {
                      setDialogState(() {
                        validationMessage = 'A reason is required.';
                      });

                      return;
                    }

                    Navigator.of(dialogContext).pop(cleanReason);
                  },
                  child: const Text('Return Property'),
                ),
              ],
            );
          },
        );
      },
    );

    controller.dispose();

    if (reason == null || reason.trim().isEmpty || !mounted) {
      return;
    }

    setState(() {
      _isProcessing = true;
      _errorMessage = null;
    });

    try {
      await StaffPropertyReviewService.instance.returnToPartner(
        propertyId: widget.propertyId,
        reason: reason,
      );

      if (!mounted) {
        return;
      }

      _hasChanged = true;

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Property returned to partner.')),
      );

      Navigator.of(context).pop(true);
    } catch (error) {
      if (!mounted) {
        return;
      }

      setState(() {
        _errorMessage = _cleanError(error);
      });

      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(_cleanError(error))));
    } finally {
      if (mounted) {
        setState(() {
          _isProcessing = false;
        });
      }
    }
  }

  Future<void> _returnPendingVideo({
    required int videoId,
    required bool closeAfterSuccess,
  }) async {
    if (_isProcessing) {
      return;
    }

    final controller = TextEditingController();

    final reason = await showDialog<String>(
      context: context,
      builder: (dialogContext) {
        String? validationMessage;

        return StatefulBuilder(
          builder: (context, setDialogState) {
            return AlertDialog(
              title: const Text('Return Walkthrough Video'),
              content: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Explain what must be corrected before the partner '
                    'uploads a replacement.',
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: controller,
                    maxLines: 4,
                    decoration: InputDecoration(
                      labelText: 'Video return reason',
                      border: const OutlineInputBorder(),
                      errorText: validationMessage,
                    ),
                  ),
                ],
              ),
              actions: [
                TextButton(
                  onPressed: () {
                    Navigator.of(dialogContext).pop();
                  },
                  child: const Text('Cancel'),
                ),
                FilledButton(
                  onPressed: () {
                    final cleanReason = controller.text.trim();

                    if (cleanReason.isEmpty) {
                      setDialogState(() {
                        validationMessage = 'A reason is required.';
                      });

                      return;
                    }

                    Navigator.of(dialogContext).pop(cleanReason);
                  },
                  child: const Text('Return Video'),
                ),
              ],
            );
          },
        );
      },
    );

    controller.dispose();

    if (reason == null || reason.trim().isEmpty || !mounted) {
      return;
    }

    setState(() {
      _isProcessing = true;
      _errorMessage = null;
    });

    try {
      final result = await StaffPropertyReviewService.instance.returnVideo(
        propertyId: widget.propertyId,
        videoId: videoId,
        reason: reason,
      );

      if (!mounted) {
        return;
      }

      setState(() {
        _review = result;
        _hasChanged = true;
      });

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Walkthrough returned to the partner.')),
      );

      if (closeAfterSuccess && mounted) {
        Navigator.of(context).pop(true);
      }
    } catch (error) {
      if (!mounted) {
        return;
      }

      setState(() {
        _errorMessage = _cleanError(error);
      });

      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(_cleanError(error))));
    } finally {
      if (mounted) {
        setState(() {
          _isProcessing = false;
        });
      }
    }
  }

  String _cleanError(Object error) {
    return error.toString().replaceFirst(RegExp(r'^Exception:\s*'), '').trim();
  }

  @override
  Widget build(BuildContext context) {
    return PopScope(
      canPop: true,
      onPopInvokedWithResult: (didPop, result) {
        if (!didPop) {
          return;
        }
      },
      child: Scaffold(
        backgroundColor: const Color(0xFFF6F8F6),
        appBar: AppBar(
          title: const Text('Property Review'),
          backgroundColor: const Color(0xFF14532D),
          foregroundColor: Colors.white,
          leading: IconButton(
            onPressed: () {
              Navigator.of(context).pop(_hasChanged);
            },
            icon: const Icon(Icons.arrow_back),
          ),
        ),
        body: _buildBody(),
      ),
    );
  }

  Widget _buildBody() {
    if (_isLoading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_errorMessage != null && _review.isEmpty) {
      return ListView(
        padding: const EdgeInsets.all(16),
        children: [
          const SizedBox(height: 60),
          _ErrorPanel(message: _errorMessage!, onRetry: _loadReview),
        ],
      );
    }

    final property = _map(_review['property']);

    final partner = _map(_review['partner']);

    final photos = _map(_review['photos']);

    final commission = _map(_review['commission']);

    final mandate = _map(_review['mandate']);

    final publishing = _map(_review['publishing']);

    final commercialReadiness = _map(_review['commercial_readiness']);

    final videos = _mapList(_review['videos']);

    final pendingVideo = _pendingVideo(videos);

    final propertyReviewRequired = _bool(_review['property_review_required']);

    final videoOnlyReview = !propertyReviewRequired && pendingVideo != null;

    final blockers = _list(_review['blockers']);

    final readyToPublish = _bool(_review['ready_to_publish']);

    final commissionExists = commission.isNotEmpty;

    final mandateExists = mandate.isNotEmpty;

    final commissionAccepted = _bool(commission['partner_accepted']);

    final commissionVerified = _bool(commission['is_verified']);

    final commissionLocked = _bool(commission['is_locked']);

    final mandateDeclared = _bool(mandate['partner_declared']);

    final mandateStatus = mandate['status']?.toString() ?? '';

    final mandateApproved = mandateStatus == 'approved';

    final canVerifyCommission =
        commissionExists && commissionAccepted && !commissionVerified;

    final canLockCommission =
        commissionExists && commissionVerified && !commissionLocked;

    final canApproveMandate =
        mandateExists &&
        mandateDeclared &&
        commissionLocked &&
        !mandateApproved;

    return RefreshIndicator(
      onRefresh: _loadReview,
      child: ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.fromLTRB(16, 16, 16, 36),
        children: [
          _PropertyCard(property: property, partner: partner),

          const SizedBox(height: 16),

          _VideoReviewCard(
            videos: videos,
            isProcessing: _isProcessing,
            showApproveAction: videoOnlyReview,
            showReturnAction: pendingVideo != null,
            onApprove: pendingVideo == null
                ? null
                : () => _approvePendingVideo(_int(pendingVideo['id'])),
            onReturn: pendingVideo == null
                ? null
                : () => _returnPendingVideo(
                    videoId: _int(pendingVideo['id']),
                    closeAfterSuccess: videoOnlyReview,
                  ),
          ),

          const SizedBox(height: 16),

          if (_errorMessage != null) ...[
            _InlineError(message: _errorMessage!),
            const SizedBox(height: 16),
          ],

          if (propertyReviewRequired) ...[
            _ReadinessCard(
              publishing: publishing,
              commercialReadiness: commercialReadiness,
              photos: photos,
              blockers: blockers,
              readyToPublish: readyToPublish,
            ),

            const SizedBox(height: 16),

            _CommissionCard(commission: commission),

            const SizedBox(height: 16),

            _MandateCard(mandate: mandate),

            const SizedBox(height: 16),

            _ActionCard(
              isProcessing: _isProcessing,
              commissionExists: commissionExists,
              commissionAccepted: commissionAccepted,
              commissionVerified: commissionVerified,
              commissionLocked: commissionLocked,
              mandateExists: mandateExists,
              mandateDeclared: mandateDeclared,
              mandateApproved: mandateApproved,
              readyToPublish: readyToPublish,
              hasPendingVideo: pendingVideo != null,
              canVerifyCommission: canVerifyCommission,
              canLockCommission: canLockCommission,
              canApproveMandate: canApproveMandate,
              onVerifyCommission: _verifyCommission,
              onLockCommission: _lockCommission,
              onApproveMandate: _approveMandate,
              onPublish: _publishProperty,
              onReturnToPartner: _returnToPartner,
            ),
          ] else if (videoOnlyReview) ...[
            const _InlineGuidance(
              message:
                  'This property is already live. Approving the replacement '
                  'will swap only the walkthrough video; returning it will '
                  'keep the current approved video visible to customers.',
            ),
          ],
        ],
      ),
    );
  }
}

class _PropertyCard extends StatelessWidget {
  const _PropertyCard({required this.property, required this.partner});

  final Map<String, dynamic> property;
  final Map<String, dynamic> partner;

  @override
  Widget build(BuildContext context) {
    final title = property['title']?.toString() ?? '';

    final town = property['town']?.toString() ?? '';

    final county = property['county']?.toString() ?? '';

    final listingType = property['listing_type']?.toString() ?? '';

    final price = _double(property['price']);

    final partnerName = partner['display_name']?.toString() ?? '';

    final amenities = (property['amenities'] as List? ?? const <dynamic>[])
        .whereType<Map>()
        .map((item) => item['name']?.toString().trim() ?? '')
        .where((name) => name.isNotEmpty)
        .toList();

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              title.isEmpty ? 'Untitled property' : title,
              style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: 5),
            Text(
              [
                if (town.trim().isNotEmpty) town.trim(),
                if (county.trim().isNotEmpty) county.trim(),
              ].join(', '),
              style: const TextStyle(color: Colors.black54),
            ),
            const SizedBox(height: 14),
            _InfoLine(label: 'Listing', value: _pretty(listingType)),
            _InfoLine(label: 'Price', value: _formatKes(price)),
            _InfoLine(
              label: 'Partner',
              value: partnerName.isEmpty ? 'Unknown partner' : partnerName,
            ),
            _InfoLine(
              label: 'Amenities',
              value: amenities.isEmpty ? 'None selected' : amenities.join(', '),
            ),
          ],
        ),
      ),
    );
  }
}

class _VideoReviewCard extends StatelessWidget {
  const _VideoReviewCard({
    required this.videos,
    required this.isProcessing,
    required this.showApproveAction,
    required this.showReturnAction,
    required this.onApprove,
    required this.onReturn,
  });

  final List<Map<String, dynamic>> videos;
  final bool isProcessing;
  final bool showApproveAction;
  final bool showReturnAction;
  final Future<void> Function()? onApprove;
  final Future<void> Function()? onReturn;

  @override
  Widget build(BuildContext context) {
    if (videos.isEmpty) {
      return const _SectionCard(
        title: 'Walkthrough Video',
        icon: Icons.videocam_outlined,
        child: _EmptyPanel(
          text:
              'No walkthrough was uploaded. Video is optional, so the '
              'property can still be reviewed and published.',
        ),
      );
    }

    final orderedVideos = [...videos]
      ..sort((left, right) {
        final leftPending = left['review_status']?.toString() == 'pending';
        final rightPending = right['review_status']?.toString() == 'pending';

        if (leftPending == rightPending) {
          return 0;
        }

        return leftPending ? -1 : 1;
      });

    return _SectionCard(
      title: 'Walkthrough Video Review',
      icon: Icons.videocam_outlined,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          ...orderedVideos.map((video) {
            return Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: _StaffVideoPreview(video: video),
            );
          }),
          if (showApproveAction) ...[
            FilledButton.icon(
              onPressed: isProcessing ? null : onApprove,
              icon: const Icon(Icons.check_circle_outline),
              label: const Text('Approve Replacement Video'),
            ),
            const SizedBox(height: 8),
          ],
          if (showReturnAction)
            OutlinedButton.icon(
              onPressed: isProcessing ? null : onReturn,
              icon: const Icon(Icons.undo),
              label: const Text('Return Video to Partner'),
            ),
        ],
      ),
    );
  }
}

class _StaffVideoPreview extends StatelessWidget {
  const _StaffVideoPreview({required this.video});

  final Map<String, dynamic> video;

  @override
  Widget build(BuildContext context) {
    final title = video['title']?.toString().trim() ?? '';
    final videoUrl = video['video_url']?.toString().trim() ?? '';
    final thumbnailUrl = video['thumbnail_url']?.toString().trim() ?? '';
    final reviewStatus = video['review_status']?.toString() ?? '';
    final rejectionReason = video['rejection_reason']?.toString().trim() ?? '';
    final duration = _int(video['duration']);
    final width = _int(video['width']);
    final height = _int(video['height']);
    final fileSize = _int(video['file_size']);

    final statusColor = switch (reviewStatus) {
      'approved' => const Color(0xFF166534),
      'rejected' => const Color(0xFFB91C1C),
      _ => const Color(0xFF9A3412),
    };

    final statusBackground = switch (reviewStatus) {
      'approved' => const Color(0xFFF0FDF4),
      'rejected' => const Color(0xFFFEF2F2),
      _ => const Color(0xFFFFF7ED),
    };

    return Container(
      decoration: BoxDecoration(
        border: Border.all(color: const Color(0xFFE5E7EB)),
        borderRadius: BorderRadius.circular(12),
      ),
      clipBehavior: Clip.antiAlias,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          AspectRatio(
            aspectRatio: 16 / 9,
            child: Material(
              color: Colors.black87,
              child: InkWell(
                onTap: videoUrl.isEmpty
                    ? null
                    : () {
                        Navigator.of(context).push(
                          MaterialPageRoute<void>(
                            builder: (_) => PropertyVideoScreen(
                              videoUrl: videoUrl,
                              title: title.isEmpty
                                  ? 'Walkthrough Review'
                                  : title,
                            ),
                          ),
                        );
                      },
                child: Stack(
                  fit: StackFit.expand,
                  children: [
                    if (thumbnailUrl.isNotEmpty)
                      Image.network(
                        thumbnailUrl,
                        fit: BoxFit.cover,
                        errorBuilder: (_, _, _) {
                          return const ColoredBox(color: Colors.black87);
                        },
                      ),
                    const ColoredBox(color: Color(0x22000000)),
                    Center(
                      child: CircleAvatar(
                        radius: 30,
                        backgroundColor: Colors.black54,
                        child: Icon(
                          videoUrl.isEmpty
                              ? Icons.videocam_off_outlined
                              : Icons.play_arrow_rounded,
                          color: Colors.white,
                          size: 42,
                        ),
                      ),
                    ),
                    const Positioned(
                      left: 12,
                      bottom: 10,
                      child: Text(
                        'Tap to preview',
                        style: TextStyle(
                          color: Colors.white,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(12),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        title.isEmpty ? 'Property walkthrough' : title,
                        style: const TextStyle(fontWeight: FontWeight.w700),
                      ),
                    ),
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 9,
                        vertical: 5,
                      ),
                      decoration: BoxDecoration(
                        color: statusBackground,
                        borderRadius: BorderRadius.circular(999),
                      ),
                      child: Text(
                        _pretty(reviewStatus),
                        style: TextStyle(
                          color: statusColor,
                          fontSize: 12,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 12,
                  runSpacing: 6,
                  children: [
                    if (duration > 0)
                      _VideoFact(
                        icon: Icons.timer_outlined,
                        label: _formatDuration(duration),
                      ),
                    if (width > 0 && height > 0)
                      _VideoFact(
                        icon: Icons.high_quality_outlined,
                        label: '$width × $height',
                      ),
                    if (fileSize > 0)
                      _VideoFact(
                        icon: Icons.storage_outlined,
                        label: _formatFileSize(fileSize),
                      ),
                  ],
                ),
                if (rejectionReason.isNotEmpty) ...[
                  const SizedBox(height: 8),
                  Text(
                    'Return reason: $rejectionReason',
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

class _VideoFact extends StatelessWidget {
  const _VideoFact({required this.icon, required this.label});

  final IconData icon;
  final String label;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: 16, color: Colors.black54),
        const SizedBox(width: 4),
        Text(label, style: const TextStyle(color: Colors.black54)),
      ],
    );
  }
}

class _ReadinessCard extends StatelessWidget {
  const _ReadinessCard({
    required this.publishing,
    required this.commercialReadiness,
    required this.photos,
    required this.blockers,
    required this.readyToPublish,
  });

  final Map<String, dynamic> publishing;
  final Map<String, dynamic> commercialReadiness;
  final Map<String, dynamic> photos;
  final List<dynamic> blockers;
  final bool readyToPublish;

  @override
  Widget build(BuildContext context) {
    final score = _int(publishing['readiness_score']);

    final photoCount = _int(photos['count']);

    final requiredPhotos = _int(photos['required_for_publication']);

    final commercialAllowed = _bool(commercialReadiness['allowed']);

    return _SectionCard(
      title: 'Publication Readiness',
      icon: Icons.fact_check_outlined,
      child: Column(
        children: [
          _CheckLine(
            label: 'Property readiness $score%',
            complete: score == 100,
          ),
          _CheckLine(
            label: 'Photos $photoCount / $requiredPhotos',
            complete: photoCount >= requiredPhotos && requiredPhotos > 0,
          ),
          _CheckLine(
            label: 'Commercial authorization',
            complete: commercialAllowed,
          ),
          _CheckLine(label: 'Ready to publish', complete: readyToPublish),
          if (blockers.isNotEmpty) ...[
            const SizedBox(height: 12),
            _BlockersPanel(blockers: blockers),
          ],
        ],
      ),
    );
  }
}

class _CommissionCard extends StatelessWidget {
  const _CommissionCard({required this.commission});

  final Map<String, dynamic> commission;

  @override
  Widget build(BuildContext context) {
    if (commission.isEmpty) {
      return const _SectionCard(
        title: 'Commission Agreement',
        icon: Icons.handshake_outlined,
        child: _EmptyPanel(
          text: 'No commission agreement exists for this property.',
        ),
      );
    }

    final method = commission['commission_method_display']?.toString() ?? '';

    final basis = commission['commission_basis_display']?.toString() ?? '';

    final total = _double(commission['expected_total_commission']);

    final rate = commission['commission_rate']?.toString();

    final fixed = _doubleNullable(commission['fixed_commission_amount']);

    return _SectionCard(
      title: 'Commission Agreement',
      icon: Icons.handshake_outlined,
      child: Column(
        children: [
          _InfoLine(label: 'Method', value: method),
          _InfoLine(label: 'Basis', value: basis),
          if (rate != null && rate.trim().isNotEmpty)
            _InfoLine(label: 'Rate', value: '$rate%'),
          if (fixed != null)
            _InfoLine(label: 'Fixed commission', value: _formatKes(fixed)),
          _InfoLine(label: 'Expected commission', value: _formatKes(total)),
          const Divider(height: 24),
          _CheckLine(
            label: 'Partner accepted',
            complete: _bool(commission['partner_accepted']),
          ),
          _CheckLine(
            label: 'Pata Hao verified',
            complete: _bool(commission['is_verified']),
          ),
          _CheckLine(
            label: 'Commission locked',
            complete: _bool(commission['is_locked']),
          ),
        ],
      ),
    );
  }
}

class _MandateCard extends StatelessWidget {
  const _MandateCard({required this.mandate});

  final Map<String, dynamic> mandate;

  @override
  Widget build(BuildContext context) {
    if (mandate.isEmpty) {
      return const _SectionCard(
        title: 'Digital Mandate',
        icon: Icons.assignment_turned_in_outlined,
        child: _EmptyPanel(
          text: 'No digital mandate exists for this property.',
        ),
      );
    }

    final owner = _map(mandate['owner']);

    final authorizationMethod =
        mandate['authorization_method_display']?.toString() ?? '';

    final notes = mandate['authorization_notes']?.toString().trim() ?? '';

    return _SectionCard(
      title: 'Digital Mandate',
      icon: Icons.assignment_turned_in_outlined,
      child: Column(
        children: [
          _InfoLine(
            label: 'Owner',
            value: owner['legal_name']?.toString() ?? '',
          ),
          _InfoLine(
            label: 'Owner phone',
            value: owner['phone_number']?.toString() ?? '',
          ),
          _InfoLine(label: 'Authorization', value: authorizationMethod),
          if (notes.isNotEmpty) _InfoLine(label: 'Notes', value: notes),
          const Divider(height: 24),
          _CheckLine(
            label: 'Authority confirmed',
            complete: _bool(mandate['owner_authority_confirmed']),
          ),
          _CheckLine(
            label: 'Recorded transaction policy acknowledged',
            complete: _bool(mandate['no_cash_acknowledged']),
          ),
          _CheckLine(
            label: 'Anti-circumvention acknowledged',
            complete: _bool(mandate['anti_circumvention_acknowledged']),
          ),
          _CheckLine(
            label: 'Partner declared mandate',
            complete: _bool(mandate['partner_declared']),
          ),
          _CheckLine(
            label: 'Pata Hao approved mandate',
            complete: mandate['status']?.toString() == 'approved',
          ),
        ],
      ),
    );
  }
}

class _ActionCard extends StatelessWidget {
  const _ActionCard({
    required this.isProcessing,
    required this.commissionExists,
    required this.commissionAccepted,
    required this.commissionVerified,
    required this.commissionLocked,
    required this.mandateExists,
    required this.mandateDeclared,
    required this.mandateApproved,
    required this.readyToPublish,
    required this.hasPendingVideo,
    required this.canVerifyCommission,
    required this.canLockCommission,
    required this.canApproveMandate,
    required this.onVerifyCommission,
    required this.onLockCommission,
    required this.onApproveMandate,
    required this.onPublish,
    required this.onReturnToPartner,
  });

  final bool isProcessing;
  final bool commissionExists;
  final bool commissionAccepted;
  final bool commissionVerified;
  final bool commissionLocked;
  final bool mandateExists;
  final bool mandateDeclared;
  final bool mandateApproved;
  final bool readyToPublish;
  final bool hasPendingVideo;
  final bool canVerifyCommission;
  final bool canLockCommission;
  final bool canApproveMandate;

  final Future<void> Function() onVerifyCommission;
  final Future<void> Function() onLockCommission;
  final Future<void> Function() onApproveMandate;
  final Future<void> Function() onPublish;
  final Future<void> Function() onReturnToPartner;

  @override
  Widget build(BuildContext context) {
    return _SectionCard(
      title: 'Pata Hao Actions',
      icon: Icons.admin_panel_settings_outlined,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _ActionStep(
            number: 1,
            title: 'Verify Commission',
            complete: commissionVerified,
            enabled: canVerifyCommission && !isProcessing,
            unavailableReason: !commissionExists
                ? 'Commission agreement is missing.'
                : !commissionAccepted
                ? 'Partner must accept the commission first.'
                : null,
            onPressed: onVerifyCommission,
          ),
          const SizedBox(height: 10),
          _ActionStep(
            number: 2,
            title: 'Lock Commission',
            complete: commissionLocked,
            enabled: canLockCommission && !isProcessing,
            unavailableReason: !commissionVerified
                ? 'Verify the commission first.'
                : null,
            onPressed: onLockCommission,
          ),
          const SizedBox(height: 10),
          _ActionStep(
            number: 3,
            title: 'Approve Mandate',
            complete: mandateApproved,
            enabled: canApproveMandate && !isProcessing,
            unavailableReason: !mandateExists
                ? 'Digital mandate is missing.'
                : !mandateDeclared
                ? 'Partner has not accepted the mandate.'
                : !commissionLocked
                ? 'Lock the commission before approving the mandate.'
                : null,
            onPressed: onApproveMandate,
          ),
          const SizedBox(height: 10),
          _ActionStep(
            number: 4,
            title: hasPendingVideo
                ? 'Approve & Publish Property + Video'
                : 'Publish Property',
            complete: false,
            enabled: readyToPublish && !isProcessing,
            unavailableReason: !readyToPublish
                ? 'Resolve all publication blockers first.'
                : null,
            onPressed: onPublish,
            primary: true,
          ),
          const SizedBox(height: 18),
          OutlinedButton.icon(
            onPressed: isProcessing ? null : onReturnToPartner,
            icon: const Icon(Icons.undo),
            label: const Text('Return to Partner'),
          ),
        ],
      ),
    );
  }
}

class _ActionStep extends StatelessWidget {
  const _ActionStep({
    required this.number,
    required this.title,
    required this.complete,
    required this.enabled,
    required this.onPressed,
    this.unavailableReason,
    this.primary = false,
  });

  final int number;
  final String title;
  final bool complete;
  final bool enabled;
  final Future<void> Function() onPressed;
  final String? unavailableReason;
  final bool primary;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        border: Border.all(
          color: complete ? const Color(0xFFBBF7D0) : const Color(0xFFE5E7EB),
        ),
        borderRadius: BorderRadius.circular(12),
        color: complete ? const Color(0xFFF0FDF4) : Colors.white,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 30,
                height: 30,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: complete
                      ? const Color(0xFF15803D)
                      : const Color(0xFFE5E7EB),
                ),
                alignment: Alignment.center,
                child: complete
                    ? const Icon(Icons.check, size: 18, color: Colors.white)
                    : Text(
                        '$number',
                        style: const TextStyle(fontWeight: FontWeight.w700),
                      ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  title,
                  style: const TextStyle(fontWeight: FontWeight.w700),
                ),
              ),
            ],
          ),
          if (unavailableReason != null && !complete) ...[
            const SizedBox(height: 8),
            Text(
              unavailableReason!,
              style: const TextStyle(color: Colors.black54, fontSize: 13),
            ),
          ],
          if (!complete) ...[
            const SizedBox(height: 10),
            SizedBox(
              width: double.infinity,
              child: primary
                  ? FilledButton(
                      onPressed: enabled ? onPressed : null,
                      child: Text(title),
                    )
                  : OutlinedButton(
                      onPressed: enabled ? onPressed : null,
                      child: Text(title),
                    ),
            ),
          ],
        ],
      ),
    );
  }
}

class _SectionCard extends StatelessWidget {
  const _SectionCard({
    required this.title,
    required this.icon,
    required this.child,
  });

  final String title;
  final IconData icon;
  final Widget child;

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
                Icon(icon),
                const SizedBox(width: 8),
                Text(
                  title,
                  style: const TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 14),
            child,
          ],
        ),
      ),
    );
  }
}

class _InfoLine extends StatelessWidget {
  const _InfoLine({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            child: Text(label, style: const TextStyle(color: Colors.black54)),
          ),
          const SizedBox(width: 14),
          Flexible(
            child: Text(
              value,
              textAlign: TextAlign.end,
              style: const TextStyle(fontWeight: FontWeight.w600),
            ),
          ),
        ],
      ),
    );
  }
}

class _CheckLine extends StatelessWidget {
  const _CheckLine({required this.label, required this.complete});

  final String label;
  final bool complete;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Row(
        children: [
          Icon(
            complete ? Icons.check_circle : Icons.radio_button_unchecked,
            size: 20,
            color: complete ? const Color(0xFF15803D) : Colors.black38,
          ),
          const SizedBox(width: 8),
          Expanded(child: Text(label)),
        ],
      ),
    );
  }
}

class _BlockersPanel extends StatelessWidget {
  const _BlockersPanel({required this.blockers});

  final List<dynamic> blockers;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFFFFF7ED),
        border: Border.all(color: const Color(0xFFFED7AA)),
        borderRadius: BorderRadius.circular(10),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Blockers',
            style: TextStyle(
              color: Color(0xFF9A3412),
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 6),
          ...blockers.map((blocker) {
            return Padding(
              padding: const EdgeInsets.only(bottom: 3),
              child: Text(
                '• ${blocker.toString()}',
                style: const TextStyle(color: Color(0xFF7C2D12)),
              ),
            );
          }),
        ],
      ),
    );
  }
}

class _EmptyPanel extends StatelessWidget {
  const _EmptyPanel({required this.text});

  final String text;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: const Color(0xFFFFF7ED),
        borderRadius: BorderRadius.circular(10),
      ),
      child: Text(text),
    );
  }
}

class _InlineError extends StatelessWidget {
  const _InlineError({required this.message});

  final String message;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: const Color(0xFFFEF2F2),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: const Color(0xFFFECACA)),
      ),
      child: Text(message, style: const TextStyle(color: Color(0xFF991B1B))),
    );
  }
}

class _InlineGuidance extends StatelessWidget {
  const _InlineGuidance({required this.message});

  final String message;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: const Color(0xFFEFF6FF),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: const Color(0xFFBFDBFE)),
      ),
      child: Text(
        message,
        style: const TextStyle(color: Color(0xFF1E3A8A), height: 1.4),
      ),
    );
  }
}

class _ErrorPanel extends StatelessWidget {
  const _ErrorPanel({required this.message, required this.onRetry});

  final String message;
  final Future<void> Function() onRetry;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          children: [
            const Icon(Icons.error_outline, size: 48, color: Color(0xFFB91C1C)),
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

Map<String, dynamic> _map(dynamic value) {
  if (value is Map) {
    return Map<String, dynamic>.from(value);
  }

  return <String, dynamic>{};
}

List<Map<String, dynamic>> _mapList(dynamic value) {
  if (value is! List) {
    return <Map<String, dynamic>>[];
  }

  return value
      .whereType<Map>()
      .map((item) => Map<String, dynamic>.from(item))
      .toList();
}

Map<String, dynamic>? _pendingVideo(dynamic value) {
  for (final video in _mapList(value)) {
    if (video['review_status']?.toString() == 'pending') {
      return video;
    }
  }

  return null;
}

List<dynamic> _list(dynamic value) {
  if (value is List) {
    return value;
  }

  return <dynamic>[];
}

int _int(dynamic value) {
  if (value is int) {
    return value;
  }

  if (value is num) {
    return value.toInt();
  }

  return int.tryParse(value?.toString() ?? '') ?? 0;
}

double _double(dynamic value) {
  if (value is num) {
    return value.toDouble();
  }

  return double.tryParse(value?.toString() ?? '') ?? 0;
}

double? _doubleNullable(dynamic value) {
  if (value == null) {
    return null;
  }

  if (value is num) {
    return value.toDouble();
  }

  return double.tryParse(value.toString());
}

bool _bool(dynamic value) {
  if (value is bool) {
    return value;
  }

  final normalized = value?.toString().trim().toLowerCase();

  return normalized == 'true' || normalized == '1' || normalized == 'yes';
}

String _formatKes(num value) {
  final whole = value.round().toString();

  final formatted = whole.replaceAllMapped(
    RegExp(r'\B(?=(\d{3})+(?!\d))'),
    (match) => ',',
  );

  return 'KES $formatted';
}

String _formatDuration(int seconds) {
  final minutes = seconds ~/ 60;
  final remainingSeconds = seconds % 60;

  return '$minutes:${remainingSeconds.toString().padLeft(2, '0')}';
}

String _formatFileSize(int bytes) {
  final megabytes = bytes / (1024 * 1024);
  return '${megabytes.toStringAsFixed(1)} MB';
}

String _pretty(String value) {
  final words = value
      .trim()
      .replaceAll('_', ' ')
      .split(' ')
      .where((word) => word.isNotEmpty)
      .map(
        (word) =>
            '${word[0].toUpperCase()}'
            '${word.substring(1).toLowerCase()}',
      );

  return words.join(' ');
}
