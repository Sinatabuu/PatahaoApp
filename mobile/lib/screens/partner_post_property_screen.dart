import 'package:flutter/material.dart';

import 'package:mobile/models/property.dart';
import 'package:mobile/screens/partner_new_property_form_screen.dart';
import 'package:mobile/screens/partner_property_workspace_screen.dart';
import 'package:mobile/services/partner_property_service.dart';
import 'package:mobile/services/property_location_service.dart';

class PartnerPostPropertyScreen extends StatefulWidget {
  const PartnerPostPropertyScreen({super.key});

  @override
  State<PartnerPostPropertyScreen> createState() {
    return _PartnerPostPropertyScreenState();
  }
}

class _PartnerPostPropertyScreenState extends State<PartnerPostPropertyScreen> {
  bool _isCheckingLocation = false;
  bool _isSubmittingDecision = false;

  String? _errorMessage;

  PropertyLocationResult? _location;

  List<Map<String, dynamic>> _candidates = const [];

  Future<void> _checkLocation() async {
    if (_isCheckingLocation || _isSubmittingDecision) {
      return;
    }

    setState(() {
      _isCheckingLocation = true;
      _errorMessage = null;
    });

    try {
      final location = await PropertyLocationService.instance
          .captureCurrentLocation();

      final result = await PartnerPropertyService.instance.findNearbyProperties(
        latitude: location.latitude,
        longitude: location.longitude,
      );

      final rawCandidates = result['candidates'];

      final candidates = rawCandidates is List
          ? rawCandidates
                .whereType<Map>()
                .map((item) => Map<String, dynamic>.from(item))
                .toList()
          : <Map<String, dynamic>>[];

      if (!mounted) {
        return;
      }

      setState(() {
        _location = location;
        _candidates = candidates;
      });
    } catch (error) {
      if (!mounted) {
        return;
      }

      setState(() {
        _errorMessage = _cleanError(error);
      });
    } finally {
      if (mounted) {
        setState(() {
          _isCheckingLocation = false;
        });
      }
    }
  }

  Future<void> _openMyProperty(Map<String, dynamic> candidate) async {
    if (_isSubmittingDecision) {
      return;
    }

    final propertyId = int.tryParse(candidate['id']?.toString() ?? '');

    if (propertyId == null || propertyId <= 0) {
      return;
    }

    bool shouldCloseScreen = false;

    setState(() {
      _isSubmittingDecision = true;
      _errorMessage = null;
    });

    try {
      final Property property = await PartnerPropertyService.instance
          .fetchMyProperty(propertyId);

      if (!mounted) {
        return;
      }

      final changed = await Navigator.of(context).push<bool>(
        MaterialPageRoute<bool>(
          builder: (_) => PartnerPropertyWorkspaceScreen(property: property),
        ),
      );

      if (!mounted) {
        return;
      }

      shouldCloseScreen = changed == true;
    } catch (error) {
      if (!mounted) {
        return;
      }

      final message = _cleanError(error);

      setState(() {
        _errorMessage = message;
      });

      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(message)));
    } finally {
      if (mounted) {
        setState(() {
          _isSubmittingDecision = false;
        });
      }
    }

    if (shouldCloseScreen && mounted) {
      Navigator.of(context).pop(true);
    }
  }

  Future<void> _confirmDifferentProperty() async {
    final location = _location;

    if (location == null || _isSubmittingDecision) {
      return;
    }

    final candidateIds = _candidates
        .map((candidate) => int.tryParse(candidate['id']?.toString() ?? ''))
        .whereType<int>()
        .toList();

    bool shouldCloseScreen = false;

    setState(() {
      _isSubmittingDecision = true;
      _errorMessage = null;
    });

    try {
      final result = await PartnerPropertyService.instance
          .confirmDifferentProperty(
            latitude: location.latitude,
            longitude: location.longitude,
            candidateIds: candidateIds,
          );

      if (!mounted) {
        return;
      }

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            result['detail']?.toString() ?? 'Different property confirmed.',
          ),
        ),
      );

      final property = await Navigator.of(context).push<Property?>(
        MaterialPageRoute<Property?>(
          builder: (_) => PartnerNewPropertyFormScreen(
            latitude: location.latitude,
            longitude: location.longitude,
          ),
        ),
      );

      if (!mounted) {
        return;
      }

      shouldCloseScreen = property != null;
    } catch (error) {
      if (!mounted) {
        return;
      }

      final message = _cleanError(error);

      setState(() {
        _errorMessage = message;
      });

      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(message)));
    } finally {
      if (mounted) {
        setState(() {
          _isSubmittingDecision = false;
        });
      }
    }

    if (shouldCloseScreen && mounted) {
      Navigator.of(context).pop(true);
    }
  }

  Future<void> _joinProperty(Map<String, dynamic> candidate) async {
    if (_isSubmittingDecision) {
      return;
    }

    final propertyId = int.tryParse(candidate['id']?.toString() ?? '');

    if (propertyId == null || propertyId <= 0) {
      return;
    }

    bool shouldCloseScreen = false;

    setState(() {
      _isSubmittingDecision = true;
      _errorMessage = null;
    });

    try {
      final result = await PartnerPropertyService.instance.joinExistingProperty(
        propertyId,
      );

      if (!mounted) {
        return;
      }

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            result['detail']?.toString() ??
                'Property participation request submitted.',
          ),
        ),
      );

      shouldCloseScreen = true;
    } catch (error) {
      if (!mounted) {
        return;
      }

      final message = _cleanError(error);

      setState(() {
        _errorMessage = message;
      });

      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(message)));
    } finally {
      if (mounted) {
        setState(() {
          _isSubmittingDecision = false;
        });
      }
    }

    if (shouldCloseScreen && mounted) {
      Navigator.of(context).pop(true);
    }
  }

  String _cleanError(Object error) {
    return error.toString().replaceFirst(RegExp(r'^Exception:\s*'), '').trim();
  }

  String _candidateTitle(Map<String, dynamic> candidate) {
    final title = candidate['title']?.toString().trim() ?? '';

    if (title.isNotEmpty) {
      return title;
    }

    return 'Nearby property';
  }

  String _candidateLocation(Map<String, dynamic> candidate) {
    final estate = candidate['estate']?.toString().trim() ?? '';
    final town = candidate['town']?.toString().trim() ?? '';

    final parts = <String>[
      if (estate.isNotEmpty) estate,
      if (town.isNotEmpty) town,
    ];

    if (parts.isEmpty) {
      return 'Location unavailable';
    }

    return parts.join(', ');
  }

  String _candidateDistance(Map<String, dynamic> candidate) {
    final raw = candidate['distance_meters'];

    if (raw == null) {
      return '';
    }

    final distance = double.tryParse(raw.toString());

    if (distance == null) {
      return '';
    }

    if (distance < 1000) {
      return '${distance.round()} m away';
    }

    return '${(distance / 1000).toStringAsFixed(1)} km away';
  }

  bool _candidateBelongsToCurrentPartner(Map<String, dynamic> candidate) {
    final values = <dynamic>[
      candidate['is_my_property'],
      candidate['belongs_to_partner'],
      candidate['owned_by_me'],
    ];

    for (final value in values) {
      if (value == true) {
        return true;
      }

      final text = value?.toString().trim().toLowerCase();

      if (text == 'true' || text == '1' || text == 'yes') {
        return true;
      }
    }

    return false;
  }

  @override
  Widget build(BuildContext context) {
    final location = _location;

    return Scaffold(
      backgroundColor: const Color(0xFFF6F8F6),
      appBar: AppBar(
        title: const Text('Post Property'),
        backgroundColor: const Color(0xFF14532D),
        foregroundColor: Colors.white,
      ),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.fromLTRB(18, 20, 18, 32),
          children: [
            const Text(
              'Add a property',
              style: TextStyle(
                fontSize: 24,
                fontWeight: FontWeight.bold,
                color: Color(0xFF111827),
              ),
            ),
            const SizedBox(height: 8),
            const Text(
              'Pata Hao checks nearby properties first so the same '
              'building is not posted more than once.',
              style: TextStyle(color: Colors.black54, height: 1.45),
            ),
            const SizedBox(height: 20),
            FilledButton.icon(
              onPressed: _isCheckingLocation || _isSubmittingDecision
                  ? null
                  : _checkLocation,
              icon: _isCheckingLocation
                  ? const SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.my_location_outlined),
              label: Text(
                _isCheckingLocation
                    ? 'Checking location...'
                    : location == null
                    ? 'Check Current Location'
                    : 'Check Location Again',
              ),
            ),
            if (_errorMessage != null && _errorMessage!.trim().isNotEmpty) ...[
              const SizedBox(height: 16),
              Container(
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: const Color(0xFFFEF2F2),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: const Color(0xFFFECACA)),
                ),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Icon(Icons.error_outline, color: Color(0xFFB91C1C)),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Text(
                        _errorMessage!,
                        style: const TextStyle(color: Color(0xFF991B1B)),
                      ),
                    ),
                  ],
                ),
              ),
            ],
            if (location != null) ...[
              const SizedBox(height: 20),
              Card(
                elevation: 0,
                color: const Color(0xFFF0FDF4),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(14),
                  side: const BorderSide(color: Color(0xFFBBF7D0)),
                ),
                child: const Padding(
                  padding: EdgeInsets.all(16),
                  child: Row(
                    children: [
                      Icon(
                        Icons.location_on_outlined,
                        color: Color(0xFF15803D),
                      ),
                      SizedBox(width: 10),
                      Expanded(
                        child: Text(
                          'Location captured. Check the nearby '
                          'properties below before continuing.',
                          style: TextStyle(
                            color: Color(0xFF166534),
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 20),
              if (_candidates.isEmpty) ...[
                const Card(
                  child: Padding(
                    padding: EdgeInsets.all(18),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Icon(
                              Icons.check_circle_outline,
                              color: Color(0xFF15803D),
                            ),
                            SizedBox(width: 8),
                            Expanded(
                              child: Text(
                                'No nearby Pata Hao property found',
                                style: TextStyle(
                                  fontWeight: FontWeight.bold,
                                  fontSize: 16,
                                ),
                              ),
                            ),
                          ],
                        ),
                        SizedBox(height: 8),
                        Text(
                          'This location appears clear for a new '
                          'property record.',
                          style: TextStyle(color: Colors.black54),
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 14),
                FilledButton.icon(
                  onPressed: _isSubmittingDecision
                      ? null
                      : _confirmDifferentProperty,
                  icon: _isSubmittingDecision
                      ? const SizedBox(
                          width: 18,
                          height: 18,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Icon(Icons.add_home_work_outlined),
                  label: Text(
                    _isSubmittingDecision
                        ? 'Please wait...'
                        : 'Continue with New Property',
                  ),
                ),
              ] else ...[
                const Text(
                  'Nearby properties found',
                  style: TextStyle(
                    fontSize: 19,
                    fontWeight: FontWeight.bold,
                    color: Color(0xFF111827),
                  ),
                ),
                const SizedBox(height: 8),
                const Text(
                  'These properties are close to your current '
                  'location. Check carefully before creating '
                  'another property.',
                  style: TextStyle(color: Colors.black54, height: 1.4),
                ),
                const SizedBox(height: 14),
                ..._candidates.map((candidate) {
                  final isMine = _candidateBelongsToCurrentPartner(candidate);

                  final distance = _candidateDistance(candidate);

                  return Card(
                    margin: const EdgeInsets.only(bottom: 14),
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            _candidateTitle(candidate),
                            style: const TextStyle(
                              fontSize: 17,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                          const SizedBox(height: 6),
                          Text(
                            _candidateLocation(candidate),
                            style: const TextStyle(color: Colors.black54),
                          ),
                          if (distance.isNotEmpty) ...[
                            const SizedBox(height: 4),
                            Text(
                              distance,
                              style: const TextStyle(color: Colors.black54),
                            ),
                          ],
                          const SizedBox(height: 14),
                          if (isMine)
                            SizedBox(
                              width: double.infinity,
                              child: FilledButton.icon(
                                onPressed: _isSubmittingDecision
                                    ? null
                                    : () {
                                        _openMyProperty(candidate);
                                      },
                                icon: const Icon(Icons.home_work_outlined),
                                label: const Text('Open My Property'),
                              ),
                            )
                          else
                            SizedBox(
                              width: double.infinity,
                              child: FilledButton.icon(
                                onPressed: _isSubmittingDecision
                                    ? null
                                    : () {
                                        _joinProperty(candidate);
                                      },
                                icon: const Icon(Icons.link),
                                label: const Text('This is the Same Property'),
                              ),
                            ),
                        ],
                      ),
                    ),
                  );
                }),
                const SizedBox(height: 8),
                OutlinedButton.icon(
                  onPressed: _isSubmittingDecision
                      ? null
                      : _confirmDifferentProperty,
                  icon: const Icon(Icons.add_home_work_outlined),
                  label: const Text('None of These - Create New Property'),
                ),
              ],
            ],
          ],
        ),
      ),
    );
  }
}
