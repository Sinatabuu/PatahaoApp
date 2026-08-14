import 'package:flutter/material.dart';

import 'package:mobile/screens/staff_property_review_detail_screen.dart';
import 'package:mobile/services/staff_property_review_service.dart';

class StaffPropertyReviewQueueScreen extends StatefulWidget {
  const StaffPropertyReviewQueueScreen({super.key, this.onLogout});

  final Future<void> Function()? onLogout;

  @override
  State<StaffPropertyReviewQueueScreen> createState() {
    return _StaffPropertyReviewQueueScreenState();
  }
}

class _StaffPropertyReviewQueueScreenState
    extends State<StaffPropertyReviewQueueScreen> {
  bool _isLoading = true;
  String? _errorMessage;

  List<Map<String, dynamic>> _reviews = <Map<String, dynamic>>[];

  @override
  void initState() {
    super.initState();
    _loadQueue();
  }

  Future<void> _loadQueue() async {
    if (!mounted) {
      return;
    }

    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final reviews = await StaffPropertyReviewService.instance
          .fetchReviewQueue();

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

  Future<void> _openReview(Map<String, dynamic> review) async {
    final property = _map(review['property']);

    final propertyId = _int(property['id']);

    if (propertyId <= 0) {
      return;
    }

    final changed = await Navigator.of(context).push<bool>(
      MaterialPageRoute<bool>(
        builder: (_) {
          return StaffPropertyReviewDetailScreen(propertyId: propertyId);
        },
      ),
    );

    if (!mounted) {
      return;
    }

    if (changed == true) {
      await _loadQueue();
    }
  }

  Future<void> _logout() async {
    final onLogout = widget.onLogout;

    if (onLogout == null) {
      return;
    }

    await onLogout();
  }

  String _cleanError(Object error) {
    return error.toString().replaceFirst(RegExp(r'^Exception:\s*'), '').trim();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF6F8F6),
      appBar: AppBar(
        title: const Text('Pata Hao Review Desk'),
        backgroundColor: const Color(0xFF14532D),
        foregroundColor: Colors.white,
        actions: [
          if (widget.onLogout != null)
            IconButton(
              tooltip: 'Sign out',
              onPressed: _logout,
              icon: const Icon(Icons.logout),
            ),
        ],
      ),
      body: RefreshIndicator(onRefresh: _loadQueue, child: _buildBody()),
    );
  }

  Widget _buildBody() {
    if (_isLoading) {
      return ListView(
        physics: AlwaysScrollableScrollPhysics(),
        children: [
          SizedBox(height: 180),
          Center(child: CircularProgressIndicator()),
        ],
      );
    }

    if (_errorMessage != null) {
      return ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(16),
        children: [
          const SizedBox(height: 60),
          _ErrorPanel(message: _errorMessage!, onRetry: _loadQueue),
        ],
      );
    }

    if (_reviews.isEmpty) {
      return ListView(
        physics: AlwaysScrollableScrollPhysics(),
        padding: EdgeInsets.all(24),
        children: [
          SizedBox(height: 100),
          Icon(Icons.task_alt, size: 64, color: Color(0xFF15803D)),
          SizedBox(height: 16),
          Text(
            'Review queue is clear',
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 22, fontWeight: FontWeight.w700),
          ),
          SizedBox(height: 8),
          Text(
            'There are no properties currently waiting for Pata Hao review.',
            textAlign: TextAlign.center,
            style: TextStyle(color: Colors.black54, height: 1.4),
          ),
        ],
      );
    }

    return ListView(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
      children: [
        _QueueSummaryCard(reviewCount: _reviews.length),
        const SizedBox(height: 16),
        ..._reviews.map((review) {
          return Padding(
            padding: const EdgeInsets.only(bottom: 14),
            child: _ReviewCard(
              review: review,
              onOpen: () {
                _openReview(review);
              },
            ),
          );
        }),
      ],
    );
  }
}

class _QueueSummaryCard extends StatelessWidget {
  const _QueueSummaryCard({required this.reviewCount});

  final int reviewCount;

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 0,
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Row(
          children: [
            Container(
              width: 52,
              height: 52,
              decoration: BoxDecoration(
                color: const Color(0xFFE8F5E9),
                borderRadius: BorderRadius.circular(14),
              ),
              child: const Icon(
                Icons.fact_check_outlined,
                color: Color(0xFF15803D),
              ),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Pending property reviews',
                    style: TextStyle(fontSize: 17, fontWeight: FontWeight.w700),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    '$reviewCount ${reviewCount == 1 ? 'property' : 'properties'} waiting for review.',
                    style: const TextStyle(color: Colors.black54),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ReviewCard extends StatelessWidget {
  const _ReviewCard({required this.review, required this.onOpen});

  final Map<String, dynamic> review;
  final VoidCallback onOpen;

  @override
  Widget build(BuildContext context) {
    final property = _map(review['property']);

    final partner = _map(review['partner']);

    final photos = _map(review['photos']);

    final publishing = _map(review['publishing']);

    final commission = _map(review['commission']);

    final mandate = _map(review['mandate']);

    final blockers = _list(review['blockers']);

    final readyToPublish = _bool(review['ready_to_publish']);

    final title = property['title']?.toString().trim() ?? '';

    final town = property['town']?.toString().trim() ?? '';

    final county = property['county']?.toString().trim() ?? '';

    final partnerName = partner['display_name']?.toString().trim() ?? '';

    final readinessScore = _int(publishing['readiness_score']);

    final photoCount = _int(photos['count']);

    final requiredPhotos = _int(photos['required_for_publication']);

    final commissionAccepted = _bool(commission['partner_accepted']);

    final commissionVerified = _bool(commission['is_verified']);

    final commissionLocked = _bool(commission['is_locked']);

    final mandateDeclared = _bool(mandate['partner_declared']);

    final mandateApproved = mandate['status']?.toString() == 'approved';

    return Card(
      elevation: 0,
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: onOpen,
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          title.isEmpty ? 'Untitled property' : title,
                          style: const TextStyle(
                            fontSize: 18,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          [
                            if (town.isNotEmpty) town,
                            if (county.isNotEmpty) county,
                          ].join(', '),
                          style: const TextStyle(color: Colors.black54),
                        ),
                      ],
                    ),
                  ),
                  _ReadyChip(ready: readyToPublish),
                ],
              ),

              const SizedBox(height: 14),

              _InfoLine(
                icon: Icons.person_outline,
                label: 'Partner',
                value: partnerName.isEmpty ? 'Unknown partner' : partnerName,
              ),

              const SizedBox(height: 10),

              _InfoLine(
                icon: Icons.analytics_outlined,
                label: 'Property readiness',
                value: '$readinessScore%',
              ),

              const SizedBox(height: 10),

              _InfoLine(
                icon: Icons.photo_library_outlined,
                label: 'Photos',
                value: '$photoCount / $requiredPhotos',
              ),

              const Divider(height: 28),

              const Text(
                'Commercial checks',
                style: TextStyle(fontWeight: FontWeight.w700),
              ),

              const SizedBox(height: 8),

              _CheckLine(
                label: 'Partner accepted commission',
                complete: commissionAccepted,
              ),

              _CheckLine(
                label: 'Pata Hao verified commission',
                complete: commissionVerified,
              ),

              _CheckLine(
                label: 'Commission locked',
                complete: commissionLocked,
              ),

              _CheckLine(
                label: 'Partner declared mandate',
                complete: mandateDeclared,
              ),

              _CheckLine(
                label: 'Pata Hao approved mandate',
                complete: mandateApproved,
              ),

              if (blockers.isNotEmpty) ...[
                const SizedBox(height: 12),
                _BlockerSummary(blockers: blockers),
              ],

              const SizedBox(height: 14),

              SizedBox(
                width: double.infinity,
                child: FilledButton.icon(
                  onPressed: onOpen,
                  icon: const Icon(Icons.chevron_right),
                  label: const Text('Review Property'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _ReadyChip extends StatelessWidget {
  const _ReadyChip({required this.ready});

  final bool ready;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: ready ? const Color(0xFFE8F5E9) : const Color(0xFFFFF7ED),
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(
        ready ? 'Ready' : 'Review',
        style: TextStyle(
          fontSize: 12,
          fontWeight: FontWeight.w700,
          color: ready ? const Color(0xFF166534) : const Color(0xFF9A3412),
        ),
      ),
    );
  }
}

class _InfoLine extends StatelessWidget {
  const _InfoLine({
    required this.icon,
    required this.label,
    required this.value,
  });

  final IconData icon;
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Icon(icon, size: 20, color: Colors.black54),
        const SizedBox(width: 9),
        Expanded(
          child: Text(label, style: const TextStyle(color: Colors.black54)),
        ),
        const SizedBox(width: 10),
        Flexible(
          child: Text(
            value,
            textAlign: TextAlign.end,
            style: const TextStyle(fontWeight: FontWeight.w600),
          ),
        ),
      ],
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
            size: 19,
            color: complete ? const Color(0xFF15803D) : Colors.black38,
          ),
          const SizedBox(width: 8),
          Expanded(child: Text(label)),
        ],
      ),
    );
  }
}

class _BlockerSummary extends StatelessWidget {
  const _BlockerSummary({required this.blockers});

  final List<dynamic> blockers;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFFFFF7ED),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: const Color(0xFFFED7AA)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Current blockers',
            style: TextStyle(
              fontWeight: FontWeight.w700,
              color: Color(0xFF9A3412),
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

bool _bool(dynamic value) {
  if (value is bool) {
    return value;
  }

  final normalized = value?.toString().trim().toLowerCase();

  return normalized == 'true' || normalized == '1' || normalized == 'yes';
}
