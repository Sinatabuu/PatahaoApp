class AppNotification {
  const AppNotification({
    required this.id,
    required this.title,
    required this.message,
    required this.notificationType,
    required this.notificationTypeLabel,
    required this.isRead,
    required this.createdAt,
  });

  final int id;
  final String title;
  final String message;
  final String notificationType;
  final String notificationTypeLabel;
  final bool isRead;
  final String createdAt;

  factory AppNotification.fromJson(Map<String, dynamic> json) {
    return AppNotification(
      id: _toInt(json['id']),
      title: json['title']?.toString() ?? '',
      message: json['message']?.toString() ?? '',
      notificationType: json['notification_type']?.toString() ?? 'system',
      notificationTypeLabel: json['notification_type_label']?.toString() ?? '',
      isRead: json['is_read'] == true,
      createdAt: json['created_at']?.toString() ?? '',
    );
  }

  AppNotification copyWith({bool? isRead}) {
    return AppNotification(
      id: id,
      title: title,
      message: message,
      notificationType: notificationType,
      notificationTypeLabel: notificationTypeLabel,
      isRead: isRead ?? this.isRead,
      createdAt: createdAt,
    );
  }

  static int _toInt(dynamic value) {
    if (value is int) return value;
    if (value is num) return value.toInt();
    return int.tryParse(value?.toString() ?? '') ?? 0;
  }
}
