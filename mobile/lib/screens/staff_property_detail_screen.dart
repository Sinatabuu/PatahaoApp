import 'package:flutter/material.dart';

import 'package:mobile/models/property.dart';
import 'package:mobile/services/staff_property_admin_service.dart';

class StaffPropertyDetailScreen extends StatefulWidget {
  const StaffPropertyDetailScreen({super.key, required this.propertyId});

  final int propertyId;

  @override
  State<StaffPropertyDetailScreen> createState() {
    return _StaffPropertyDetailScreenState();
  }
}

class _StaffPropertyDetailScreenState extends State<StaffPropertyDetailScreen> {
  bool _isLoading = true;
  String? _errorMessage;
  Property? _property;

  @override
  void initState() {
    super.initState();
    _loadProperty();
  }

  Future<void> _loadProperty() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final property = await StaffPropertyAdminService.instance.fetchProperty(
        widget.propertyId,
      );

      if (!mounted) {
        return;
      }

      setState(() {
        _property = property;
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

  String _cleanError(Object error) {
    return error.toString().replaceFirst(RegExp(r'^Exception:\s*'), '').trim();
  }

  String _statusLabel(String status) {
    if (status.trim().isEmpty) {
      return 'Unknown';
    }

    return status
        .replaceAll('_', ' ')
        .split(' ')
        .where((part) => part.isNotEmpty)
        .map(
          (part) =>
              '${part[0].toUpperCase()}${part.substring(1).toLowerCase()}',
        )
        .join(' ');
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF6F8F6),
      appBar: AppBar(
        title: const Text('Property Details'),
        backgroundColor: const Color(0xFF14532D),
        foregroundColor: Colors.white,
        actions: [
          IconButton(
            tooltip: 'Refresh',
            onPressed: _isLoading ? null : _loadProperty,
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      body: _buildBody(),
    );
  }

  Widget _buildBody() {
    if (_isLoading && _property == null) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_errorMessage != null && _property == null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(
                Icons.error_outline,
                size: 56,
                color: Color(0xFFB45309),
              ),
              const SizedBox(height: 16),
              Text(_errorMessage!, textAlign: TextAlign.center),
              const SizedBox(height: 18),
              ElevatedButton.icon(
                onPressed: _loadProperty,
                icon: const Icon(Icons.refresh),
                label: const Text('Try Again'),
              ),
            ],
          ),
        ),
      );
    }

    final property = _property;

    if (property == null) {
      return const SizedBox.shrink();
    }

    return RefreshIndicator(
      onRefresh: _loadProperty,
      child: ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(16),
        children: [
          Text(
            property.title,
            style: const TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 8),
          Text(
            _statusLabel(property.status),
            style: const TextStyle(
              color: Color(0xFF14532D),
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 20),

          _InfoCard(
            title: 'Property',
            rows: [
              _InfoRow(label: 'Type', value: property.formattedPropertyType),
              _InfoRow(label: 'Listing', value: property.formattedListingType),
              _InfoRow(label: 'Price', value: property.formattedPrice),
              _InfoRow(label: 'Location', value: property.locationLabel),
              _InfoRow(label: 'Bedrooms', value: '${property.bedrooms}'),
              _InfoRow(label: 'Bathrooms', value: '${property.bathrooms}'),
            ],
          ),

          const SizedBox(height: 14),

          _InfoCard(
            title: 'Partner',
            rows: [
              _InfoRow(label: 'Partner', value: property.partnerName),
              _InfoRow(label: 'Trust badge', value: property.trustBadge),
            ],
          ),

          const SizedBox(height: 14),

          if (property.description.trim().isNotEmpty)
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Description',
                      style: TextStyle(
                        fontSize: 17,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 10),
                    Text(
                      property.description,
                      style: const TextStyle(height: 1.4),
                    ),
                  ],
                ),
              ),
            ),

          if (property.verificationReturnReason.trim().isNotEmpty) ...[
            const SizedBox(height: 14),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Return Reason',
                      style: TextStyle(
                        fontSize: 17,
                        fontWeight: FontWeight.bold,
                        color: Color(0xFFB45309),
                      ),
                    ),
                    const SizedBox(height: 10),
                    Text(property.verificationReturnReason),
                  ],
                ),
              ),
            ),
          ],

          const SizedBox(height: 14),

          _InfoCard(
            title: 'Media',
            rows: [
              _InfoRow(label: 'Photos', value: '${property.photos.length}'),
              _InfoRow(label: 'Videos', value: '${property.videos.length}'),
              _InfoRow(
                label: 'Amenities',
                value: '${property.amenities.length}',
              ),
            ],
          ),

          const SizedBox(height: 24),
        ],
      ),
    );
  }
}

class _InfoCard extends StatelessWidget {
  const _InfoCard({required this.title, required this.rows});

  final String title;
  final List<_InfoRow> rows;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              title,
              style: const TextStyle(fontSize: 17, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 12),
            ...rows,
          ],
        ),
      ),
    );
  }
}

class _InfoRow extends StatelessWidget {
  const _InfoRow({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 95,
            child: Text(label, style: const TextStyle(color: Colors.black54)),
          ),
          Expanded(
            child: Text(
              value.trim().isEmpty ? '—' : value,
              style: const TextStyle(fontWeight: FontWeight.w500),
            ),
          ),
        ],
      ),
    );
  }
}
