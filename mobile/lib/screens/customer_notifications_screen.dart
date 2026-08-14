import 'package:flutter/material.dart';

import '../models/notification.dart';
import '../services/notification_service.dart';

class CustomerNotificationsScreen extends StatefulWidget {
  const CustomerNotificationsScreen({super.key});

  @override
  State<CustomerNotificationsScreen> createState() =>
      _CustomerNotificationsScreenState();
}

class _CustomerNotificationsScreenState
    extends State<CustomerNotificationsScreen> {
  final NotificationService _service = const NotificationService();

  late Future<List<AppNotification>> _future;
  List<AppNotification>? _items;
  bool _markingAll = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() {
    _future = _service.fetchNotifications();
  }

  Future<void> _refresh() async {
    setState(_load);
    final items = await _future;
    if (!mounted) return;
    setState(() => _items = items);
  }

  Future<void> _open(AppNotification item) async {
    if (!item.isRead) {
      final previous = _items ?? <AppNotification>[];
      setState(() {
        _items = previous
            .map(
              (current) => current.id == item.id
                  ? current.copyWith(isRead: true)
                  : current,
            )
            .toList();
      });

      try {
        item = await _service.markAsRead(notificationId: item.id);
      } catch (error) {
        if (!mounted) return;
        await _refresh();
        if (!mounted) return;
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text(_clean(error))));
        return;
      }
    }

    if (!mounted) return;

    await showDialog<void>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        icon: Icon(
          _icon(item.notificationType),
          color: _color(item.notificationType),
        ),
        title: Text(item.title),
        content: Text(item.message, style: const TextStyle(height: 1.5)),
        actions: [
          FilledButton(
            onPressed: () {
              Navigator.of(dialogContext).pop();
            },
            child: const Text('Close'),
          ),
        ],
      ),
    );
  }

  Future<void> _markAll() async {
    final items = _items ?? <AppNotification>[];

    if (_markingAll || items.every((item) => item.isRead)) {
      return;
    }

    final previous = items;

    setState(() {
      _markingAll = true;
      _items = items.map((item) => item.copyWith(isRead: true)).toList();
    });

    try {
      await _service.markAllAsRead();

      if (!mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('All notifications marked as read.')),
      );
    } catch (error) {
      if (!mounted) return;
      setState(() => _items = previous);
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(_clean(error))));
    } finally {
      if (mounted) {
        setState(() => _markingAll = false);
      }
    }
  }

  String _clean(Object error) {
    return error.toString().replaceFirst('Exception: ', '').trim();
  }

  IconData _icon(String type) {
    switch (type.trim().toLowerCase()) {
      case 'viewing':
        return Icons.calendar_month_outlined;
      case 'payment':
        return Icons.payments_outlined;
      case 'deal':
        return Icons.handshake_outlined;
      default:
        return Icons.notifications_outlined;
    }
  }

  Color _color(String type) {
    switch (type.trim().toLowerCase()) {
      case 'viewing':
        return const Color(0xFF2563EB);
      case 'payment':
        return const Color(0xFF15803D);
      case 'deal':
        return const Color(0xFF7C3AED);
      default:
        return const Color(0xFFD97706);
    }
  }

  String _date(String value) {
    final parsed = DateTime.tryParse(value)?.toLocal();
    if (parsed == null) return '';

    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);
    final day = DateTime(parsed.year, parsed.month, parsed.day);
    final difference = today.difference(day).inDays;

    final hour = parsed.hour == 0
        ? 12
        : parsed.hour > 12
        ? parsed.hour - 12
        : parsed.hour;
    final minute = parsed.minute.toString().padLeft(2, '0');
    final period = parsed.hour >= 12 ? 'PM' : 'AM';

    if (difference == 0) {
      return 'Today, $hour:$minute $period';
    }

    if (difference == 1) {
      return 'Yesterday, $hour:$minute $period';
    }

    return '${parsed.day}/${parsed.month}/${parsed.year} '
        '$hour:$minute $period';
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF4F7F4),
      appBar: AppBar(
        title: const Text('Notifications'),
        backgroundColor: const Color(0xFF14532D),
        foregroundColor: Colors.white,
        actions: [
          IconButton(
            tooltip: 'Refresh',
            onPressed: _refresh,
            icon: const Icon(Icons.refresh_rounded),
          ),
          IconButton(
            tooltip: 'Mark all as read',
            onPressed: _markingAll ? null : _markAll,
            icon: _markingAll
                ? const SizedBox(
                    width: 19,
                    height: 19,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      color: Colors.white,
                    ),
                  )
                : const Icon(Icons.done_all_rounded),
          ),
        ],
      ),
      body: FutureBuilder<List<AppNotification>>(
        future: _future,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting &&
              _items == null) {
            return const Center(child: CircularProgressIndicator());
          }

          if (snapshot.hasError && _items == null) {
            return _ErrorView(
              message: _clean(snapshot.error!),
              onRetry: _refresh,
            );
          }

          final items = _items ?? snapshot.data ?? <AppNotification>[];

          _items ??= items;

          if (items.isEmpty) {
            return RefreshIndicator(
              onRefresh: _refresh,
              child: ListView(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: const EdgeInsets.all(24),
                children: const [
                  SizedBox(height: 110),
                  Icon(
                    Icons.notifications_none_rounded,
                    size: 78,
                    color: Color(0xFF34AD2C),
                  ),
                  SizedBox(height: 18),
                  Text(
                    'No notifications yet',
                    textAlign: TextAlign.center,
                    style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold),
                  ),
                  SizedBox(height: 10),
                  Text(
                    'Viewing, payment, and account '
                    'updates will appear here.',
                    textAlign: TextAlign.center,
                    style: TextStyle(color: Colors.black54, height: 1.5),
                  ),
                ],
              ),
            );
          }

          return RefreshIndicator(
            onRefresh: _refresh,
            child: ListView.builder(
              physics: const AlwaysScrollableScrollPhysics(),
              padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
              itemCount: items.length,
              itemBuilder: (context, index) {
                final item = items[index];

                return Card(
                  margin: const EdgeInsets.only(bottom: 12),
                  color: item.isRead ? Colors.white : const Color(0xFFF0FDF4),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(17),
                    side: BorderSide(
                      color: item.isRead
                          ? const Color(0xFFE5E7EB)
                          : const Color(0xFF86EFAC),
                    ),
                  ),
                  child: InkWell(
                    onTap: () => _open(item),
                    borderRadius: BorderRadius.circular(17),
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          CircleAvatar(
                            backgroundColor: _color(
                              item.notificationType,
                            ).withValues(alpha: 0.12),
                            child: Icon(
                              _icon(item.notificationType),
                              color: _color(item.notificationType),
                            ),
                          ),
                          const SizedBox(width: 13),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Row(
                                  children: [
                                    Expanded(
                                      child: Text(
                                        item.title,
                                        style: TextStyle(
                                          fontSize: 16,
                                          fontWeight: item.isRead
                                              ? FontWeight.w600
                                              : FontWeight.bold,
                                        ),
                                      ),
                                    ),
                                    if (!item.isRead)
                                      Container(
                                        width: 9,
                                        height: 9,
                                        decoration: const BoxDecoration(
                                          color: Color(0xFF34AD2C),
                                          shape: BoxShape.circle,
                                        ),
                                      ),
                                  ],
                                ),
                                const SizedBox(height: 6),
                                Text(
                                  item.message,
                                  maxLines: 3,
                                  overflow: TextOverflow.ellipsis,
                                  style: const TextStyle(
                                    color: Colors.black54,
                                    height: 1.4,
                                  ),
                                ),
                                if (_date(item.createdAt).isNotEmpty) ...[
                                  const SizedBox(height: 9),
                                  Text(
                                    _date(item.createdAt),
                                    style: const TextStyle(
                                      fontSize: 12,
                                      color: Colors.black45,
                                    ),
                                  ),
                                ],
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                );
              },
            ),
          );
        },
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
          const SizedBox(height: 110),
          const Icon(
            Icons.notifications_off_outlined,
            size: 68,
            color: Colors.black38,
          ),
          const SizedBox(height: 18),
          const Text(
            'Could not load notifications',
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
