import 'package:flutter/material.dart';

import 'package:mobile/services/staff_governance_service.dart';
import 'package:mobile/screens/staff_governance_case_detail_screen.dart';

class StaffGovernanceCasesScreen extends StatefulWidget {
  const StaffGovernanceCasesScreen({super.key});

  @override
  State<StaffGovernanceCasesScreen> createState() {
    return _StaffGovernanceCasesScreenState();
  }
}

class _StaffGovernanceCasesScreenState
    extends State<StaffGovernanceCasesScreen> {
  bool _isLoading = true;
  String? _errorMessage;

  List<Map<String, dynamic>> _cases = <Map<String, dynamic>>[];

  @override
  void initState() {
    super.initState();
    _loadCases();
  }

  Future<void> _loadCases() async {
    if (!mounted) {
      return;
    }

    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final response = await StaffGovernanceService.instance.fetchCases();

      final rawResults = response['results'];

      final cases = <Map<String, dynamic>>[];

      if (rawResults is List) {
        for (final item in rawResults) {
          if (item is Map) {
            cases.add(Map<String, dynamic>.from(item));
          }
        }
      }

      if (!mounted) {
        return;
      }

      setState(() {
        _cases = cases;
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

  String _text(Map<String, dynamic> item, String key) {
    return item[key]?.toString().trim() ?? '';
  }

  String _cleanError(Object error) {
    return error.toString().replaceFirst(RegExp(r'^Exception:\s*'), '').trim();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF6F8F6),
      appBar: AppBar(
        title: const Text('Governance Review'),
        backgroundColor: const Color(0xFF14532D),
        foregroundColor: Colors.white,
        actions: [
          IconButton(
            tooltip: 'Refresh',
            onPressed: _isLoading ? null : _loadCases,
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      body: _buildBody(),
    );
  }

  Widget _buildBody() {
    if (_isLoading && _cases.isEmpty) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_errorMessage != null && _cases.isEmpty) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.error_outline, size: 52, color: Colors.black38),
              const SizedBox(height: 14),
              Text(_errorMessage!, textAlign: TextAlign.center),
              const SizedBox(height: 16),
              FilledButton.icon(
                onPressed: _loadCases,
                icon: const Icon(Icons.refresh),
                label: const Text('Try again'),
              ),
            ],
          ),
        ),
      );
    }

    if (_cases.isEmpty) {
      return RefreshIndicator(
        onRefresh: _loadCases,
        child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          children: const [
            SizedBox(height: 120),
            Icon(Icons.verified_user_outlined, size: 60, color: Colors.black26),
            SizedBox(height: 16),
            Center(
              child: Text(
                'No governance cases are waiting for Pata Hao.',
                style: TextStyle(color: Colors.black54),
              ),
            ),
          ],
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: _loadCases,
      child: ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(16),
        children: [
          if (_isLoading)
            const Padding(
              padding: EdgeInsets.only(bottom: 12),
              child: LinearProgressIndicator(),
            ),

          Text(
            '${_cases.length} case'
            '${_cases.length == 1 ? '' : 's'} '
            'waiting for staff review',
            style: const TextStyle(
              color: Colors.black54,
              fontWeight: FontWeight.w600,
            ),
          ),

          const SizedBox(height: 14),

          ..._cases.map((governanceCase) {
            final propertyTitle = _text(governanceCase, 'property_title');

            final dealNumber = _text(governanceCase, 'deal_number');

            final partnerName = _text(governanceCase, 'partner_name');

            final title = _text(governanceCase, 'title');

            final message = _text(governanceCase, 'message');

            return Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: Card(
                elevation: 0,
                child: InkWell(
                  borderRadius: BorderRadius.circular(12),
                  onTap: () async {
                    final changed = await Navigator.of(context).push<bool>(
                      MaterialPageRoute<bool>(
                        builder: (_) {
                          return StaffGovernanceCaseDetailScreen(
                            governanceCase: governanceCase,
                          );
                        },
                      ),
                    );

                    if (!mounted) {
                      return;
                    }

                    if (changed == true) {
                      await _loadCases();
                    }
                  },
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const CircleAvatar(
                              backgroundColor: Color(0xFFFFF7ED),
                              child: Icon(
                                Icons.gpp_maybe_outlined,
                                color: Color(0xFFC2410C),
                              ),
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    propertyTitle.isEmpty
                                        ? 'Property'
                                        : propertyTitle,
                                    style: const TextStyle(
                                      fontSize: 17,
                                      fontWeight: FontWeight.bold,
                                    ),
                                  ),
                                  if (dealNumber.isNotEmpty)
                                    Text(
                                      dealNumber,
                                      style: const TextStyle(
                                        color: Colors.black54,
                                        fontSize: 12,
                                      ),
                                    ),
                                ],
                              ),
                            ),
                            const Icon(
                              Icons.chevron_right,
                              color: Colors.black38,
                            ),
                          ],
                        ),
                        const SizedBox(height: 14),

                        Text(
                          title.isEmpty ? 'Governance review required' : title,
                          style: const TextStyle(fontWeight: FontWeight.w700),
                        ),

                        if (partnerName.isNotEmpty) ...[
                          const SizedBox(height: 6),
                          Text(
                            'Partner: $partnerName',
                            style: const TextStyle(color: Colors.black54),
                          ),
                        ],

                        if (message.isNotEmpty) ...[
                          const SizedBox(height: 10),
                          Text(
                            message,
                            maxLines: 3,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(height: 1.4),
                          ),
                        ],

                        const SizedBox(height: 12),

                        const Align(
                          alignment: Alignment.centerLeft,
                          child: Chip(
                            avatar: Icon(
                              Icons.account_balance_outlined,
                              size: 18,
                            ),
                            label: Text('Pata Hao action required'),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            );
          }),
        ],
      ),
    );
  }
}
