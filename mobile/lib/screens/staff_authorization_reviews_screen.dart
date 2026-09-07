import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';

import 'package:mobile/models/staff_authorization_review.dart';
import 'package:mobile/services/staff_authorization_review_service.dart';

class StaffAuthorizationReviewsScreen extends StatefulWidget {
  const StaffAuthorizationReviewsScreen({super.key});

  @override
  State<StaffAuthorizationReviewsScreen> createState() {
    return _StaffAuthorizationReviewsScreenState();
  }
}

class _StaffAuthorizationReviewsScreenState
    extends State<StaffAuthorizationReviewsScreen> {
  bool _isLoading = true;
  int? _openingReviewId;
  String? _errorMessage;
  List<StaffAuthorizationReview> _reviews = const [];

  @override
  void initState() {
    super.initState();
    _loadReviews();
  }

  Future<void> _loadReviews() async {
    if (!mounted) {
      return;
    }

    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final reviews = await StaffAuthorizationReviewService.instance
          .fetchPendingReviews();

      if (!mounted) {
        return;
      }

      setState(() {
        _reviews = reviews;
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

  Future<void> _openReview(
    StaffAuthorizationReview review,
  ) async {
    if (_openingReviewId != null) {
      return;
    }

    setState(() {
      _openingReviewId = review.id;
    });

    try {
      final salePack = await StaffAuthorizationReviewService.instance
          .fetchSalePack(review.id);

      if (!mounted) {
        return;
      }

      final reviewedDocumentIds = await showDialog<List<int>>(
        context: context,
        builder: (dialogContext) {
          return _AuthorizationReviewDialog(
            review: review,
            salePack: salePack,
          );
        },
      );

      if (reviewedDocumentIds == null || !mounted) {
        return;
      }

      await StaffAuthorizationReviewService.instance.completeReview(
        review.id,
        reviewedDocumentIds: reviewedDocumentIds,
      );

      if (!mounted) {
        return;
      }

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            '${review.propertyTitle} authorization approved.',
          ),
          backgroundColor: const Color(0xFF14532D),
        ),
      );

      await _loadReviews();
    } catch (error) {
      if (!mounted) {
        return;
      }

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(_cleanError(error)),
          backgroundColor: const Color(0xFFB91C1C),
        ),
      );
    } finally {
      if (mounted) {
        setState(() {
          _openingReviewId = null;
        });
      }
    }
  }

  String _cleanError(Object error) {
    return error
        .toString()
        .replaceFirst(RegExp(r'^Exception:\s*'), '')
        .replaceFirst(RegExp(r'^FormatException:\s*'), '')
        .trim();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF6F8F6),
      appBar: AppBar(
        title: const Text('Authorization Reviews'),
        backgroundColor: const Color(0xFF14532D),
        foregroundColor: Colors.white,
      ),
      body: RefreshIndicator(
        onRefresh: _loadReviews,
        child: _buildBody(),
      ),
    );
  }

  Widget _buildBody() {
    if (_isLoading && _reviews.isEmpty) {
      return const Center(
        child: CircularProgressIndicator(),
      );
    }

    if (_errorMessage != null && _reviews.isEmpty) {
      return ListView(
        padding: const EdgeInsets.all(24),
        children: [
          const SizedBox(height: 80),
          const Icon(
            Icons.error_outline,
            size: 52,
            color: Color(0xFFB91C1C),
          ),
          const SizedBox(height: 16),
          Text(
            _errorMessage!,
            textAlign: TextAlign.center,
            style: const TextStyle(
              color: Color(0xFF7F1D1D),
            ),
          ),
          const SizedBox(height: 18),
          Center(
            child: FilledButton.icon(
              onPressed: _loadReviews,
              icon: const Icon(Icons.refresh),
              label: const Text('Try Again'),
            ),
          ),
        ],
      );
    }

    if (_reviews.isEmpty) {
      return ListView(
        padding: const EdgeInsets.all(24),
        children: const [
          SizedBox(height: 80),
          Icon(
            Icons.verified_user_outlined,
            size: 58,
            color: Color(0xFF14532D),
          ),
          SizedBox(height: 16),
          Text(
            'No authorizations are waiting.',
            textAlign: TextAlign.center,
            style: TextStyle(
              fontSize: 19,
              fontWeight: FontWeight.w700,
            ),
          ),
          SizedBox(height: 8),
          Text(
            'New partner submissions will appear here automatically.',
            textAlign: TextAlign.center,
            style: TextStyle(
              color: Color(0xFF4B5563),
              height: 1.4,
            ),
          ),
        ],
      );
    }

    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 28),
      children: [
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: const Color(0xFFFFFBEB),
            borderRadius: BorderRadius.circular(16),
            border: Border.all(
              color: const Color(0xFFFDE68A),
            ),
          ),
          child: Row(
            children: [
              const Icon(
                Icons.assignment_late_outlined,
                color: Color(0xFF92400E),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Text(
                  _reviews.length == 1
                      ? '1 authorization needs review'
                      : '${_reviews.length} authorizations need review',
                  style: const TextStyle(
                    fontWeight: FontWeight.w700,
                    color: Color(0xFF78350F),
                  ),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 14),
        ..._reviews.map(_buildReviewCard),
      ],
    );
  }

  Widget _buildReviewCard(
    StaffAuthorizationReview review,
  ) {
    final isOpening = _openingReviewId == review.id;

    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const CircleAvatar(
                  backgroundColor: Color(0xFFFFF7ED),
                  child: Icon(
                    Icons.description_outlined,
                    color: Color(0xFFC2410C),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        review.propertyTitle,
                        style: const TextStyle(
                          fontSize: 17,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      const SizedBox(height: 3),
                      Text(
                        review.partnerName,
                        style: const TextStyle(
                          color: Color(0xFF4B5563),
                        ),
                      ),
                    ],
                  ),
                ),
                const _WaitingBadge(),
              ],
            ),
            const SizedBox(height: 14),
            _ReviewLine(
              label: 'Owner',
              value: review.ownerName.isEmpty
                  ? 'Not provided'
                  : review.ownerName,
            ),
            _ReviewLine(
              label: 'Submitted',
              value: _formatDate(review.submittedAt),
            ),
            _ReviewLine(
              label: 'Mandate',
              value: review.mandateNumber,
            ),
            const SizedBox(height: 14),
            SizedBox(
              width: double.infinity,
              child: FilledButton.icon(
                onPressed: isOpening
                    ? null
                    : () {
                        _openReview(review);
                      },
                icon: isOpening
                    ? const SizedBox(
                        width: 18,
                        height: 18,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                        ),
                      )
                    : const Icon(Icons.fact_check_outlined),
                label: Text(
                  isOpening
                      ? 'Opening...'
                      : 'Review Authorization',
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  String _formatDate(DateTime? dateTime) {
    if (dateTime == null) {
      return 'Recently';
    }

    final local = dateTime.toLocal();
    final day = local.day.toString().padLeft(2, '0');
    final month = local.month.toString().padLeft(2, '0');
    final year = local.year.toString();
    final hour = local.hour.toString().padLeft(2, '0');
    final minute = local.minute.toString().padLeft(2, '0');

    return '$day/$month/$year $hour:$minute';
  }
}

class _AuthorizationReviewDialog extends StatefulWidget {
  const _AuthorizationReviewDialog({
    required this.review,
    required this.salePack,
  });

  final StaffAuthorizationReview review;
  final Map<String, dynamic> salePack;

  @override
  State<_AuthorizationReviewDialog> createState() {
    return _AuthorizationReviewDialogState();
  }
}

class _AuthorizationReviewDialogState
    extends State<_AuthorizationReviewDialog> {
  bool _confirmed = false;
  int? _openingEvidenceId;
  final Set<int> _openedEvidenceIds = <int>{};

  List<StaffAuthorizationEvidence> get _evidence {
    final rawSteps = widget.salePack['steps'];

    if (rawSteps is! List) {
      return const [];
    }

    return rawSteps
        .whereType<Map>()
        .map(
          (step) => StaffAuthorizationEvidence.fromStep(
            Map<String, dynamic>.from(step),
          ),
        )
        .toList(growable: false);
  }

  bool get _salePackRequired =>
      widget.salePack['sale_pack_required'] == true;

  bool get _hasMissingEvidence =>
      _salePackRequired &&
      (
        _evidence.isEmpty ||
        _evidence.any(
          (item) => !item.isProvided,
        )
      );

  bool get _allEvidenceOpened =>
      !_salePackRequired ||
      (
        _evidence.isNotEmpty &&
        _evidence
            .where((item) => item.isProvided)
            .every((item) => _openedEvidenceIds.contains(item.id))
      );

  Future<void> _openEvidence(
    StaffAuthorizationEvidence evidence,
  ) async {
    if (!evidence.isProvided || _openingEvidenceId != null) {
      return;
    }

    setState(() {
      _openingEvidenceId = evidence.id;
    });

    try {
      final evidenceFile = await StaffAuthorizationReviewService.instance
          .fetchEvidence(
            widget.review.id,
            evidence.id,
            filename: evidence.filename,
          );

      if (!mounted) {
        return;
      }

      var opened = false;

      if (evidenceFile.isImage) {
        await precacheImage(
          MemoryImage(evidenceFile.bytes),
          context,
        );

        if (!mounted) {
          return;
        }

        await showDialog<void>(
          context: context,
          builder: (imageContext) {
            return Dialog(
              child: ConstrainedBox(
                constraints: const BoxConstraints(
                  maxWidth: 900,
                  maxHeight: 760,
                ),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    ListTile(
                      title: Text(evidence.label),
                      subtitle: Text(evidence.filename),
                      trailing: IconButton(
                        tooltip: 'Close',
                        onPressed: () {
                          Navigator.of(imageContext).pop();
                        },
                        icon: const Icon(Icons.close),
                      ),
                    ),
                    const Divider(height: 1),
                    Flexible(
                      child: InteractiveViewer(
                        minScale: 0.5,
                        maxScale: 5,
                        child: Image.memory(
                          evidenceFile.bytes,
                          fit: BoxFit.contain,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            );
          },
        );
        opened = true;
      } else {
        final savedPath = await FilePicker.platform.saveFile(
          dialogTitle: 'Save evidence for inspection',
          fileName: evidence.filename,
          bytes: evidenceFile.bytes,
        );
        opened = savedPath != null;

        if (opened && mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text(
                'Evidence saved. Open it with your PDF viewer, '
                'then return to complete the review.',
              ),
            ),
          );
        }
      }

      if (opened && mounted) {
        setState(() {
          _openedEvidenceIds.add(evidence.id);
        });
      }
    } catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              error
                  .toString()
                  .replaceFirst(RegExp(r'^Exception:\s*'), '')
                  .replaceFirst(RegExp(r'^FormatException:\s*'), '')
                  .trim(),
            ),
            backgroundColor: const Color(0xFFB91C1C),
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() {
          _openingEvidenceId = null;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final review = widget.review;
    final evidence = _evidence;
    final canApprove =
        _confirmed && !_hasMissingEvidence && _allEvidenceOpened;

    return AlertDialog(
      title: Text(review.propertyTitle),
      content: SizedBox(
        width: double.maxFinite,
        child: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              const Text(
                'Authorization review',
                style: TextStyle(
                  fontWeight: FontWeight.w700,
                  color: Color(0xFF14532D),
                ),
              ),
              const SizedBox(height: 12),
              _ReviewLine(
                label: 'Partner',
                value: review.partnerName,
              ),
              _ReviewLine(
                label: 'Owner',
                value: review.ownerName,
              ),
              _ReviewLine(
                label: 'Owner phone',
                value: review.ownerPhone,
              ),
              _ReviewLine(
                label: 'Authority',
                value: review.authorizationMethodDisplay,
              ),
              _ReviewLine(
                label: 'Agreement',
                value: review.agreementNumber,
              ),
              _ReviewLine(
                label: 'Commission',
                value: _commissionLabel(review),
              ),
              const Divider(height: 28),
              Text(
                _salePackRequired
                    ? 'Current sale evidence'
                    : 'Evidence',
                style: const TextStyle(
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(height: 8),
              if (!_salePackRequired)
                const Text(
                  'No Sale Mandate Pack is required for this listing.',
                  style: TextStyle(
                    color: Color(0xFF4B5563),
                  ),
                )
              else
                ...evidence.map(
                  (item) => _EvidenceRow(
                    evidence: item,
                    wasOpened: _openedEvidenceIds.contains(item.id),
                    isOpening: _openingEvidenceId == item.id,
                    onOpen: item.isProvided
                        ? () {
                            _openEvidence(item);
                          }
                        : null,
                  ),
                ),
              if (_hasMissingEvidence) ...[
                const SizedBox(height: 10),
                const Text(
                  'Required sale evidence is missing. Return to the '
                  'partner before approval.',
                  style: TextStyle(
                    color: Color(0xFFB91C1C),
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
              if (!_hasMissingEvidence && !_allEvidenceOpened) ...[
                const SizedBox(height: 10),
                const Text(
                  'Open every current evidence file before confirming '
                  'this authorization.',
                  style: TextStyle(
                    color: Color(0xFF92400E),
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
              const Divider(height: 28),
              CheckboxListTile(
                value: _confirmed,
                contentPadding: EdgeInsets.zero,
                controlAffinity:
                    ListTileControlAffinity.leading,
                title: const Text(
                  'I opened and inspected the owner authority, '
                  'commission terms, and every current evidence file.',
                  style: TextStyle(fontSize: 14),
                ),
                onChanged: _hasMissingEvidence || !_allEvidenceOpened
                    ? null
                    : (value) {
                        setState(() {
                          _confirmed = value == true;
                        });
                      },
              ),
              const Text(
                'Approval verifies the owner, locks the accepted '
                'commission terms, approves the current evidence, and '
                'records the decision in the audit trail.',
                style: TextStyle(
                  fontSize: 12,
                  color: Color(0xFF6B7280),
                  height: 1.35,
                ),
              ),
            ],
          ),
        ),
      ),
      actions: [
        TextButton(
          onPressed: () {
            Navigator.of(context).pop();
          },
          child: const Text('Cancel'),
        ),
        FilledButton(
          onPressed: canApprove
              ? () {
                  final documentIds = _openedEvidenceIds.toList()
                    ..sort();
                  Navigator.of(context).pop(documentIds);
                }
              : null,
          child: const Text('Approve Authorization'),
        ),
      ],
    );
  }

  String _commissionLabel(
    StaffAuthorizationReview review,
  ) {
    final amount = review.expectedCommission;

    if (amount.isNotEmpty) {
      return '${review.currency} $amount';
    }

    if (review.commissionMethod.isNotEmpty) {
      return review.commissionMethod;
    }

    return 'Accepted terms';
  }
}

class _EvidenceRow extends StatelessWidget {
  const _EvidenceRow({
    required this.evidence,
    required this.wasOpened,
    required this.isOpening,
    required this.onOpen,
  });

  final StaffAuthorizationEvidence evidence;
  final bool wasOpened;
  final bool isOpening;
  final VoidCallback? onOpen;

  @override
  Widget build(BuildContext context) {
    final metadata = [
      evidence.status,
      if (evidence.fileSizeLabel.isNotEmpty)
        evidence.fileSizeLabel,
      if (evidence.shortHash.isNotEmpty)
        'Hash ${evidence.shortHash}',
    ].join(' • ');

    return Container(
      width: double.infinity,
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(11),
      decoration: BoxDecoration(
        color: const Color(0xFFF9FAFB),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(
          color: const Color(0xFFE5E7EB),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            evidence.label,
            style: const TextStyle(
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 3),
          Text(
            evidence.filename,
            style: const TextStyle(
              fontSize: 13,
            ),
          ),
          if (metadata.isNotEmpty) ...[
            const SizedBox(height: 3),
            Text(
              metadata,
              style: const TextStyle(
                fontSize: 11,
                color: Color(0xFF6B7280),
              ),
            ),
          ],
          const SizedBox(height: 8),
          OutlinedButton.icon(
            onPressed: isOpening ? null : onOpen,
            icon: isOpening
                ? const SizedBox(
                    width: 16,
                    height: 16,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                    ),
                  )
                : Icon(
                    wasOpened
                        ? Icons.check_circle_outline
                        : Icons.open_in_new,
                  ),
            label: Text(
              isOpening
                  ? 'Opening...'
                  : (wasOpened ? 'Opened' : 'View Evidence'),
            ),
          ),
        ],
      ),
    );
  }
}

class _ReviewLine extends StatelessWidget {
  const _ReviewLine({
    required this.label,
    required this.value,
  });

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 7),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 92,
            child: Text(
              label,
              style: const TextStyle(
                color: Color(0xFF6B7280),
              ),
            ),
          ),
          Expanded(
            child: Text(
              value.trim().isEmpty ? 'Not provided' : value,
              style: const TextStyle(
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _WaitingBadge extends StatelessWidget {
  const _WaitingBadge();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: 8,
        vertical: 5,
      ),
      decoration: BoxDecoration(
        color: const Color(0xFFFFF7ED),
        borderRadius: BorderRadius.circular(999),
      ),
      child: const Text(
        'Waiting',
        style: TextStyle(
          fontSize: 11,
          fontWeight: FontWeight.w700,
          color: Color(0xFF9A3412),
        ),
      ),
    );
  }
}
