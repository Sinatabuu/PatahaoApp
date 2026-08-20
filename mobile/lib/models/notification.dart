class AppNotification {
  const AppNotification({
    required this.id,
    required this.title,
    required this.message,
    required this.notificationType,
    required this.notificationTypeLabel,
    required this.isRead,
    required this.createdAt,
    required this.governanceCaseId,
    required this.actionLabel,
  });

  final int id;
  final String title;
  final String message;
  final String notificationType;
  final String notificationTypeLabel;
  final bool isRead;
  final String createdAt;

  final int? governanceCaseId;
  final String actionLabel;

  bool get hasGovernanceAction {
    return governanceCaseId != null &&
        governanceCaseId! > 0 &&
        actionLabel.trim().isNotEmpty;
  }

  factory AppNotification.fromJson(Map<String, dynamic> json) {
    final governanceCase = _toNullableInt(json['governance_case']);

    return AppNotification(
      id: _toInt(json['id']),
      title: json['title']?.toString() ?? '',
      message: json['message']?.toString() ?? '',
      notificationType: json['notification_type']?.toString() ?? 'system',
      notificationTypeLabel: json['notification_type_label']?.toString() ?? '',
      isRead: json['is_read'] == true,
      createdAt: json['created_at']?.toString() ?? '',
      governanceCaseId: governanceCase,
      actionLabel: json['action_label']?.toString().trim() ?? '',
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
      governanceCaseId: governanceCaseId,
      actionLabel: actionLabel,
    );
  }

  static int _toInt(dynamic value) {
    if (value is int) {
      return value;
    }

    if (value is num) {
      return value.toInt();
    }

    return int.tryParse(value?.toString() ?? '') ?? 0;
  }

  static int? _toNullableInt(dynamic value) {
    if (value == null) {
      return null;
    }

    if (value is int) {
      return value;
    }

    if (value is num) {
      return value.toInt();
    }

    final parsed = int.tryParse(value.toString());

    if (parsed == null || parsed <= 0) {
      return null;
    }

    return parsed;
  }
}
