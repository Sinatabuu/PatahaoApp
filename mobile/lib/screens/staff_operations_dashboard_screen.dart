import 'package:flutter/material.dart';

import 'package:mobile/screens/staff_property_review_queue_screen.dart';
import 'package:mobile/screens/staff_properties_screen.dart';
import 'package:mobile/services/staff_operations_service.dart';
import 'package:mobile/services/auth_service.dart';
import 'package:mobile/screens/staff_partners_screen.dart';
import 'package:mobile/screens/staff_viewings_screen.dart';
import 'package:mobile/screens/staff_deals_screen.dart';
import 'package:mobile/screens/staff_completed_deals_revenue_screen.dart';
import 'package:mobile/screens/staff_governance_cases_screen.dart';

class StaffOperationsDashboardScreen extends StatefulWidget {
  const StaffOperationsDashboardScreen({
    super.key,
    required this.currentUser,
    required this.onLogout,
  });

  final AuthUser currentUser;
  final Future<void> Function() onLogout;

  @override
  State<StaffOperationsDashboardScreen> createState() {
    return _StaffOperationsDashboardScreenState();
  }
}

class _StaffOperationsDashboardScreenState
    extends State<StaffOperationsDashboardScreen> {
  bool _isLoading = true;
  String? _errorMessage;
  StaffOperationsSummary? _summary;

  @override
  void initState() {
    super.initState();
    _loadSummary();
  }

  Future<void> _loadSummary() async {
    if (!mounted) {
      return;
    }

    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final summary = await StaffOperationsService.instance.fetchSummary();

      if (!mounted) {
        return;
      }

      setState(() {
        _summary = summary;
        _isLoading = false;
      });
    } catch (error) {
      if (!mounted) {
        return;
      }

      setState(() {
        _isLoading = false;
        _errorMessage = _cleanError(error);
      });
    }
  }

  Future<void> _openReviewDesk() async {
    await Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) {
          return StaffPropertyReviewQueueScreen(onLogout: widget.onLogout);
        },
      ),
    );

    if (!mounted) {
      return;
    }

    await _loadSummary();
  }

  Future<void> _openProperties() async {
    await Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) {
          return const StaffPropertiesScreen();
        },
      ),
    );

    if (!mounted) {
      return;
    }

    await _loadSummary();
  }

  Future<void> _openPartners() async {
    await Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) {
          return const StaffPartnersScreen();
        },
      ),
    );

    if (!mounted) {
      return;
    }

    await _loadSummary();
  }

  Future<void> _openViewings() async {
    await Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) {
          return const StaffViewingsScreen();
        },
      ),
    );

    if (!mounted) {
      return;
    }

    await _loadSummary();
  }

  String _cleanError(Object error) {
    return error.toString().replaceFirst(RegExp(r'^Exception:\s*'), '').trim();
  }

  Future<void> _openDeals() async {
    await Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) {
          return const StaffDealsScreen();
        },
      ),
    );

    if (!mounted) {
      return;
    }

    await _loadSummary();
  }

  Future<void> _openCompletedDealsRevenue() async {
    await Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) {
          return const StaffCompletedDealsRevenueScreen();
        },
      ),
    );

    if (!mounted) {
      return;
    }

    await _loadSummary();
  }

  Future<void> _openGovernanceCases() async {
    await Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) {
          return const StaffGovernanceCasesScreen();
        },
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF6F8F6),
      appBar: AppBar(
        title: const Text('Pata Hao Operations'),
        backgroundColor: const Color(0xFF14532D),
        foregroundColor: Colors.white,
        actions: [
          IconButton(
            tooltip: 'Refresh',
            onPressed: _isLoading ? null : _loadSummary,
            icon: const Icon(Icons.refresh),
          ),
          IconButton(
            tooltip: 'Sign Out',
            onPressed: widget.onLogout,
            icon: const Icon(Icons.logout),
          ),
        ],
      ),
      body: RefreshIndicator(onRefresh: _loadSummary, child: _buildBody()),
    );
  }

  Widget _buildBody() {
    if (_isLoading && _summary == null) {
      return ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        children: const [
          SizedBox(height: 180),
          Center(child: CircularProgressIndicator()),
        ],
      );
    }

    if (_errorMessage != null && _summary == null) {
      return ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(20),
        children: [
          const SizedBox(height: 80),
          Icon(Icons.error_outline, size: 56, color: Colors.orange.shade800),
          const SizedBox(height: 16),
          const Text(
            'Unable to load operations',
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 10),
          Text(
            _errorMessage!,
            textAlign: TextAlign.center,
            style: const TextStyle(color: Colors.black54, height: 1.4),
          ),
          const SizedBox(height: 20),
          Center(
            child: ElevatedButton.icon(
              onPressed: _loadSummary,
              icon: const Icon(Icons.refresh),
              label: const Text('Try Again'),
            ),
          ),
        ],
      );
    }

    final summary = _summary;

    if (summary == null) {
      return const SizedBox.shrink();
    }

    return ListView(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.all(16),
      children: [
        const Text(
          'Operations Overview',
          style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 4),
        Text(
          'Signed in as ${widget.currentUser.displayName}',
          style: const TextStyle(
            fontSize: 14,
            color: Colors.black54,
            fontWeight: FontWeight.w500,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          summary.generatedForDate.isEmpty
              ? 'Current Pata Hao activity'
              : 'Activity for ${summary.generatedForDate}',
          style: const TextStyle(color: Colors.black54),
        ),
        const SizedBox(height: 20),
        GridView.count(
          crossAxisCount: 2,
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          crossAxisSpacing: 12,
          mainAxisSpacing: 12,
          childAspectRatio: 1.35,
          children: [
            _SummaryCard(
              label: 'Pending Reviews',
              value: summary.pendingReviews,
              icon: Icons.fact_check_outlined,
            ),
            _SummaryCard(
              label: 'Published Properties',
              value: summary.publishedProperties,
              icon: Icons.home_work_outlined,
            ),
            _SummaryCard(
              label: 'Active Partners',
              value: summary.activePartners,
              icon: Icons.groups_outlined,
            ),
            _SummaryCard(
              label: "Today's Viewings",
              value: summary.todaysViewings,
              icon: Icons.calendar_today_outlined,
            ),
            _SummaryCard(
              label: 'Open Deals',
              value: summary.openDeals,
              icon: Icons.handshake_outlined,
            ),
            _SummaryCard(
              label: 'Commission Activity',
              value: summary.commissionActivity,
              icon: Icons.payments_outlined,
            ),
          ],
        ),

        const SizedBox(height: 28),

        const Text(
          'Administration',
          style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 12),

        Card(
          child: ListTile(
            contentPadding: const EdgeInsets.symmetric(
              horizontal: 18,
              vertical: 10,
            ),
            leading: const CircleAvatar(
              backgroundColor: Color(0xFFE7F5EC),
              child: Icon(Icons.fact_check_outlined, color: Color(0xFF14532D)),
            ),
            title: const Text(
              'Property Review Desk',
              style: TextStyle(fontWeight: FontWeight.w600),
            ),
            subtitle: Text(
              summary.pendingReviews == 1
                  ? '1 property waiting for review'
                  : '${summary.pendingReviews} properties waiting for review',
            ),
            trailing: const Icon(Icons.chevron_right),
            onTap: _openReviewDesk,
          ),
        ),

        const SizedBox(height: 12),

        Card(
          child: ListTile(
            contentPadding: const EdgeInsets.symmetric(
              horizontal: 18,
              vertical: 10,
            ),
            leading: const CircleAvatar(
              backgroundColor: Color(0xFFE7F5EC),
              child: Icon(Icons.apartment_outlined, color: Color(0xFF14532D)),
            ),
            title: const Text(
              'Properties',
              style: TextStyle(fontWeight: FontWeight.w600),
            ),
            subtitle: Text(
              '${summary.publishedProperties} currently published',
            ),
            trailing: const Icon(Icons.chevron_right),
            onTap: _openProperties,
          ),
        ),

        Card(
          child: ListTile(
            contentPadding: const EdgeInsets.symmetric(
              horizontal: 18,
              vertical: 10,
            ),
            leading: const CircleAvatar(
              backgroundColor: Color(0xFFE7F5EC),
              child: Icon(Icons.people_outline, color: Color(0xFF14532D)),
            ),
            title: const Text(
              'Partners',
              style: TextStyle(fontWeight: FontWeight.w600),
            ),
            subtitle: Text('${summary.activePartners} active partners'),
            trailing: const Icon(Icons.chevron_right),
            onTap: _openPartners,
          ),
        ),

        Card(
          child: ListTile(
            contentPadding: const EdgeInsets.symmetric(
              horizontal: 18,
              vertical: 10,
            ),
            leading: const CircleAvatar(
              backgroundColor: Color(0xFFE7F5EC),
              child: Icon(
                Icons.calendar_month_outlined,
                color: Color(0xFF14532D),
              ),
            ),
            title: const Text(
              'Viewings',
              style: TextStyle(fontWeight: FontWeight.w600),
            ),
            subtitle: Text("${summary.todaysViewings} scheduled today"),
            trailing: const Icon(Icons.chevron_right),
            onTap: _openViewings,
          ),
        ),

        Card(
          child: ListTile(
            contentPadding: const EdgeInsets.symmetric(
              horizontal: 18,
              vertical: 10,
            ),
            leading: const CircleAvatar(
              backgroundColor: Color(0xFFE7F5EC),
              child: Icon(Icons.handshake_outlined, color: Color(0xFF14532D)),
            ),
            title: const Text(
              'Deals',
              style: TextStyle(fontWeight: FontWeight.w600),
            ),
            subtitle: Text('${summary.openDeals} open deals'),
            trailing: const Icon(Icons.chevron_right),
            onTap: _openDeals,
          ),
        ),

        Card(
          child: ListTile(
            contentPadding: const EdgeInsets.symmetric(
              horizontal: 18,
              vertical: 10,
            ),
            leading: const CircleAvatar(
              backgroundColor: Color(0xFFFFF7ED),
              child: Icon(Icons.gpp_maybe_outlined, color: Color(0xFFC2410C)),
            ),
            title: const Text(
              'Governance Review',
              style: TextStyle(fontWeight: FontWeight.w600),
            ),
            subtitle: const Text('Blocked deals requiring Pata Hao review'),
            trailing: const Icon(Icons.chevron_right),
            onTap: _openGovernanceCases,
          ),
        ),
        Card(
          child: ListTile(
            contentPadding: const EdgeInsets.symmetric(
              horizontal: 18,
              vertical: 10,
            ),
            leading: const CircleAvatar(
              backgroundColor: Color(0xFFE7F5EC),
              child: Icon(Icons.bar_chart_outlined, color: Color(0xFF14532D)),
            ),
            title: const Text(
              'Completed Deals & Revenue',
              style: TextStyle(fontWeight: FontWeight.w600),
            ),
            subtitle: const Text(
              'Commission, partner payouts, and Pata Hao retained revenue',
            ),
            trailing: const Icon(Icons.chevron_right),
            onTap: _openCompletedDealsRevenue,
          ),
        ),

        const SizedBox(height: 24),
      ],
    );
  }
}

class _SummaryCard extends StatelessWidget {
  const _SummaryCard({
    required this.label,
    required this.value,
    required this.icon,
  });

  final String label;
  final int value;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Icon(icon, color: const Color(0xFF14532D)),
            Text(
              '$value',
              style: const TextStyle(fontSize: 28, fontWeight: FontWeight.bold),
            ),
            Text(
              label,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(
                color: Colors.black54,
                fontWeight: FontWeight.w500,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
