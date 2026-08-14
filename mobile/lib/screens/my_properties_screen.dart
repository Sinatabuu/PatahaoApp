import 'package:flutter/material.dart';

import 'package:mobile/models/property.dart';
import 'package:mobile/services/partner_property_service.dart';
import 'package:mobile/services/property_service.dart';
import 'package:mobile/screens/partner_property_workspace_screen.dart'
    as photo_workspace;

class MyPropertiesScreen extends StatefulWidget {
  const MyPropertiesScreen({super.key});

  @override
  State<MyPropertiesScreen> createState() => _MyPropertiesScreenState();
}

class _MyPropertiesScreenState extends State<MyPropertiesScreen> {
  late Future<List<Property>> _propertiesFuture;

  String _selectedStatus = 'all';
  String _selectedListingType = 'all';

  @override
  void initState() {
    super.initState();
    _loadProperties();
  }

  void _loadProperties() {
    _propertiesFuture = PartnerPropertyService.instance.fetchMyProperties(
      status: _selectedStatus == 'all' ? null : _selectedStatus,
      listingType: _selectedListingType == 'all' ? null : _selectedListingType,
    );
  }

  Future<void> _refreshProperties() async {
    setState(_loadProperties);
    await _propertiesFuture;
  }

  void _applyFilters() {
    setState(_loadProperties);
  }

  Future<void> _openPropertyWorkspace(Property property) async {
    await Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (context) {
          return photo_workspace.PartnerPropertyWorkspaceScreen(
            property: property,
          );
        },
      ),
    );

    if (!mounted) {
      return;
    }

    await _refreshProperties();
  }

  String _cleanError(Object? error) {
    final message = error?.toString() ?? '';

    if (message.startsWith('Exception: ')) {
      return message.substring('Exception: '.length);
    }

    return message.isEmpty ? 'Unable to load your properties.' : message;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF6F8F6),
      appBar: AppBar(
        title: const Text('My Properties'),
        backgroundColor: Colors.white,
        actions: [
          IconButton(
            tooltip: 'Refresh',
            onPressed: _refreshProperties,
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      body: Column(
        children: [
          _FilterBar(
            selectedStatus: _selectedStatus,
            selectedListingType: _selectedListingType,
            onStatusChanged: (value) {
              setState(() {
                _selectedStatus = value;
              });

              _applyFilters();
            },
            onListingTypeChanged: (value) {
              setState(() {
                _selectedListingType = value;
              });

              _applyFilters();
            },
          ),
          Expanded(
            child: FutureBuilder<List<Property>>(
              future: _propertiesFuture,
              builder: (context, snapshot) {
                if (snapshot.connectionState == ConnectionState.waiting) {
                  return const Center(child: CircularProgressIndicator());
                }

                if (snapshot.hasError) {
                  return _ErrorView(
                    message: _cleanError(snapshot.error),
                    onRetry: _refreshProperties,
                  );
                }

                final properties = snapshot.data ?? const <Property>[];

                if (properties.isEmpty) {
                  return RefreshIndicator(
                    onRefresh: _refreshProperties,
                    child: ListView(
                      physics: const AlwaysScrollableScrollPhysics(),
                      padding: const EdgeInsets.all(24),
                      children: const [
                        SizedBox(height: 80),
                        _EmptyPropertiesView(),
                      ],
                    ),
                  );
                }

                return RefreshIndicator(
                  onRefresh: _refreshProperties,
                  child: ListView.separated(
                    physics: const AlwaysScrollableScrollPhysics(),
                    padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
                    itemCount: properties.length,
                    separatorBuilder: (_, _) => const SizedBox(height: 14),
                    itemBuilder: (context, index) {
                      final property = properties[index];

                      return _PartnerPropertyCard(
                        property: property,
                        onManage: () => _openPropertyWorkspace(property),
                      );
                    },
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}

class _FilterBar extends StatelessWidget {
  const _FilterBar({
    required this.selectedStatus,
    required this.selectedListingType,
    required this.onStatusChanged,
    required this.onListingTypeChanged,
  });

  final String selectedStatus;
  final String selectedListingType;
  final ValueChanged<String> onStatusChanged;
  final ValueChanged<String> onListingTypeChanged;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.white,
      elevation: 1,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Filter inventory',
              style: Theme.of(
                context,
              ).textTheme.labelLarge?.copyWith(fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: 10),
            Row(
              children: [
                Expanded(
                  child: DropdownButtonFormField<String>(
                    initialValue: selectedStatus,
                    decoration: const InputDecoration(
                      labelText: 'Status',
                      border: OutlineInputBorder(),
                      isDense: true,
                    ),
                    items: const [
                      DropdownMenuItem(
                        value: 'all',
                        child: Text('All statuses'),
                      ),
                      DropdownMenuItem(value: 'draft', child: Text('Draft')),
                      DropdownMenuItem(
                        value: 'pending',
                        child: Text('Pending verification'),
                      ),
                      DropdownMenuItem(
                        value: 'published',
                        child: Text('Published'),
                      ),
                      DropdownMenuItem(
                        value: 'reserved',
                        child: Text('Reserved'),
                      ),
                      DropdownMenuItem(value: 'rented', child: Text('Rented')),
                      DropdownMenuItem(value: 'sold', child: Text('Sold')),
                      DropdownMenuItem(
                        value: 'archived',
                        child: Text('Archived'),
                      ),
                    ],
                    onChanged: (value) {
                      if (value != null) {
                        onStatusChanged(value);
                      }
                    },
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: DropdownButtonFormField<String>(
                    initialValue: selectedListingType,
                    decoration: const InputDecoration(
                      labelText: 'Listing',
                      border: OutlineInputBorder(),
                      isDense: true,
                    ),
                    items: const [
                      DropdownMenuItem(
                        value: 'all',
                        child: Text('Rent and sale'),
                      ),
                      DropdownMenuItem(value: 'rent', child: Text('For rent')),
                      DropdownMenuItem(value: 'sale', child: Text('For sale')),
                    ],
                    onChanged: (value) {
                      if (value != null) {
                        onListingTypeChanged(value);
                      }
                    },
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _PartnerPropertyCard extends StatelessWidget {
  const _PartnerPropertyCard({required this.property, required this.onManage});

  final Property property;
  final VoidCallback onManage;

  String? _imageUrl() {
    final coverPhoto = property.coverPhoto;

    if (coverPhoto == null || coverPhoto.image.trim().isEmpty) {
      return null;
    }

    final image = coverPhoto.image.trim();

    if (image.startsWith('http://') || image.startsWith('https://')) {
      return image;
    }

    if (image.startsWith('/')) {
      return '${PropertyService.baseUrl}$image';
    }

    return '${PropertyService.baseUrl}/$image';
  }

  @override
  Widget build(BuildContext context) {
    final imageUrl = _imageUrl();

    return Card(
      margin: EdgeInsets.zero,
      clipBehavior: Clip.antiAlias,
      elevation: 1.5,
      child: InkWell(
        onTap: onManage,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            SizedBox(
              height: 185,
              width: double.infinity,
              child: imageUrl == null
                  ? const _PropertyImagePlaceholder()
                  : Image.network(
                      imageUrl,
                      fit: BoxFit.cover,
                      errorBuilder: (context, error, stackTrace) {
                        return const _PropertyImagePlaceholder();
                      },
                      loadingBuilder: (context, child, progress) {
                        if (progress == null) {
                          return child;
                        }

                        return const Center(child: CircularProgressIndicator());
                      },
                    ),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 16, 16, 14),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Expanded(
                        child: Text(
                          property.title,
                          style: Theme.of(context).textTheme.titleLarge
                              ?.copyWith(fontWeight: FontWeight.w800),
                        ),
                      ),
                      const SizedBox(width: 12),
                      _StatusBadge(status: property.status),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Text(
                    property.formattedPrice,
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.w800,
                      color: Colors.green.shade800,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    '${property.formattedPropertyType}'
                    ' • ${property.formattedListingType}',
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: 6),
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Icon(
                        Icons.location_on_outlined,
                        size: 18,
                        color: Colors.grey.shade700,
                      ),
                      const SizedBox(width: 5),
                      Expanded(
                        child: Text(
                          property.locationLabel,
                          style: TextStyle(color: Colors.grey.shade700),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  Wrap(
                    spacing: 16,
                    runSpacing: 8,
                    children: [
                      _PropertyMetric(
                        icon: Icons.bed_outlined,
                        label: '${property.bedrooms} bedrooms',
                      ),
                      _PropertyMetric(
                        icon: Icons.bathtub_outlined,
                        label: '${property.bathrooms} bathrooms',
                      ),
                      _PropertyMetric(
                        icon: Icons.photo_library_outlined,
                        label: '${property.photos.length} photos',
                      ),
                    ],
                  ),
                  const SizedBox(height: 16),
                  SizedBox(
                    width: double.infinity,
                    child: FilledButton.icon(
                      onPressed: onManage,
                      icon: const Icon(Icons.settings_outlined),
                      label: const Text('Manage Property'),
                    ),
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

class _PropertyImagePlaceholder extends StatelessWidget {
  const _PropertyImagePlaceholder();

  @override
  Widget build(BuildContext context) {
    return Container(
      color: Colors.grey.shade200,
      alignment: Alignment.center,
      child: Icon(
        Icons.home_work_outlined,
        size: 58,
        color: Colors.grey.shade500,
      ),
    );
  }
}

class _PropertyMetric extends StatelessWidget {
  const _PropertyMetric({required this.icon, required this.label});

  final IconData icon;
  final String label;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: 18, color: Colors.grey.shade700),
        const SizedBox(width: 5),
        Text(label, style: TextStyle(color: Colors.grey.shade700)),
      ],
    );
  }
}

class _StatusBadge extends StatelessWidget {
  const _StatusBadge({required this.status});

  final String status;

  String get _label {
    switch (status.trim().toLowerCase()) {
      case 'draft':
        return 'Draft';
      case 'pending':
        return 'Pending';
      case 'published':
        return 'Published';
      case 'reserved':
        return 'Reserved';
      case 'rented':
        return 'Rented';
      case 'sold':
        return 'Sold';
      case 'archived':
        return 'Archived';
      default:
        return status.trim().isEmpty ? 'Unknown' : status;
    }
  }

  Color _backgroundColor(BuildContext context) {
    switch (status.trim().toLowerCase()) {
      case 'published':
        return Colors.green.shade100;
      case 'pending':
        return Colors.orange.shade100;
      case 'reserved':
        return Colors.blue.shade100;
      case 'rented':
      case 'sold':
        return Colors.purple.shade100;
      case 'archived':
        return Colors.grey.shade300;
      default:
        return Colors.grey.shade200;
    }
  }

  Color _foregroundColor(BuildContext context) {
    switch (status.trim().toLowerCase()) {
      case 'published':
        return Colors.green.shade900;
      case 'pending':
        return Colors.orange.shade900;
      case 'reserved':
        return Colors.blue.shade900;
      case 'rented':
      case 'sold':
        return Colors.purple.shade900;
      case 'archived':
        return Colors.grey.shade800;
      default:
        return Colors.grey.shade800;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: _backgroundColor(context),
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(
        _label,
        style: TextStyle(
          color: _foregroundColor(context),
          fontSize: 12,
          fontWeight: FontWeight.w800,
        ),
      ),
    );
  }
}

class _EmptyPropertiesView extends StatelessWidget {
  const _EmptyPropertiesView();

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Card(
        child: Padding(
          padding: const EdgeInsets.all(28),
          child: Column(
            children: [
              Icon(
                Icons.home_work_outlined,
                size: 62,
                color: Colors.grey.shade500,
              ),
              const SizedBox(height: 16),
              Text(
                'No properties found',
                style: Theme.of(
                  context,
                ).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w800),
              ),
              const SizedBox(height: 8),
              Text(
                'There are no properties matching the '
                'selected inventory filters.',
                textAlign: TextAlign.center,
                style: TextStyle(color: Colors.grey.shade700),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _ErrorView extends StatelessWidget {
  const _ErrorView({required this.message, required this.onRetry});

  final String message;
  final Future<void> Function() onRetry;

  @override
  Widget build(BuildContext context) {
    return RefreshIndicator(
      onRefresh: onRetry,
      child: ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(24),
        children: [
          const SizedBox(height: 70),
          Icon(Icons.error_outline, size: 60, color: Colors.red.shade700),
          const SizedBox(height: 16),
          Text(
            'Unable to load properties',
            textAlign: TextAlign.center,
            style: Theme.of(
              context,
            ).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w800),
          ),
          const SizedBox(height: 10),
          Text(message, textAlign: TextAlign.center),
          const SizedBox(height: 20),
          Center(
            child: FilledButton.icon(
              onPressed: onRetry,
              icon: const Icon(Icons.refresh),
              label: const Text('Try Again'),
            ),
          ),
        ],
      ),
    );
  }
}

class PartnerPropertyWorkspaceScreen extends StatelessWidget {
  const PartnerPropertyWorkspaceScreen({required this.property, super.key});

  final Property property;

  String? _imageUrl() {
    final coverPhoto = property.coverPhoto;

    if (coverPhoto == null || coverPhoto.image.trim().isEmpty) {
      return null;
    }

    final image = coverPhoto.image.trim();

    if (image.startsWith('http://') || image.startsWith('https://')) {
      return image;
    }

    if (image.startsWith('/')) {
      return '${PropertyService.baseUrl}$image';
    }

    return '${PropertyService.baseUrl}/$image';
  }

  void _openPropertyDetails(BuildContext context) {
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      builder: (sheetContext) {
        return DraggableScrollableSheet(
          expand: false,
          initialChildSize: 0.72,
          minChildSize: 0.45,
          maxChildSize: 0.92,
          builder: (context, scrollController) {
            return ListView(
              controller: scrollController,
              padding: const EdgeInsets.fromLTRB(20, 4, 20, 32),
              children: [
                Text(
                  'Property Details',
                  style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                    fontWeight: FontWeight.w800,
                  ),
                ),
                const SizedBox(height: 20),
                _DetailRow(
                  icon: Icons.home_work_outlined,
                  label: 'Property type',
                  value: property.formattedPropertyType,
                ),
                _DetailRow(
                  icon: Icons.sell_outlined,
                  label: 'Listing type',
                  value: property.formattedListingType,
                ),
                _DetailRow(
                  icon: Icons.payments_outlined,
                  label: 'Price',
                  value: property.formattedPrice,
                ),
                _DetailRow(
                  icon: Icons.bed_outlined,
                  label: 'Bedrooms',
                  value: property.bedrooms.toString(),
                ),
                _DetailRow(
                  icon: Icons.bathtub_outlined,
                  label: 'Bathrooms',
                  value: property.bathrooms.toString(),
                ),
                _DetailRow(
                  icon: Icons.location_on_outlined,
                  label: 'Location',
                  value: property.locationLabel,
                ),
                const SizedBox(height: 16),
                Text(
                  'Description',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.w800,
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  property.description.trim().isEmpty
                      ? 'No description has been provided.'
                      : property.description,
                  style: Theme.of(
                    context,
                  ).textTheme.bodyLarge?.copyWith(height: 1.5),
                ),
              ],
            );
          },
        );
      },
    );
  }

  void _openPhotoSummary(BuildContext context) {
    showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      builder: (sheetContext) {
        return SafeArea(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(20, 4, 20, 28),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                CircleAvatar(
                  radius: 34,
                  backgroundColor: Colors.green.shade50,
                  child: Icon(
                    Icons.photo_library_outlined,
                    size: 34,
                    color: Colors.green.shade800,
                  ),
                ),
                const SizedBox(height: 16),
                Text(
                  '${property.photos.length} uploaded photos',
                  style: Theme.of(
                    sheetContext,
                  ).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w800),
                ),
                const SizedBox(height: 10),
                const Text(
                  'The property photos are available to customers on the '
                  'listing. Uploading, deleting and reordering photos will be '
                  'connected to the protected partner media API next.',
                  textAlign: TextAlign.center,
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  void _openStatusInformation(BuildContext context) {
    showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      builder: (sheetContext) {
        return SafeArea(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(20, 4, 20, 28),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                _StatusBadge(status: property.status),
                const SizedBox(height: 18),
                Text(
                  'Listing workflow',
                  style: Theme.of(
                    sheetContext,
                  ).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w800),
                ),
                const SizedBox(height: 10),
                const Text(
                  'Status changes will use protected partner actions. This '
                  'ensures that a partner can manage only properties assigned '
                  'to their own approved account.',
                  textAlign: TextAlign.center,
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  void _openPreview(BuildContext context) {
    Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder: (_) => _PartnerPropertyPreviewScreen(property: property),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final imageUrl = _imageUrl();

    return Scaffold(
      backgroundColor: const Color(0xFFF6F8F6),
      appBar: AppBar(
        title: const Text('Property Workspace'),
        backgroundColor: Colors.white,
      ),
      body: ListView(
        padding: const EdgeInsets.only(bottom: 32),
        children: [
          _WorkspaceHero(property: property, imageUrl: imageUrl),
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 18, 16, 0),
            child: _WorkspaceSummary(property: property),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 24, 16, 10),
            child: Text(
              'Manage property',
              style: Theme.of(
                context,
              ).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w800),
            ),
          ),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: GridView.count(
              crossAxisCount: 2,
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              mainAxisSpacing: 12,
              crossAxisSpacing: 12,
              childAspectRatio: 1.12,
              children: [
                _WorkspaceTile(
                  icon: Icons.edit_note_outlined,
                  title: 'Details',
                  subtitle: 'Review listing information',
                  onTap: () => _openPropertyDetails(context),
                ),
                _WorkspaceTile(
                  icon: Icons.photo_library_outlined,
                  title: 'Photos',
                  subtitle: '${property.photos.length} uploaded',
                  onTap: () => _openPhotoSummary(context),
                ),
                _WorkspaceTile(
                  icon: Icons.fact_check_outlined,
                  title: 'Status',
                  subtitle: _statusLabel(property.status),
                  onTap: () => _openStatusInformation(context),
                ),
                _WorkspaceTile(
                  icon: Icons.visibility_outlined,
                  title: 'Preview',
                  subtitle: 'See the customer view',
                  onTap: () => _openPreview(context),
                ),
              ],
            ),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 26, 16, 10),
            child: Text(
              'Next partner tools',
              style: Theme.of(
                context,
              ).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w800),
            ),
          ),
          const Padding(
            padding: EdgeInsets.symmetric(horizontal: 16),
            child: Column(
              children: [
                _PlannedWorkspaceOption(
                  icon: Icons.edit_outlined,
                  title: 'Edit property details',
                  subtitle: 'Requires the protected property update endpoint.',
                ),
                _PlannedWorkspaceOption(
                  icon: Icons.video_library_outlined,
                  title: 'Manage videos',
                  subtitle: 'Requires the protected partner media endpoint.',
                ),
                _PlannedWorkspaceOption(
                  icon: Icons.analytics_outlined,
                  title: 'Property analytics',
                  subtitle: 'Will use real views and viewing-request data.',
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _WorkspaceHero extends StatelessWidget {
  const _WorkspaceHero({required this.property, required this.imageUrl});

  final Property property;
  final String? imageUrl;

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        SizedBox(
          height: 250,
          width: double.infinity,
          child: imageUrl == null
              ? const _PropertyImagePlaceholder()
              : Image.network(
                  imageUrl!,
                  fit: BoxFit.cover,
                  errorBuilder: (context, error, stackTrace) {
                    return const _PropertyImagePlaceholder();
                  },
                  loadingBuilder: (context, child, progress) {
                    if (progress == null) {
                      return child;
                    }

                    return const Center(child: CircularProgressIndicator());
                  },
                ),
        ),
        Positioned.fill(
          child: DecoratedBox(
            decoration: BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                colors: [
                  Colors.transparent,
                  Colors.black.withValues(alpha: 0.78),
                ],
              ),
            ),
          ),
        ),
        Positioned(
          left: 16,
          right: 16,
          bottom: 18,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _StatusBadge(status: property.status),
              const SizedBox(height: 10),
              Text(
                property.title,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                  color: Colors.white,
                  fontWeight: FontWeight.w900,
                ),
              ),
              const SizedBox(height: 6),
              Text(
                property.formattedPrice,
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  color: Colors.white,
                  fontWeight: FontWeight.w800,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _WorkspaceSummary extends StatelessWidget {
  const _WorkspaceSummary({required this.property});

  final Property property;

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: EdgeInsets.zero,
      elevation: 1,
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          children: [
            Row(
              children: [
                Expanded(
                  child: _WorkspaceMetric(
                    icon: Icons.bed_outlined,
                    value: property.bedrooms.toString(),
                    label: 'Bedrooms',
                  ),
                ),
                Expanded(
                  child: _WorkspaceMetric(
                    icon: Icons.bathtub_outlined,
                    value: property.bathrooms.toString(),
                    label: 'Bathrooms',
                  ),
                ),
                Expanded(
                  child: _WorkspaceMetric(
                    icon: Icons.photo_library_outlined,
                    value: property.photos.length.toString(),
                    label: 'Photos',
                  ),
                ),
              ],
            ),
            const Divider(height: 28),
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Icon(
                  Icons.location_on_outlined,
                  size: 20,
                  color: Colors.grey.shade700,
                ),
                const SizedBox(width: 7),
                Expanded(
                  child: Text(
                    property.locationLabel,
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _WorkspaceMetric extends StatelessWidget {
  const _WorkspaceMetric({
    required this.icon,
    required this.value,
    required this.label,
  });

  final IconData icon;
  final String value;
  final String label;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Icon(icon, color: Colors.green.shade800),
        const SizedBox(height: 7),
        Text(
          value,
          style: Theme.of(
            context,
          ).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w900),
        ),
        const SizedBox(height: 2),
        Text(
          label,
          style: Theme.of(
            context,
          ).textTheme.bodySmall?.copyWith(color: Colors.grey.shade700),
        ),
      ],
    );
  }
}

class _WorkspaceTile extends StatelessWidget {
  const _WorkspaceTile({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.onTap,
  });

  final IconData icon;
  final String title;
  final String subtitle;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: EdgeInsets.zero,
      elevation: 1,
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              CircleAvatar(
                backgroundColor: Colors.green.shade50,
                child: Icon(icon, color: Colors.green.shade800),
              ),
              const Spacer(),
              Text(
                title,
                style: Theme.of(
                  context,
                ).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w800),
              ),
              const SizedBox(height: 4),
              Text(
                subtitle,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: Theme.of(
                  context,
                ).textTheme.bodySmall?.copyWith(color: Colors.grey.shade700),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _PlannedWorkspaceOption extends StatelessWidget {
  const _PlannedWorkspaceOption({
    required this.icon,
    required this.title,
    required this.subtitle,
  });

  final IconData icon;
  final String title;
  final String subtitle;

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      elevation: 0,
      color: Colors.grey.shade100,
      child: ListTile(
        contentPadding: const EdgeInsets.symmetric(horizontal: 18, vertical: 7),
        leading: CircleAvatar(
          backgroundColor: Colors.grey.shade200,
          child: Icon(icon, color: Colors.grey.shade700),
        ),
        title: Text(title, style: const TextStyle(fontWeight: FontWeight.w800)),
        subtitle: Text(subtitle),
        trailing: Container(
          padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 5),
          decoration: BoxDecoration(
            color: Colors.grey.shade300,
            borderRadius: BorderRadius.circular(999),
          ),
          child: const Text(
            'Planned',
            style: TextStyle(fontSize: 11, fontWeight: FontWeight.w800),
          ),
        ),
      ),
    );
  }
}

class _DetailRow extends StatelessWidget {
  const _DetailRow({
    required this.icon,
    required this.label,
    required this.value,
  });

  final IconData icon;
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, size: 21, color: Colors.green.shade800),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  label,
                  style: Theme.of(
                    context,
                  ).textTheme.bodySmall?.copyWith(color: Colors.grey.shade700),
                ),
                const SizedBox(height: 3),
                Text(
                  value.trim().isEmpty ? 'Not provided' : value,
                  style: Theme.of(
                    context,
                  ).textTheme.bodyLarge?.copyWith(fontWeight: FontWeight.w700),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _PartnerPropertyPreviewScreen extends StatelessWidget {
  const _PartnerPropertyPreviewScreen({required this.property});

  final Property property;

  String? _imageUrl() {
    final coverPhoto = property.coverPhoto;

    if (coverPhoto == null || coverPhoto.image.trim().isEmpty) {
      return null;
    }

    final image = coverPhoto.image.trim();

    if (image.startsWith('http://') || image.startsWith('https://')) {
      return image;
    }

    if (image.startsWith('/')) {
      return '${PropertyService.baseUrl}$image';
    }

    return '${PropertyService.baseUrl}/$image';
  }

  @override
  Widget build(BuildContext context) {
    final imageUrl = _imageUrl();

    return Scaffold(
      backgroundColor: const Color(0xFFF6F8F6),
      appBar: AppBar(
        title: const Text('Listing Preview'),
        backgroundColor: Colors.white,
      ),
      body: ListView(
        padding: const EdgeInsets.only(bottom: 32),
        children: [
          SizedBox(
            height: 260,
            width: double.infinity,
            child: imageUrl == null
                ? const _PropertyImagePlaceholder()
                : Image.network(
                    imageUrl,
                    fit: BoxFit.cover,
                    errorBuilder: (context, error, stackTrace) {
                      return const _PropertyImagePlaceholder();
                    },
                  ),
          ),
          Padding(
            padding: const EdgeInsets.all(18),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _StatusBadge(status: property.status),
                const SizedBox(height: 14),
                Text(
                  property.title,
                  style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                    fontWeight: FontWeight.w900,
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  property.formattedPrice,
                  style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    color: Colors.green.shade800,
                    fontWeight: FontWeight.w900,
                  ),
                ),
                const SizedBox(height: 10),
                Text(
                  '${property.formattedPropertyType} • '
                  '${property.formattedListingType}',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: 10),
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Icon(
                      Icons.location_on_outlined,
                      size: 20,
                      color: Colors.grey.shade700,
                    ),
                    const SizedBox(width: 6),
                    Expanded(child: Text(property.locationLabel)),
                  ],
                ),
                const SizedBox(height: 20),
                Wrap(
                  spacing: 12,
                  runSpacing: 10,
                  children: [
                    Chip(
                      avatar: const Icon(Icons.bed_outlined, size: 18),
                      label: Text('${property.bedrooms} bedrooms'),
                    ),
                    Chip(
                      avatar: const Icon(Icons.bathtub_outlined, size: 18),
                      label: Text('${property.bathrooms} bathrooms'),
                    ),
                    Chip(
                      avatar: const Icon(
                        Icons.photo_library_outlined,
                        size: 18,
                      ),
                      label: Text('${property.photos.length} photos'),
                    ),
                  ],
                ),
                const SizedBox(height: 24),
                Text(
                  'Description',
                  style: Theme.of(
                    context,
                  ).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w800),
                ),
                const SizedBox(height: 10),
                Text(
                  property.description.trim().isEmpty
                      ? 'No description has been provided.'
                      : property.description,
                  style: Theme.of(
                    context,
                  ).textTheme.bodyLarge?.copyWith(height: 1.5),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

String _statusLabel(String status) {
  switch (status.trim().toLowerCase()) {
    case 'draft':
      return 'Draft';
    case 'pending':
      return 'Pending verification';
    case 'published':
      return 'Published';
    case 'reserved':
      return 'Reserved';
    case 'rented':
      return 'Rented';
    case 'sold':
      return 'Sold';
    case 'archived':
      return 'Archived';
    default:
      return status.trim().isEmpty ? 'Unknown' : status;
  }
}
