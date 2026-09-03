import 'package:flutter/material.dart';
import '../models/property.dart';
import '../services/property_service.dart';
import 'request_viewing_screen.dart';
import 'property_video_screen.dart';
import '../widgets/pata_hao_network_image.dart';
import 'package:mobile/screens/login_screen.dart';
import 'package:mobile/services/auth_service.dart';
import 'package:mobile/screens/add_phone_number_screen.dart';
import 'package:mobile/screens/property_photo_viewer_screen.dart';

class PropertyDetailScreen extends StatelessWidget {
  final Property property;

  const PropertyDetailScreen({super.key, required this.property});

  String get formattedPrice {
    final amount = double.tryParse(property.price);

    final formattedAmount = amount == null
        ? property.price
        : amount
              .toStringAsFixed(0)
              .replaceAllMapped(
                RegExp(r'\B(?=(\d{3})+(?!\d))'),
                (match) => ',',
              );

    if (property.listingType.trim().toLowerCase() == 'rent') {
      return 'KES $formattedAmount / month';
    }

    return 'KES $formattedAmount';
  }

  int get viewingFee {
    return property.listingType.trim().toLowerCase() == 'sale' ? 2000 : 400;
  }

  String get formattedViewingFee {
    return viewingFee.toString().replaceAllMapped(
      RegExp(r'\B(?=(\d{3})+(?!\d))'),
      (match) => ',',
    );
  }

  String get location {
    return [
      property.estate,
      property.town,
      property.county,
    ].where((value) => value.trim().isNotEmpty).join(', ');
  }

  String get propertyType {
    if (property.propertyType.isEmpty) {
      return 'Property';
    }

    return property.propertyType
        .split('_')
        .map(
          (word) => word.isEmpty
              ? ''
              : '${word[0].toUpperCase()}${word.substring(1)}',
        )
        .join(' ');
  }

  String _mediaUrl(String path) {
    if (path.startsWith('http://') || path.startsWith('https://')) {
      return path;
    }

    if (path.startsWith('/')) {
      return '${PropertyService.baseUrl}$path';
    }

    return '${PropertyService.baseUrl}/$path';
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.white,
      appBar: AppBar(
        title: const Text('Property Details'),
        backgroundColor: const Color(0xFF14532D),
        foregroundColor: Colors.white,
      ),
      body: SafeArea(
        child: Column(
          children: [
            Expanded(
              child: SingleChildScrollView(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _buildPhotoGallery(context),
                    Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          if (property.isSuccessBroadcastActive) ...[
                            _buildSuccessBroadcastBanner(),
                            const SizedBox(height: 18),
                          ],
                          Text(
                            property.title,
                            style: const TextStyle(
                              fontSize: 24,
                              fontWeight: FontWeight.bold,
                              color: Color(0xFF111827),
                            ),
                          ),
                          const SizedBox(height: 8),
                          Text(
                            formattedPrice,
                            style: const TextStyle(
                              fontSize: 21,
                              fontWeight: FontWeight.bold,
                              color: Color(0xFF14532D),
                            ),
                          ),
                          const SizedBox(height: 10),
                          Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const Icon(
                                Icons.location_on_outlined,
                                color: Colors.black54,
                                size: 21,
                              ),
                              const SizedBox(width: 6),
                              Expanded(
                                child: Text(
                                  location.isEmpty
                                      ? 'Location not provided'
                                      : location,
                                  style: const TextStyle(
                                    fontSize: 15,
                                    color: Colors.black54,
                                  ),
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 22),
                          Row(
                            children: [
                              Expanded(
                                child: _DetailBox(
                                  icon: Icons.home_outlined,
                                  label: propertyType,
                                ),
                              ),
                              const SizedBox(width: 12),
                              Expanded(
                                child: _DetailBox(
                                  icon: property.listingType == 'rent'
                                      ? Icons.key_outlined
                                      : Icons.sell_outlined,
                                  label: property.listingType == 'rent'
                                      ? 'For Rent'
                                      : 'For Sale',
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 24),

                          if (property.amenities.isNotEmpty) ...[
                            _buildAmenitiesSection(),
                            const SizedBox(height: 24),
                          ],

                          const Text(
                            'About this property',
                            style: TextStyle(
                              fontSize: 19,
                              fontWeight: FontWeight.bold,
                              color: Color(0xFF111827),
                            ),
                          ),
                          const SizedBox(height: 10),
                          Text(
                            property.isCompletedTransaction
                                ? ('This successful transaction '
                                      'was completed through Pata Hao.')
                                : ('Contact the property partner '
                                      'and request a viewing to receive '
                                      'more information about this '
                                      'property.'),
                            style: const TextStyle(
                              fontSize: 15,
                              height: 1.5,
                              color: Colors.black87,
                            ),
                          ),
                          const SizedBox(height: 24),
                          if (property.partner != null) ...[
                            _buildPartnerSection(),
                            const SizedBox(height: 24),
                          ],
                          Container(
                            width: double.infinity,
                            padding: const EdgeInsets.all(16),
                            decoration: BoxDecoration(
                              color: const Color(0xFFF0FDF4),
                              borderRadius: BorderRadius.circular(14),
                              border: Border.all(
                                color: const Color(0xFFBBF7D0),
                              ),
                            ),
                            child: Row(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Icon(
                                  Icons.verified_user_outlined,
                                  color: Color(0xFF14532D),
                                ),
                                SizedBox(width: 12),
                                Expanded(
                                  child: Text(
                                    property.isCompletedTransaction
                                        ? ('Pata Hao verified this '
                                              'completed transaction. '
                                              'The property is no longer '
                                              'accepting viewing requests.')
                                        : ('Viewing requests are '
                                              'managed through Pata Hao. '
                                              'The viewing commitment fee '
                                              'is KES '
                                              '$formattedViewingFee, '
                                              'no cash and must be paid '
                                              'in the app.'),
                                    style: const TextStyle(
                                      fontSize: 14,
                                      height: 1.4,
                                      color: Color(0xFF14532D),
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          ),
                          const SizedBox(height: 24),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),
            _buildRequestViewingButton(context),
          ],
        ),
      ),
    );
  }

  void _openPhotoViewer(BuildContext context, int photoIndex) {
    final imageUrls = property.photos
        .map((photo) => _mediaUrl(photo.image))
        .toList();

    if (imageUrls.isEmpty) {
      return;
    }

    final safeIndex = photoIndex.clamp(0, imageUrls.length - 1);

    Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) {
          return PropertyPhotoViewerScreen(
            imageUrls: imageUrls,
            initialIndex: safeIndex,
            title: property.title,
          );
        },
      ),
    );
  }

  Widget _buildPhotoGallery(BuildContext context) {
    PropertyVideo? video;

    for (final item in property.videos) {
      if (item.video.trim().isNotEmpty) {
        video = item;
        break;
      }
    }

    final hasVideo = video != null;

    final totalMediaItems = property.photos.length + (hasVideo ? 1 : 0);

    if (totalMediaItems == 0) {
      return Container(
        height: 260,
        width: double.infinity,
        color: const Color(0xFFE5E7EB),
        child: const Center(
          child: Icon(
            Icons.home_work_outlined,
            size: 90,
            color: Colors.black38,
          ),
        ),
      );
    }

    return SizedBox(
      height: 260,
      width: double.infinity,
      child: PageView.builder(
        itemCount: totalMediaItems,
        itemBuilder: (context, index) {
          if (hasVideo && index == 0) {
            final currentVideo = video!;

            final videoUrl = _mediaUrl(currentVideo.video);

            final thumbnailUrl = currentVideo.thumbnail.trim().isNotEmpty
                ? _mediaUrl(currentVideo.thumbnail)
                : property.coverPhoto != null
                ? _mediaUrl(property.coverPhoto!.image)
                : '';

            return Stack(
              fit: StackFit.expand,
              children: [
                PataHaoNetworkImage(
                  imageUrl: thumbnailUrl,
                  width: double.infinity,
                  height: 260,
                  fit: BoxFit.cover,
                  cacheWidth: 1400,
                ),
                Material(
                  color: Colors.transparent,
                  child: InkWell(
                    onTap: () {
                      Navigator.of(context).push(
                        MaterialPageRoute<void>(
                          builder: (_) {
                            return PropertyVideoScreen(
                              videoUrl: videoUrl,
                              title: currentVideo.title.trim().isEmpty
                                  ? property.title
                                  : currentVideo.title,
                            );
                          },
                        ),
                      );
                    },
                    child: const Center(
                      child: CircleAvatar(
                        radius: 38,
                        backgroundColor: Colors.black54,
                        child: Icon(
                          Icons.play_arrow_rounded,
                          size: 56,
                          color: Colors.white,
                        ),
                      ),
                    ),
                  ),
                ),
                Positioned(
                  left: 14,
                  bottom: 14,
                  child: Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 11,
                      vertical: 7,
                    ),
                    decoration: BoxDecoration(
                      color: Colors.black54,
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: const Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(
                          Icons.videocam_rounded,
                          size: 17,
                          color: Colors.white,
                        ),
                        SizedBox(width: 6),
                        Text(
                          'Play property video',
                          style: TextStyle(
                            color: Colors.white,
                            fontSize: 13,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
                if (totalMediaItems > 1)
                  Positioned(
                    right: 14,
                    bottom: 14,
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 10,
                        vertical: 7,
                      ),
                      decoration: BoxDecoration(
                        color: Colors.black54,
                        borderRadius: BorderRadius.circular(20),
                      ),
                      child: Text(
                        '1 of $totalMediaItems',
                        style: const TextStyle(
                          color: Colors.white,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ),
                  ),
              ],
            );
          }

          final photoIndex = hasVideo ? index - 1 : index;

          final photo = property.photos[photoIndex];

          return Stack(
            fit: StackFit.expand,
            children: [
              Material(
                color: Colors.transparent,
                child: InkWell(
                  onTap: () {
                    _openPhotoViewer(context, photoIndex);
                  },
                  child: PataHaoNetworkImage(
                    imageUrl: _mediaUrl(photo.image),
                    width: double.infinity,
                    height: 260,
                    fit: BoxFit.cover,
                    cacheWidth: 1400,
                  ),
                ),
              ),

              Positioned(
                left: 14,
                bottom: 14,
                child: IgnorePointer(
                  child: Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 10,
                      vertical: 7,
                    ),
                    decoration: BoxDecoration(
                      color: Colors.black54,
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: const Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(
                          Icons.zoom_in_outlined,
                          color: Colors.white,
                          size: 17,
                        ),
                        SizedBox(width: 5),
                        Text(
                          'Tap to view',
                          style: TextStyle(
                            color: Colors.white,
                            fontSize: 12,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),

              if (totalMediaItems > 1)
                Positioned(
                  right: 14,
                  bottom: 14,
                  child: IgnorePointer(
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 10,
                        vertical: 7,
                      ),
                      decoration: BoxDecoration(
                        color: Colors.black54,
                        borderRadius: BorderRadius.circular(20),
                      ),
                      child: Text(
                        '${index + 1} of '
                        '$totalMediaItems',
                        style: const TextStyle(
                          color: Colors.white,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ),
                  ),
                ),
            ],
          );
        },
      ),
    );
  }

  Widget _buildAmenitiesSection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Amenities',
          style: TextStyle(
            fontSize: 19,
            fontWeight: FontWeight.bold,
            color: Color(0xFF111827),
          ),
        ),
        const SizedBox(height: 12),
        Wrap(
          spacing: 10,
          runSpacing: 10,
          children: property.amenities.map((amenity) {
            return Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
              decoration: BoxDecoration(
                color: const Color(0xFFF0FDF4),
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: const Color(0xFFBBF7D0)),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Icon(
                    Icons.check_circle_outline,
                    size: 18,
                    color: Color(0xFF15803D),
                  ),
                  const SizedBox(width: 7),
                  Text(
                    amenity.name,
                    style: const TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w600,
                      color: Color(0xFF14532D),
                    ),
                  ),
                ],
              ),
            );
          }).toList(),
        ),
      ],
    );
  }

  Widget _buildPartnerSection() {
    final partner = property.partner;

    if (partner == null) {
      return const SizedBox.shrink();
    }

    final displayName = partner.businessName.trim().isNotEmpty
        ? partner.businessName
        : partner.name.trim().isNotEmpty
        ? partner.name
        : 'Pata Hao Partner';

    final partnerLocation = [
      partner.town,
      partner.county,
    ].where((value) => value.trim().isNotEmpty).join(', ');

    final profilePhoto = partner.profilePhoto?.trim();
    final hasProfilePhoto = profilePhoto != null && profilePhoto.isNotEmpty;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Property Partner',
          style: TextStyle(
            fontSize: 19,
            fontWeight: FontWeight.bold,
            color: Color(0xFF111827),
          ),
        ),
        const SizedBox(height: 12),
        Container(
          width: double.infinity,
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: const Color(0xFFE5E7EB)),
            boxShadow: const [
              BoxShadow(
                color: Color(0x0D000000),
                blurRadius: 8,
                offset: Offset(0, 3),
              ),
            ],
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                crossAxisAlignment: CrossAxisAlignment.center,
                children: [
                  CircleAvatar(
                    radius: 34,
                    backgroundColor: const Color(0xFFE5E7EB),
                    backgroundImage: hasProfilePhoto
                        ? NetworkImage(_mediaUrl(profilePhoto))
                        : null,
                    child: hasProfilePhoto
                        ? null
                        : const Icon(
                            Icons.person_outline,
                            size: 38,
                            color: Colors.black38,
                          ),
                  ),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Flexible(
                              child: Text(
                                displayName,
                                style: const TextStyle(
                                  fontSize: 17,
                                  fontWeight: FontWeight.bold,
                                  color: Color(0xFF111827),
                                ),
                              ),
                            ),
                            if (partner.isVerified) ...[
                              const SizedBox(width: 6),
                              const Icon(
                                Icons.verified,
                                size: 20,
                                color: Color(0xFF15803D),
                              ),
                            ],
                          ],
                        ),
                        if (partner.name.trim().isNotEmpty &&
                            partner.name != displayName) ...[
                          const SizedBox(height: 3),
                          Text(
                            partner.name,
                            style: const TextStyle(
                              fontSize: 14,
                              color: Colors.black54,
                            ),
                          ),
                        ],
                        if (partnerLocation.isNotEmpty) ...[
                          const SizedBox(height: 5),
                          Row(
                            children: [
                              const Icon(
                                Icons.location_on_outlined,
                                size: 17,
                                color: Colors.black54,
                              ),
                              const SizedBox(width: 4),
                              Expanded(
                                child: Text(
                                  partnerLocation,
                                  style: const TextStyle(
                                    fontSize: 13,
                                    color: Colors.black54,
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ],
                      ],
                    ),
                  ),
                ],
              ),
              if (partner.serviceArea?.trim().isNotEmpty == true) ...[
                const SizedBox(height: 14),
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Icon(
                      Icons.map_outlined,
                      size: 19,
                      color: Color(0xFF14532D),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        'Service area: ${partner.serviceArea}',
                        style: const TextStyle(
                          fontSize: 14,
                          color: Colors.black87,
                        ),
                      ),
                    ),
                  ],
                ),
              ],
              if (partner.bio?.trim().isNotEmpty == true) ...[
                const SizedBox(height: 14),
                Text(
                  partner.bio!,
                  style: const TextStyle(
                    fontSize: 14,
                    height: 1.45,
                    color: Colors.black87,
                  ),
                ),
              ],
              const SizedBox(height: 14),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: const Color(0xFFF9FAFB),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: const Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Icon(
                      Icons.support_agent_outlined,
                      size: 21,
                      color: Color(0xFF14532D),
                    ),
                    SizedBox(width: 9),
                    Expanded(
                      child: Text(
                        'This partner manages the property and coordinates '
                        'viewings. All viewing requests and payments must '
                        'remain inside Pata Hao no cash transactions.',
                        style: TextStyle(
                          fontSize: 13,
                          height: 1.4,
                          color: Color(0xFF374151),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildSuccessBroadcastBanner() {
    final isSold = property.status.trim().toLowerCase() == 'sold';

    final accentColor = isSold
        ? const Color(0xFFB91C1C)
        : const Color(0xFFD97706);

    final backgroundColor = isSold
        ? const Color(0xFFFEF2F2)
        : const Color(0xFFFFFBEB);

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: backgroundColor,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: accentColor.withValues(alpha: 0.35)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          CircleAvatar(
            backgroundColor: accentColor,
            foregroundColor: Colors.white,
            child: Icon(isSold ? Icons.sell_outlined : Icons.key_outlined),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  property.successDisplayLabel,
                  style: TextStyle(
                    color: accentColor,
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 5),
                const Text(
                  'Verified transaction completed through '
                  'Pata Hao.',
                  style: TextStyle(color: Color(0xFF374151), height: 1.35),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildRequestViewingButton(BuildContext context) {
    if (property.isCompletedTransaction) {
      final isSold = property.status.trim().toLowerCase() == 'sold';

      final accentColor = isSold
          ? const Color(0xFFB91C1C)
          : const Color(0xFFD97706);

      return Container(
        width: double.infinity,
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 16),
        decoration: const BoxDecoration(
          color: Colors.white,
          boxShadow: [
            BoxShadow(
              color: Color(0x1A000000),
              blurRadius: 10,
              offset: Offset(0, -2),
            ),
          ],
        ),
        child: Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: accentColor.withValues(alpha: 0.08),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: accentColor.withValues(alpha: 0.30)),
          ),
          child: Row(
            children: [
              Icon(Icons.verified_outlined, color: accentColor),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      property.successDisplayLabel,
                      style: TextStyle(
                        color: accentColor,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 3),
                    Text(
                      isSold
                          ? ('This property has been sold '
                                'and is no longer available.')
                          : ('This property has been rented '
                                'and is no longer available.'),
                      style: const TextStyle(
                        color: Color(0xFF4B5563),
                        fontSize: 13,
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
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 16),
      decoration: const BoxDecoration(
        color: Colors.white,
        boxShadow: [
          BoxShadow(
            color: Color(0x1A000000),
            blurRadius: 10,
            offset: Offset(0, -2),
          ),
        ],
      ),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                const Text(
                  'Viewing fee',
                  style: TextStyle(fontSize: 12, color: Colors.black54),
                ),
                const SizedBox(height: 2),
                Text(
                  'KES $formattedViewingFee',
                  style: const TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                    color: Color(0xFF14532D),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: 12),
          ElevatedButton.icon(
            onPressed: () async {
              final isLoggedIn = await AuthService.instance.isLoggedIn();

              if (!context.mounted) {
                return;
              }

              Future<void> continueToViewing() async {
                try {
                  final user = await AuthService.instance.getCurrentUser();

                  if (!context.mounted) {
                    return;
                  }

                  if (user.phoneNumber.trim().isEmpty) {
                    final updatedUser = await Navigator.of(context)
                        .push<AuthUser>(
                          MaterialPageRoute<AuthUser>(
                            builder: (_) => const AddPhoneNumberScreen(),
                          ),
                        );

                    if (!context.mounted) {
                      return;
                    }

                    if (updatedUser == null ||
                        updatedUser.phoneNumber.trim().isEmpty) {
                      return;
                    }
                  }

                  if (!context.mounted) {
                    return;
                  }

                  Navigator.of(context).push(
                    MaterialPageRoute<void>(
                      builder: (_) => RequestViewingScreen(property: property),
                    ),
                  );
                } catch (error) {
                  if (!context.mounted) {
                    return;
                  }

                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(
                      content: Text(
                        error.toString().replaceFirst('Exception: ', ''),
                      ),
                    ),
                  );
                }
              }

              if (isLoggedIn) {
                await continueToViewing();
                return;
              }

              Navigator.of(context).push(
                MaterialPageRoute<void>(
                  builder: (_) => LoginScreen(
                    onLoginSuccess: () async {
                      Navigator.of(context).pop();

                      await continueToViewing();
                    },
                  ),
                ),
              );
            },
            icon: const Icon(Icons.calendar_month_outlined),
            label: const Text('Request Viewing'),
            style: ElevatedButton.styleFrom(
              backgroundColor: const Color(0xFF14532D),
              foregroundColor: Colors.white,
              minimumSize: const Size(0, 54),
              padding: const EdgeInsets.symmetric(horizontal: 18),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(12),
              ),
              textStyle: const TextStyle(
                fontSize: 15,
                fontWeight: FontWeight.bold,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _DetailBox extends StatelessWidget {
  final IconData icon;
  final String label;

  const _DetailBox({required this.icon, required this.label});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 14),
      decoration: BoxDecoration(
        color: const Color(0xFFF3F4F6),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        children: [
          Icon(icon, color: const Color(0xFF14532D)),
          const SizedBox(height: 8),
          Text(
            label,
            textAlign: TextAlign.center,
            style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600),
          ),
        ],
      ),
    );
  }
}
