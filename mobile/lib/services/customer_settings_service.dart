import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class CustomerSettings {
  const CustomerSettings({
    required this.pushNotifications,
    required this.smsReminders,
    required this.emailReceipts,
    required this.language,
  });

  final bool pushNotifications;
  final bool smsReminders;
  final bool emailReceipts;
  final String language;

  CustomerSettings copyWith({
    bool? pushNotifications,
    bool? smsReminders,
    bool? emailReceipts,
    String? language,
  }) {
    return CustomerSettings(
      pushNotifications: pushNotifications ?? this.pushNotifications,
      smsReminders: smsReminders ?? this.smsReminders,
      emailReceipts: emailReceipts ?? this.emailReceipts,
      language: language ?? this.language,
    );
  }

  static const CustomerSettings defaults = CustomerSettings(
    pushNotifications: true,
    smsReminders: true,
    emailReceipts: true,
    language: 'English',
  );
}

class CustomerSettingsService {
  CustomerSettingsService._();

  static final CustomerSettingsService instance = CustomerSettingsService._();

  static const FlutterSecureStorage _storage = FlutterSecureStorage();

  static const String _pushNotificationsKey = 'customer_push_notifications';

  static const String _smsRemindersKey = 'customer_sms_reminders';

  static const String _emailReceiptsKey = 'customer_email_receipts';

  static const String _languageKey = 'customer_language';

  Future<CustomerSettings> loadSettings() async {
    final values = await Future.wait<String?>([
      _storage.read(key: _pushNotificationsKey),
      _storage.read(key: _smsRemindersKey),
      _storage.read(key: _emailReceiptsKey),
      _storage.read(key: _languageKey),
    ]);

    return CustomerSettings(
      pushNotifications: _parseBoolean(
        values[0],
        fallback: CustomerSettings.defaults.pushNotifications,
      ),
      smsReminders: _parseBoolean(
        values[1],
        fallback: CustomerSettings.defaults.smsReminders,
      ),
      emailReceipts: _parseBoolean(
        values[2],
        fallback: CustomerSettings.defaults.emailReceipts,
      ),
      language: _parseLanguage(values[3]),
    );
  }

  Future<void> savePushNotifications(bool value) async {
    await _storage.write(key: _pushNotificationsKey, value: value.toString());
  }

  Future<void> saveSmsReminders(bool value) async {
    await _storage.write(key: _smsRemindersKey, value: value.toString());
  }

  Future<void> saveEmailReceipts(bool value) async {
    await _storage.write(key: _emailReceiptsKey, value: value.toString());
  }

  Future<void> saveLanguage(String value) async {
    final normalized = _parseLanguage(value);

    await _storage.write(key: _languageKey, value: normalized);
  }

  Future<void> resetSettings() async {
    await Future.wait([
      _storage.delete(key: _pushNotificationsKey),
      _storage.delete(key: _smsRemindersKey),
      _storage.delete(key: _emailReceiptsKey),
      _storage.delete(key: _languageKey),
    ]);
  }

  bool _parseBoolean(String? value, {required bool fallback}) {
    if (value == null) {
      return fallback;
    }

    switch (value.trim().toLowerCase()) {
      case 'true':
      case '1':
      case 'yes':
        return true;

      case 'false':
      case '0':
      case 'no':
        return false;

      default:
        return fallback;
    }
  }

  String _parseLanguage(String? value) {
    final normalized = value?.trim().toLowerCase();

    if (normalized == 'kiswahili') {
      return 'Kiswahili';
    }

    return 'English';
  }
}
