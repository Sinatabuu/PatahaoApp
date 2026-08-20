class PartnerPropertyPhoto {
  const PartnerPropertyPhoto({
    required this.id,
    required this.imageUrl,
    required this.caption,
    required this.isCover,
  });

  final int id;
  final String imageUrl;
  final String caption;
  final bool isCover;

  factory PartnerPropertyPhoto.fromJson(Map<String, dynamic> json) {
    final rawImageUrl = json['image_url'] ?? json['image'];

    return PartnerPropertyPhoto(
      id: _parseInt(json['id']),
      imageUrl: rawImageUrl?.toString().trim() ?? '',
      caption: json['caption']?.toString().trim() ?? '',
      isCover: json['is_cover'] == true,
    );
  }

  static int _parseInt(dynamic value) {
    if (value is int) {
      return value;
    }

    return int.tryParse(value?.toString() ?? '') ?? 0;
  }
}