import 'package:flutter/material.dart';

import '../models/favorite.dart';
import '../models/property.dart';
import '../services/favorite_service.dart';
import '../services/property_service.dart';
import '../widgets/pata_hao_network_image.dart';
import 'property_detail_screen.dart';

class SavedPropertiesScreen extends StatefulWidget {
  const SavedPropertiesScreen({super.key});

  @override
  State<SavedPropertiesScreen> createState() =>
      _SavedPropertiesScreenState();
}

class _SavedPropertiesScreenState
    extends State<SavedPropertiesScreen> {
  late Future<List<Favorite>> _favoritesFuture;

  final Set<int> _removingFavoriteIds = <int>{};

  @override
  void initState() {
    super.initState();
    _loadFavorites();
  }

  void _loadFavorites() {
    _favoritesFuture =
        FavoriteService.instance.fetchFavorites();
  }

  Future<void> _refreshFavorites() async {
    setState(_loadFavorites);
    await _favoritesFuture;
  }

  String _cleanError(Object error) {
    return error
        .toString()
        .replaceFirst('Exception: ', '')
        .trim();
  }

  String? _propertyMediaUrl(Property property) {
    final media = property.coverMediaUrl?.trim() ?? '';

    if (media.isEmpty) {
      return null;
    }

    if (media.startsWith('http://') ||
        media.startsWith('https://')) {
      return media;
    }

    if (media.startsWith('/')) {
      return '${PropertyService.baseUrl}$media';
    }

    return '${PropertyService.baseUrl}/$media';
  }

  Future<void> _openProperty(
    Property property,
  ) async {
    await Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) =>
            PropertyDetailScreen(property: property),
      ),
    );

    if (!mounted) {
      return;
    }

    await _refreshFavorites();
  }

  Future<void> _removeFavorite(
    Favorite favorite,
  ) async {
    if (_removingFavoriteIds.contains(favorite.id)) {
      return;
    }

    setState(() {
      _removingFavoriteIds.add(favorite.id);
    });

    try {
      await FavoriteService.instance.removeFavorite(
        favoriteId: favorite.id,
      );

      if (!mounted) {
        return;
      }

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            '${favorite.property.title} removed from saved properties.',
          ),
        ),
      );

      await _refreshFavorites();
    } catch (error) {
      if (!mounted) {
        return;
      }

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(_cleanError(error)),
        ),
      );
    } finally {
      if (mounted) {
        setState(() {
          _removingFavoriteIds.remove(favorite.id);
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF6F8F6),
      appBar: AppBar(
        title: const Text('Saved Properties'),
        backgroundColor: const Color(0xFF14532D),
        foregroundColor: Colors.white,
      ),
      body: FutureBuilder<List<Favorite>>(
        future: _favoritesFuture,
        builder: (context, snapshot) {
          if (snapshot.connectionState ==
              ConnectionState.waiting) {
            return const Center(
              child: CircularProgressIndicator(),
            );
          }

          if (snapshot.hasError) {
            return RefreshIndicator(
              onRefresh: _refreshFavorites,
              child: ListView(
                physics:
                    const AlwaysScrollableScrollPhysics(),
                padding: const EdgeInsets.all(24),
                children: [
                  const SizedBox(height: 100),
                  const Icon(
                    Icons.cloud_off_outlined,
                    size: 68,
                    color: Colors.black38,
                  ),
                  const SizedBox(height: 18),
                  const Text(
                    'Could not load saved properties',
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      fontSize: 21,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: 10),
                  Text(
                    _cleanError(snapshot.error!),
                    textAlign: TextAlign.center,
                    style: const TextStyle(
                      color: Colors.black54,
                    ),
                  ),
                  const SizedBox(height: 22),
                  Center(
                    child: FilledButton.icon(
                      onPressed: () {
                        setState(_loadFavorites);
                      },
                      icon: const Icon(Icons.refresh),
                      label: const Text('Try Again'),
                    ),
                  ),
                ],
              ),
            );
          }

          final favorites =
              snapshot.data ?? <Favorite>[];

          if (favorites.isEmpty) {
            return RefreshIndicator(
              onRefresh: _refreshFavorites,
              child: ListView(
                physics:
                    const AlwaysScrollableScrollPhysics(),
                padding: const EdgeInsets.all(24),
                children: const [
                  SizedBox(height: 110),
                  Icon(
                    Icons.favorite_border_rounded,
                    size: 76,
                    color: Color(0xFF34AD2C),
                  ),
                  SizedBox(height: 18),
                  Text(
                    'No saved properties yet',
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      fontSize: 22,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  SizedBox(height: 10),
                  Text(
                    'Tap the heart on any property to save it here '
                    'for comparison later.',
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      fontSize: 15,
                      height: 1.5,
                      color: Colors.black54,
                    ),
                  ),
                ],
              ),
            );
          }

          return RefreshIndicator(
            onRefresh: _refreshFavorites,
            child: ListView.builder(
              physics:
                  const AlwaysScrollableScrollPhysics(),
              padding: const EdgeInsets.fromLTRB(
                16,
                16,
                16,
                32,
              ),
              itemCount: favorites.length,
              itemBuilder: (context, index) {
                final favorite = favorites[index];
                final property = favorite.property;

                return _SavedPropertyCard(
                  favorite: favorite,
                  mediaUrl:
                      _propertyMediaUrl(property),
                  isRemoving:
                      _removingFavoriteIds.contains(
                    favorite.id,
                  ),
                  onOpen: () =>
                      _openProperty(property),
                  onRemove: () =>
                      _removeFavorite(favorite),
                );
              },
            ),
          );
        },
      ),
    );
  }
}

class _SavedPropertyCard extends StatelessWidget {
  const _SavedPropertyCard({
    required this.favorite,
    required this.mediaUrl,
    required this.isRemoving,
    required this.onOpen,
    required this.onRemove,
  });

  final Favorite favorite;
  final String? mediaUrl;
  final bool isRemoving;
  final VoidCallback onOpen;
  final VoidCallback onRemove;

  @override
  Widget build(BuildContext context) {
    final property = favorite.property;

    return Card(
      margin: const EdgeInsets.only(bottom: 18),
      clipBehavior: Clip.antiAlias,
      elevation: 2,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(18),
      ),
      child: InkWell(
        onTap: onOpen,
        child: Column(
          crossAxisAlignment:
              CrossAxisAlignment.start,
          children: [
            Stack(
              children: [
                PataHaoNetworkImage(
                  imageUrl: mediaUrl,
                  width: double.infinity,
                  height: 210,
                  fit: BoxFit.cover,
                  cacheWidth: 900,
                ),
                Positioned(
                  top: 12,
                  left: 12,
                  child: Container(
                    padding:
                        const EdgeInsets.symmetric(
                      horizontal: 10,
                      vertical: 6,
                    ),
                    decoration: BoxDecoration(
                      color: const Color(0xFF34AD2C),
                      borderRadius:
                          BorderRadius.circular(20),
                    ),
                    child: Text(
                      property.listingType == 'rent'
                          ? 'For Rent'
                          : 'For Sale',
                      style: const TextStyle(
                        color: Colors.white,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                ),
                Positioned(
                  top: 12,
                  right: 12,
                  child: CircleAvatar(
                    backgroundColor: Colors.white,
                    child: IconButton(
                      tooltip: 'Remove from saved',
                      onPressed:
                          isRemoving ? null : onRemove,
                      icon: isRemoving
                          ? const SizedBox(
                              width: 20,
                              height: 20,
                              child:
                                  CircularProgressIndicator(
                                strokeWidth: 2,
                              ),
                            )
                          : const Icon(
                              Icons.favorite_rounded,
                              color: Colors.red,
                            ),
                    ),
                  ),
                ),
              ],
            ),
            Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment:
                    CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          property.title,
                          style: const TextStyle(
                            fontSize: 20,
                            fontWeight:
                                FontWeight.bold,
                            color: Color(0xFF111827),
                          ),
                        ),
                      ),
                      if (property.isVerified)
                        const Icon(
                          Icons.verified,
                          color: Color(0xFF34AD2C),
                        ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Row(
                    crossAxisAlignment:
                        CrossAxisAlignment.start,
                    children: [
                      const Icon(
                        Icons.location_on_outlined,
                        size: 18,
                        color: Colors.black54,
                      ),
                      const SizedBox(width: 5),
                      Expanded(
                        child: Text(
                          property.locationLabel,
                          style: const TextStyle(
                            color: Colors.black54,
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 14),
                  Wrap(
                    spacing: 18,
                    runSpacing: 8,
                    children: [
                      _SavedPropertyMetric(
                        icon: Icons.bed_outlined,
                        label:
                            '${property.bedrooms} beds',
                      ),
                      _SavedPropertyMetric(
                        icon:
                            Icons.bathtub_outlined,
                        label:
                            '${property.bathrooms} baths',
                      ),
                      if (property.hasVideoThumbnail)
                        const _SavedPropertyMetric(
                          icon:
                              Icons.videocam_outlined,
                          label: 'Video',
                        ),
                    ],
                  ),
                  const SizedBox(height: 16),
                  Text(
                    property.formattedPrice,
                    style: const TextStyle(
                      fontSize: 20,
                      fontWeight: FontWeight.bold,
                      color: Color(0xFF14532D),
                    ),
                  ),
                  const SizedBox(height: 16),
                  SizedBox(
                    width: double.infinity,
                    child: OutlinedButton.icon(
                      onPressed: onOpen,
                      icon: const Icon(
                        Icons.visibility_outlined,
                      ),
                      label:
                          const Text('View Property'),
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

class _SavedPropertyMetric
    extends StatelessWidget {
  const _SavedPropertyMetric({
    required this.icon,
    required this.label,
  });

  final IconData icon;
  final String label;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(
          icon,
          size: 19,
          color: Colors.black54,
        ),
        const SizedBox(width: 5),
        Text(
          label,
          style: const TextStyle(
            color: Colors.black87,
          ),
        ),
      ],
    );
  }
}