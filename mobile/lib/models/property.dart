import 'partner.dart';

class PropertyAmenity {
  final int id;
  final String name;
  final String slug;
  final String icon;
  final int displayOrder;

  const PropertyAmenity({
    required this.id,
    required this.name,
    required this.slug,
    required this.icon,
    required this.displayOrder,
  });

  factory PropertyAmenity.fromJson(Map<String, dynamic> json) {
    return PropertyAmenity(
      id: Property._toInt(json['id']),
      name: json['name']?.toString() ?? '',
      slug: json['slug']?.toString() ?? '',
      icon: json['icon']?.toString() ?? '',
      displayOrder: Property._toInt(json['display_order']),
    );
  }
}

class PropertyPhoto {
  final int id;
  final String image;
  final String caption;
  final bool isCover;

  const PropertyPhoto({
    required this.id,
    required this.image,
    required this.caption,
    required this.isCover,
  });

  factory PropertyPhoto.fromJson(Map<String, dynamic> json) {
    final absoluteImageUrl = json['image_url']?.toString() ?? '';
    final fallbackImage = json['image']?.toString() ?? '';

    return PropertyPhoto(
      id: Property._toInt(json['id']),
      image: absoluteImageUrl.trim().isNotEmpty
          ? absoluteImageUrl
          : fallbackImage,
      caption: json['caption']?.toString() ?? '',
      isCover: json['is_cover'] == true,
    );
  }
}

class PropertyVideo {
  final int id;
  final String video;
  final String thumbnail;
  final String title;
  final String description;
  final int duration;
  final bool isFeatured;

  const PropertyVideo({
    required this.id,
    required this.video,
    required this.thumbnail,
    required this.title,
    required this.description,
    required this.duration,
    required this.isFeatured,
  });

  factory PropertyVideo.fromJson(Map<String, dynamic> json) {
    final absoluteVideoUrl = json['video_url']?.toString() ?? '';
    final fallbackVideo = json['video']?.toString() ?? '';
    final absoluteThumbnailUrl = json['thumbnail_url']?.toString() ?? '';
    final fallbackThumbnail = json['thumbnail']?.toString() ?? '';

    return PropertyVideo(
      id: Property._toInt(json['id']),
      video: absoluteVideoUrl.trim().isNotEmpty
          ? absoluteVideoUrl
          : fallbackVideo,
      thumbnail: absoluteThumbnailUrl.trim().isNotEmpty
          ? absoluteThumbnailUrl
          : fallbackThumbnail,
      title: json['title']?.toString() ?? '',
      description: json['description']?.toString() ?? '',
      duration: Property._toInt(json['duration']),
      isFeatured: json['is_featured'] == true,
    );
  }
}

class Property {
  final int id;
  final String title;
  final Partner? partner;
  final String propertyType;
  final String listingType;
  final String price;
  final String county;
  final String town;
  final String estate;
  final int bedrooms;
  final int bathrooms;
  final String description;
  final String status;
  final String verificationReturnReason;
  final String trustBadge;
  final bool isFavorite;
  final int? favoriteId;
  final List<PropertyPhoto> photos;
  final List<PropertyVideo> videos;
  final List<PropertyAmenity> amenities;

  const Property({
    required this.id,
    required this.title,
    required this.partner,
    required this.propertyType,
    required this.listingType,
    required this.price,
    required this.county,
    required this.town,
    required this.estate,
    required this.bedrooms,
    required this.bathrooms,
    required this.description,
    required this.verificationReturnReason,
    required this.status,
    required this.trustBadge,
    required this.isFavorite,
    required this.favoriteId,
    required this.photos,
    required this.videos,
    required this.amenities,
  });

  factory Property.fromJson(Map<String, dynamic> json) {
    final rawPhotos = json['photos'];
    final rawVideos = json['videos'];
    final rawAmenities = json['amenities'];
    final rawPartner = json['partner'];

    return Property(
      id: _toInt(json['id']),
      title: json['title']?.toString() ?? 'Untitled property',
      partner: rawPartner is Map<String, dynamic>
          ? Partner.fromJson(rawPartner)
          : rawPartner is Map
          ? Partner.fromJson(Map<String, dynamic>.from(rawPartner))
          : null,
      propertyType: json['property_type']?.toString() ?? '',
      listingType: json['listing_type']?.toString() ?? '',
      price: json['price']?.toString() ?? '0',
      county: json['county']?.toString() ?? '',
      town: json['town']?.toString() ?? '',
      estate: json['estate']?.toString() ?? '',
      bedrooms: _toInt(json['bedrooms']),
      bathrooms: _toInt(json['bathrooms']),
      description: json['description']?.toString() ?? '',
      status: json['status']?.toString() ?? '',
      verificationReturnReason: json['verification_return_reason']?.toString() ?? '',
      trustBadge: json['trust_badge']?.toString() ?? 'none',
      isFavorite: json['is_favorite'] == true,
      favoriteId: json['favorite_id'] == null
          ? null
          : _toInt(json['favorite_id']),
      photos: rawPhotos is List
          ? rawPhotos
                .whereType<Map>()
                .map(
                  (item) =>
                      PropertyPhoto.fromJson(Map<String, dynamic>.from(item)),
                )
                .toList()
          : [],
      videos: rawVideos is List
          ? rawVideos
                .whereType<Map>()
                .map(
                  (item) =>
                      PropertyVideo.fromJson(Map<String, dynamic>.from(item)),
                )
                .toList()
          : [],
      amenities: rawAmenities is List
          ? rawAmenities
                .whereType<Map>()
                .map(
                  (item) =>
                      PropertyAmenity.fromJson(Map<String, dynamic>.from(item)),
                )
                .toList()
          : [],
    );
  }

  String get formattedPropertyType {
    if (propertyType.trim().isEmpty) {
      return 'Property';
    }

    return propertyType
        .replaceAll('_', ' ')
        .split(' ')
        .where((word) => word.isNotEmpty)
        .map(
          (word) =>
              '${word[0].toUpperCase()}'
              '${word.substring(1).toLowerCase()}',
        )
        .join(' ');
  }

  String get formattedListingType {
    switch (listingType.toLowerCase()) {
      case 'rent':
      case 'rental':
        return 'For Rent';

      case 'sale':
        return 'For Sale';

      default:
        return listingType.replaceAll('_', ' ').trim();
    }
  }

  String get formattedPrice {
    final numericPrice = double.tryParse(price);

    if (numericPrice == null) {
      return 'KES $price';
    }

    final formattedAmount = numericPrice
        .toStringAsFixed(0)
        .replaceAllMapped(RegExp(r'\B(?=(\d{3})+(?!\d))'), (match) => ',');

    final suffix = listingType.toLowerCase() == 'rent' ? ' / month' : '';

    return 'KES $formattedAmount$suffix';
  }

  String get locationLabel {
    final parts = <String>[
      estate,
      town,
      county,
    ].where((value) => value.trim().isNotEmpty).toList();

    return parts.isEmpty ? 'Location not provided' : parts.join(', ');
  }

  bool get isVerified {
    final badge = trustBadge.toLowerCase();

    return badge != 'none' && badge.isNotEmpty;
  }

  String get partnerName {
    final currentPartner = partner;

    if (currentPartner == null) {
      return 'Pata Hao Partner';
    }

    if (currentPartner.businessName.trim().isNotEmpty) {
      return currentPartner.businessName;
    }

    if (currentPartner.name.trim().isNotEmpty) {
      return currentPartner.name;
    }

    return 'Pata Hao Partner';
  }

  bool get hasPartner {
    return partner != null;
  }

  bool get hasAmenities {
    return amenities.isNotEmpty;
  }

  PropertyPhoto? get coverPhoto {
    for (final photo in photos) {
      if (photo.isCover && photo.image.trim().isNotEmpty) {
        return photo;
      }
    }

    for (final photo in photos) {
      if (photo.image.trim().isNotEmpty) {
        return photo;
      }
    }

    return null;
  }

  PropertyVideo? get coverVideo {
    for (final video in videos) {
      if (video.isFeatured && video.thumbnail.trim().isNotEmpty) {
        return video;
      }
    }

    for (final video in videos) {
      if (video.thumbnail.trim().isNotEmpty) {
        return video;
      }
    }

    return null;
  }

  bool get hasCoverPhoto {
    return coverPhoto != null;
  }

  bool get hasVideoThumbnail {
    return coverVideo != null;
  }
  bool get hasVideo {
    return videos.any(
      (video) => video.video.trim().isNotEmpty,
    );
  }
  String? get coverMediaUrl {
    final video = coverVideo;

    if (video != null && video.thumbnail.trim().isNotEmpty) {
      return video.thumbnail;
    }

    final photo = coverPhoto;

    if (photo != null && photo.image.trim().isNotEmpty) {
      return photo.image;
    }

    return null;
  }

  bool get usesVideoThumbnail {
    final video = coverVideo;

    return video != null && video.thumbnail.trim().isNotEmpty;
  }

  Property copyWith({
    int? id,
    String? title,
    Partner? partner,
    String? propertyType,
    String? listingType,
    String? price,
    String? county,
    String? town,
    String? estate,
    int? bedrooms,
    int? bathrooms,
    String? description,
    String? status,
    String? verificationReturnReason,
    String? trustBadge,
    bool? isFavorite,
    int? favoriteId,
    bool clearFavoriteId = false,
    List<PropertyPhoto>? photos,
    List<PropertyVideo>? videos,
    List<PropertyAmenity>? amenities,
  }) {
    return Property(
      id: id ?? this.id,
      title: title ?? this.title,
      partner: partner ?? this.partner,
      propertyType: propertyType ?? this.propertyType,
      listingType: listingType ?? this.listingType,
      price: price ?? this.price,
      county: county ?? this.county,
      town: town ?? this.town,
      estate: estate ?? this.estate,
      bedrooms: bedrooms ?? this.bedrooms,
      bathrooms: bathrooms ?? this.bathrooms,
      description: description ?? this.description,
      status: status ?? this.status,
      verificationReturnReason:
          verificationReturnReason ??
          this.verificationReturnReason,
      trustBadge: trustBadge ?? this.trustBadge,
      isFavorite: isFavorite ?? this.isFavorite,
      favoriteId: clearFavoriteId ? null : favoriteId ?? this.favoriteId,
      photos: photos ?? this.photos,
      videos: videos ?? this.videos,
      amenities: amenities ?? this.amenities,
    );
  }

  static int _toInt(dynamic value) {
    if (value is int) {
      return value;
    }

    return int.tryParse(value?.toString() ?? '') ?? 0;
  }
}
