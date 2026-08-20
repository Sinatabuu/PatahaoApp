import 'package:flutter/material.dart';

import 'package:mobile/models/property.dart';
import 'package:mobile/services/staff_property_admin_service.dart';
import 'package:mobile/screens/staff_property_detail_screen.dart';

class StaffPropertiesScreen extends StatefulWidget {
  const StaffPropertiesScreen({super.key});

  @override
  State<StaffPropertiesScreen> createState() {
    return _StaffPropertiesScreenState();
  }
}

class _StaffPropertiesScreenState extends State<StaffPropertiesScreen> {
  static const Map<String, String> _statusLabels = {
    '': 'All',
    'draft': 'Draft',
    'pending': 'Pending',
    'published': 'Published',
    'reserved': 'Reserved',
    'rented': 'Rented',
    'sold': 'Sold',
    'archived': 'Archived',
  };

  String _selectedStatus = '';
  bool _isLoading = true;
  String? _errorMessage;
  List<Property> _properties = const [];

  @override
  void initState() {
    super.initState();
    _loadProperties();
  }

  Future<void> _loadProperties() async {
    if (!mounted) {
      return;
    }

    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final properties = await StaffPropertyAdminService.instance
          .fetchProperties(
            status: _selectedStatus.isEmpty ? null : _selectedStatus,
          );

      if (!mounted) {
        return;
      }

      setState(() {
        _properties = properties;
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

  Future<void> _selectStatus(String status) async {
    if (_selectedStatus == status) {
      return;
    }

    setState(() {
      _selectedStatus = status;
    });

    await _loadProperties();
  }

  String _cleanError(Object error) {
    return error.toString().replaceFirst(RegExp(r'^Exception:\s*'), '').trim();
  }

  String _formatPrice(Property property) {
    final price = property.price.trim();

    if (price.isEmpty) {
      return 'Price not set';
    }

    final numericPrice = double.tryParse(price);

    if (numericPrice == null) {
      return 'KES $price';
    }

    return 'KES ${numericPrice.toStringAsFixed(0)}';
  }

  String _location(Property property) {
    final parts = <String>[
      if (property.estate.trim().isNotEmpty) property.estate.trim(),
      if (property.town.trim().isNotEmpty) property.town.trim(),
      if (property.county.trim().isNotEmpty) property.county.trim(),
    ];

    return parts.join(', ');
  }

  String _statusLabel(String status) {
    return _statusLabels[status] ?? status;
  }

  Color _statusColor(String status) {
    switch (status) {
      case 'published':
        return const Color(0xFF15803D);
      case 'pending':
        return const Color(0xFFB45309);
      case 'draft':
        return const Color(0xFF475569);
      case 'reserved':
        return const Color(0xFF7C3AED);
      case 'rented':
        return const Color(0xFF0369A1);
      case 'sold':
        return const Color(0xFF0F766E);
      case 'archived':
        return const Color(0xFF6B7280);
      default:
        return const Color(0xFF475569);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF6F8F6),
      appBar: AppBar(
        title: const Text('Properties'),
        backgroundColor: const Color(0xFF14532D),
        foregroundColor: Colors.white,
        actions: [
          IconButton(
            tooltip: 'Refresh',
            onPressed: _isLoading ? null : _loadProperties,
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _loadProperties,
        child: Column(
          children: [
            _buildStatusFilters(),
            Expanded(child: _buildBody()),
          ],
        ),
      ),
    );
  }

  Widget _buildStatusFilters() {
    return Container(
      color: Colors.white,
      width: double.infinity,
      padding: const EdgeInsets.symmetric(vertical: 10),
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: 12),
        child: Row(
          children: _statusLabels.entries.map((entry) {
            final selected = entry.key == _selectedStatus;

            return Padding(
              padding: const EdgeInsets.only(right: 8),
              child: ChoiceChip(
                label: Text(entry.value),
                selected: selected,
                onSelected: (_) {
                  _selectStatus(entry.key);
                },
              ),
            );
          }).toList(),
        ),
      ),
    );
  }

  Widget _buildBody() {
    if (_isLoading && _properties.isEmpty) {
      return ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        children: const [
          SizedBox(height: 180),
          Center(child: CircularProgressIndicator()),
        ],
      );
    }

    if (_errorMessage != null && _properties.isEmpty) {
      return ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(20),
        children: [
          const SizedBox(height: 70),
          const Icon(Icons.error_outline, size: 56, color: Color(0xFFB45309)),
          const SizedBox(height: 16),
          const Text(
            'Unable to load properties',
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 10),
          Text(
            _errorMessage!,
            textAlign: TextAlign.center,
            style: const TextStyle(color: Colors.black54),
          ),
          const SizedBox(height: 20),
          Center(
            child: ElevatedButton.icon(
              onPressed: _loadProperties,
              icon: const Icon(Icons.refresh),
              label: const Text('Try Again'),
            ),
          ),
        ],
      );
    }

    if (_properties.isEmpty) {
      final label = _statusLabel(_selectedStatus);

      return ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(24),
        children: [
          const SizedBox(height: 100),
          const Icon(Icons.home_work_outlined, size: 64, color: Colors.black38),
          const SizedBox(height: 16),
          Text(
            _selectedStatus.isEmpty
                ? 'No properties found'
                : 'No $label properties',
            textAlign: TextAlign.center,
            style: const TextStyle(fontSize: 19, fontWeight: FontWeight.bold),
          ),
        ],
      );
    }

    return ListView.separated(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.all(16),
      itemCount: _properties.length,
      separatorBuilder: (_, _) {
        return const SizedBox(height: 10);
      },
      itemBuilder: (context, index) {
        final property = _properties[index];

        return _PropertyAdminCard(
          property: property,
          statusLabel: _statusLabel(property.status),
          statusColor: _statusColor(property.status),
          location: _location(property),
          price: _formatPrice(property),
          onTap: () async {
            await Navigator.of(context).push(
              MaterialPageRoute<void>(
                builder: (_) {
                  return StaffPropertyDetailScreen(propertyId: property.id);
                },
              ),
            );

            if (!mounted) {
              return;
            }

            await _loadProperties();
          },
        );
      },
    );
  }
}

class _PropertyAdminCard extends StatelessWidget {
  const _PropertyAdminCard({
    required this.property,
    required this.statusLabel,
    required this.statusColor,
    required this.location,
    required this.price,
    required this.onTap,
  });

  final Property property;
  final String statusLabel;
  final Color statusColor;
  final String location;
  final String price;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final partnerName = property.partner?.name.trim() ?? '';

    return Card(
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(
                    child: Text(
                      property.title,
                      style: const TextStyle(
                        fontSize: 17,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 10,
                      vertical: 5,
                    ),
                    decoration: BoxDecoration(
                      color: statusColor.withValues(alpha: 0.12),
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: Text(
                      statusLabel,
                      style: TextStyle(
                        color: statusColor,
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 10),
              Text(
                price,
                style: const TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.w600,
                  color: Color(0xFF14532D),
                ),
              ),
              if (location.isNotEmpty) ...[
                const SizedBox(height: 6),
                Row(
                  children: [
                    const Icon(
                      Icons.location_on_outlined,
                      size: 17,
                      color: Colors.black45,
                    ),
                    const SizedBox(width: 5),
                    Expanded(
                      child: Text(
                        location,
                        style: const TextStyle(color: Colors.black54),
                      ),
                    ),
                  ],
                ),
              ],
              if (partnerName.isNotEmpty) ...[
                const SizedBox(height: 6),
                Row(
                  children: [
                    const Icon(
                      Icons.person_outline,
                      size: 17,
                      color: Colors.black45,
                    ),
                    const SizedBox(width: 5),
                    Expanded(
                      child: Text(
                        partnerName,
                        style: const TextStyle(color: Colors.black54),
                      ),
                    ),
                  ],
                ),
              ],
              const SizedBox(height: 8),
              Row(
                children: [
                  Text(
                    property.listingType == 'sale' ? 'For Sale' : 'For Rent',
                    style: const TextStyle(fontSize: 13, color: Colors.black45),
                  ),
                  const Spacer(),
                  const Icon(Icons.chevron_right, color: Colors.black38),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
