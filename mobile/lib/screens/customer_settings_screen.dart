import 'package:flutter/material.dart';

import '../services/customer_settings_service.dart';


class CustomerSettingsScreen extends StatefulWidget {
  const CustomerSettingsScreen({super.key, required this.onLogout});

  final Future<void> Function() onLogout;

  @override
  State<CustomerSettingsScreen> createState() => _CustomerSettingsScreenState();
}

class _CustomerSettingsScreenState extends State<CustomerSettingsScreen> {
  late Future<CustomerSettings> _settingsFuture;

  CustomerSettings? _settings;
  bool _isSaving = false;

  @override
  void initState() {
    super.initState();
    _loadSettings();
  }

  void _loadSettings() {
    _settingsFuture = CustomerSettingsService.instance.loadSettings();
  }

  Future<void> _refreshSettings() async {
    setState(_loadSettings);

    final settings = await _settingsFuture;

    if (!mounted) {
      return;
    }

    setState(() {
      _settings = settings;
    });
  }

  Future<void> _savePreference({
    required CustomerSettings updatedSettings,
    required Future<void> Function() saveAction,
  }) async {
    if (_isSaving) {
      return;
    }

    final previousSettings = _settings;

    setState(() {
      _settings = updatedSettings;
      _isSaving = true;
    });

    try {
      await saveAction();
    } catch (error) {
      if (!mounted) {
        return;
      }

      setState(() {
        _settings = previousSettings;
      });

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(error.toString().replaceFirst('Exception: ', '')),
        ),
      );
    } finally {
      if (mounted) {
        setState(() {
          _isSaving = false;
        });
      }
    }
  }

  Future<void> _changePushNotifications(bool value) async {
    final current = _settings ?? CustomerSettings.defaults;

    await _savePreference(
      updatedSettings: current.copyWith(pushNotifications: value),
      saveAction: () {
        return CustomerSettingsService.instance.savePushNotifications(value);
      },
    );
  }

  Future<void> _changeSmsReminders(bool value) async {
    final current = _settings ?? CustomerSettings.defaults;

    await _savePreference(
      updatedSettings: current.copyWith(smsReminders: value),
      saveAction: () {
        return CustomerSettingsService.instance.saveSmsReminders(value);
      },
    );
  }

  Future<void> _changeEmailReceipts(bool value) async {
    final current = _settings ?? CustomerSettings.defaults;

    await _savePreference(
      updatedSettings: current.copyWith(emailReceipts: value),
      saveAction: () {
        return CustomerSettingsService.instance.saveEmailReceipts(value);
      },
    );
  }

  Future<void> _chooseLanguage() async {
    final current = _settings ?? CustomerSettings.defaults;

    final selectedLanguage = await showDialog<String>(
      context: context,
      builder: (dialogContext) {
        return SimpleDialog(
          title: const Text('Choose language'),
          children: [
            SimpleDialogOption(
              onPressed: () {
                Navigator.of(dialogContext).pop('English');
              },
              child: Row(
                children: [
                  Icon(
                    current.language == 'English'
                        ? Icons.check_circle_rounded
                        : Icons.circle_outlined,
                    color: const Color(0xFF14532D),
                  ),
                  const SizedBox(width: 12),
                  const Text('English'),
                ],
              ),
            ),
            SimpleDialogOption(
              onPressed: () {
                Navigator.of(dialogContext).pop('Kiswahili');
              },
              child: Row(
                children: [
                  Icon(
                    current.language == 'Kiswahili'
                        ? Icons.check_circle_rounded
                        : Icons.circle_outlined,
                    color: const Color(0xFF14532D),
                  ),
                  const SizedBox(width: 12),
                  const Text('Kiswahili'),
                ],
              ),
            ),
          ],
        );
      },
    );

    if (selectedLanguage == null || selectedLanguage == current.language) {
      return;
    }

    await _savePreference(
      updatedSettings: current.copyWith(language: selectedLanguage),
      saveAction: () {
        return CustomerSettingsService.instance.saveLanguage(selectedLanguage);
      },
    );

    if (!mounted) {
      return;
    }

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          selectedLanguage == 'Kiswahili'
              ? 'Kiswahili preference saved.'
              : 'English preference saved.',
        ),
      ),
    );
  }

  Future<void> _resetPreferences() async {
    final shouldReset = await showDialog<bool>(
      context: context,
      builder: (dialogContext) {
        return AlertDialog(
          icon: const Icon(Icons.restart_alt_rounded, color: Color(0xFF14532D)),
          title: const Text('Reset preferences?'),
          content: const Text(
            'Notification and language settings will '
            'return to their defaults.',
          ),
          actions: [
            TextButton(
              onPressed: () {
                Navigator.of(dialogContext).pop(false);
              },
              child: const Text('Cancel'),
            ),
            FilledButton(
              onPressed: () {
                Navigator.of(dialogContext).pop(true);
              },
              child: const Text('Reset'),
            ),
          ],
        );
      },
    );

    if (shouldReset != true) {
      return;
    }

    setState(() {
      _isSaving = true;
    });

    try {
      await CustomerSettingsService.instance.resetSettings();

      if (!mounted) {
        return;
      }

      setState(() {
        _settings = CustomerSettings.defaults;
        _settingsFuture = Future.value(CustomerSettings.defaults);
      });

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Settings restored to defaults.')),
      );
    } finally {
      if (mounted) {
        setState(() {
          _isSaving = false;
        });
      }
    }
  }

  Future<void> _showInformation({
    required String title,
    required String message,
    IconData icon = Icons.info_outline_rounded,
  }) async {
    await showDialog<void>(
      context: context,
      builder: (dialogContext) {
        return AlertDialog(
          icon: Icon(icon, color: const Color(0xFF14532D)),
          title: Text(title),
          content: Text(message, style: const TextStyle(height: 1.45)),
          actions: [
            FilledButton(
              onPressed: () {
                Navigator.of(dialogContext).pop();
              },
              child: const Text('Close'),
            ),
          ],
        );
      },
    );
  }

  Future<void> _showLogoutDialog() async {
    final shouldLogout = await showDialog<bool>(
      context: context,
      builder: (dialogContext) {
        return AlertDialog(
          icon: const Icon(Icons.logout_rounded, color: Color(0xFFB91C1C)),
          title: const Text('Log out?'),
          content: const Text(
            'You will need to sign in again to access '
            'your properties, viewings, payments, and '
            'receipts.',
          ),
          actions: [
            TextButton(
              onPressed: () {
                Navigator.of(dialogContext).pop(false);
              },
              child: const Text('Stay Signed In'),
            ),
            FilledButton(
              onPressed: () {
                Navigator.of(dialogContext).pop(true);
              },
              style: FilledButton.styleFrom(
                backgroundColor: const Color(0xFFB91C1C),
              ),
              child: const Text('Log Out'),
            ),
          ],
        );
      },
    );

    if (shouldLogout != true) {
      return;
    }

    await widget.onLogout();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF4F7F4),
      appBar: AppBar(
        title: const Text('Settings'),
        backgroundColor: const Color(0xFF14532D),
        foregroundColor: Colors.white,
        actions: [
          if (_isSaving)
            const Padding(
              padding: EdgeInsets.only(right: 18),
              child: Center(
                child: SizedBox(
                  width: 19,
                  height: 19,
                  child: CircularProgressIndicator(
                    strokeWidth: 2,
                    color: Colors.white,
                  ),
                ),
              ),
            ),
        ],
      ),
      body: FutureBuilder<CustomerSettings>(
        future: _settingsFuture,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting &&
              _settings == null) {
            return const Center(child: CircularProgressIndicator());
          }

          if (snapshot.hasError && _settings == null) {
            return _SettingsErrorView(
              message: snapshot.error.toString().replaceFirst(
                'Exception: ',
                '',
              ),
              onRetry: _refreshSettings,
            );
          }

          final loadedSettings =
              _settings ?? snapshot.data ?? CustomerSettings.defaults;

          _settings ??= loadedSettings;

          return RefreshIndicator(
            onRefresh: _refreshSettings,
            child: ListView(
              physics: const AlwaysScrollableScrollPhysics(),
              padding: const EdgeInsets.fromLTRB(18, 20, 18, 36),
              children: [
                const _SettingsHeader(),
                const SizedBox(height: 24),
                const _SectionTitle(title: 'Notifications'),
                const SizedBox(height: 10),
                _SettingsSection(
                  children: [
                    SwitchListTile(
                      secondary: const Icon(
                        Icons.notifications_active_outlined,
                        color: Color(0xFF14532D),
                      ),
                      title: const Text('Push notifications'),
                      subtitle: const Text('Receive important in-app updates.'),
                      value: loadedSettings.pushNotifications,
                      onChanged: _isSaving ? null : _changePushNotifications,
                    ),
                    const Divider(height: 1),
                    SwitchListTile(
                      secondary: const Icon(
                        Icons.sms_outlined,
                        color: Color(0xFF14532D),
                      ),
                      title: const Text('SMS reminders'),
                      subtitle: const Text('Receive viewing reminders by SMS.'),
                      value: loadedSettings.smsReminders,
                      onChanged: _isSaving ? null : _changeSmsReminders,
                    ),
                    const Divider(height: 1),
                    SwitchListTile(
                      secondary: const Icon(
                        Icons.mark_email_read_outlined,
                        color: Color(0xFF14532D),
                      ),
                      title: const Text('Email receipts'),
                      subtitle: const Text(
                        'Receive payment receipts by email.',
                      ),
                      value: loadedSettings.emailReceipts,
                      onChanged: _isSaving ? null : _changeEmailReceipts,
                    ),
                  ],
                ),
                const SizedBox(height: 22),
                const _SectionTitle(title: 'Preferences'),
                const SizedBox(height: 10),
                _SettingsSection(
                  children: [
                    _SettingsTile(
                      icon: Icons.language_outlined,
                      title: 'Language',
                      subtitle: loadedSettings.language,
                      onTap: _chooseLanguage,
                    ),
                    const Divider(height: 1),
                    _SettingsTile(
                      icon: Icons.restart_alt_rounded,
                      title: 'Reset preferences',
                      subtitle: 'Restore notification and language defaults.',
                      onTap: _resetPreferences,
                    ),
                  ],
                ),
                const SizedBox(height: 22),
                const _SectionTitle(title: 'Privacy and legal'),
                const SizedBox(height: 10),
                _SettingsSection(
                  children: [
                    _SettingsTile(
                      icon: Icons.privacy_tip_outlined,
                      title: 'Privacy',
                      subtitle: 'How Pata Hao protects your information.',
                      onTap: () {
                        _showInformation(
                          title: 'Privacy',
                          icon: Icons.privacy_tip_outlined,
                          message:
                              'Pata Hao uses account information '
                              'to protect saved properties, viewing '
                              'requests, payments, receipts, and '
                              'customer support records. Sensitive '
                              'authentication information is stored '
                              'securely on your device.',
                        );
                      },
                    ),
                    const Divider(height: 1),
                    _SettingsTile(
                      icon: Icons.description_outlined,
                      title: 'Terms and conditions',
                      subtitle: 'Important rules for using Pata Hao.',
                      onTap: () {
                        _showInformation(
                          title: 'Terms and conditions',
                          icon: Icons.description_outlined,
                          message:
                              'Customers must provide accurate '
                              'information, use secure in-app '
                              'payment methods, and respect confirmed '
                              'viewing arrangements. Full legal terms '
                              'will be published before public launch.',
                        );
                      },
                    ),
                  ],
                ),
                const SizedBox(height: 22),
                const _SectionTitle(title: 'Support'),
                const SizedBox(height: 10),
                _SettingsSection(
                  children: [
                    _SettingsTile(
                      icon: Icons.help_outline_rounded,
                      title: 'Help center',
                      subtitle: 'Guidance for payments and viewings.',
                      onTap: () {
                        _showInformation(
                          title: 'Help center',
                          icon: Icons.help_outline_rounded,
                          message:
                              'For payment questions, first check '
                              'Pending Payments and Receipts. For '
                              'viewing questions, open My Viewings '
                              'to see the latest partner status.',
                        );
                      },
                    ),
                    const Divider(height: 1),
                    _SettingsTile(
                      icon: Icons.support_agent_outlined,
                      title: 'Contact Pata Hao',
                      subtitle: 'Customer support information.',
                      onTap: () {
                        _showInformation(
                          title: 'Contact Pata Hao',
                          icon: Icons.support_agent_outlined,
                          message:
                              'Customer support contact details will '
                              'be displayed here before public launch. '
                              'Always include your viewing or payment '
                              'reference when requesting assistance.',
                        );
                      },
                    ),
                    const Divider(height: 1),
                    _SettingsTile(
                      icon: Icons.home_work_outlined,
                      title: 'About Pata Hao',
                      subtitle: 'Find, commit, view, and move with confidence.',
                      onTap: () {
                        _showInformation(
                          title: 'About Pata Hao',
                          icon: Icons.home_work_outlined,
                          message:
                              'Pata Hao helps customers discover '
                              'properties, work with accountable '
                              'partners, pay secure viewing fees, '
                              'receive receipts, and track each '
                              'property journey from one place.',
                        );
                      },
                    ),
                  ],
                ),
                const SizedBox(height: 26),
                SizedBox(
                  height: 54,
                  child: OutlinedButton.icon(
                    onPressed: _showLogoutDialog,
                    style: OutlinedButton.styleFrom(
                      foregroundColor: const Color(0xFFB91C1C),
                      side: const BorderSide(color: Color(0xFFFCA5A5)),
                    ),
                    icon: const Icon(Icons.logout_rounded),
                    label: const Text(
                      'Log Out',
                      style: TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                ),
              ],
            ),
          );
        },
      ),
    );
  }
}

class _SettingsHeader extends StatelessWidget {
  const _SettingsHeader();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [Color(0xFF14532D), Color(0xFF2F7D32)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(20),
      ),
      child: const Row(
        children: [
          CircleAvatar(
            radius: 27,
            backgroundColor: Colors.white,
            child: Icon(
              Icons.settings_outlined,
              size: 29,
              color: Color(0xFF14532D),
            ),
          ),
          SizedBox(width: 15),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Your preferences',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 21,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                SizedBox(height: 5),
                Text(
                  'Control how Pata Hao communicates with you.',
                  style: TextStyle(color: Colors.white70, height: 1.35),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _SectionTitle extends StatelessWidget {
  const _SectionTitle({required this.title});

  final String title;

  @override
  Widget build(BuildContext context) {
    return Text(
      title,
      style: const TextStyle(
        fontSize: 19,
        fontWeight: FontWeight.bold,
        color: Color(0xFF111827),
      ),
    );
  }
}

class _SettingsSection extends StatelessWidget {
  const _SettingsSection({required this.children});

  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(17),
        border: Border.all(color: const Color(0xFFE5E7EB)),
      ),
      child: Column(children: children),
    );
  }
}

class _SettingsTile extends StatelessWidget {
  const _SettingsTile({
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
    return ListTile(
      leading: Container(
        width: 40,
        height: 40,
        decoration: BoxDecoration(
          color: const Color(0xFFE8F5E9),
          borderRadius: BorderRadius.circular(11),
        ),
        child: Icon(icon, size: 21, color: const Color(0xFF14532D)),
      ),
      title: Text(title, style: const TextStyle(fontWeight: FontWeight.w700)),
      subtitle: Text(subtitle),
      trailing: const Icon(Icons.chevron_right_rounded, color: Colors.black38),
      onTap: onTap,
    );
  }
}

class _SettingsErrorView extends StatelessWidget {
  const _SettingsErrorView({required this.message, required this.onRetry});

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
          const SizedBox(height: 110),
          const Icon(
            Icons.settings_suggest_outlined,
            size: 68,
            color: Colors.black38,
          ),
          const SizedBox(height: 18),
          const Text(
            'Could not load settings',
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 21, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 10),
          Text(
            message,
            textAlign: TextAlign.center,
            style: const TextStyle(color: Colors.black54),
          ),
          const SizedBox(height: 22),
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
