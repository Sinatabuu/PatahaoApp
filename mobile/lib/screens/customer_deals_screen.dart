import 'package:flutter/material.dart';

import 'package:mobile/models/deal.dart';
import 'package:mobile/screens/customer_deal_confirmation_screen.dart';
import 'package:mobile/services/deal_service.dart';

class CustomerDealsScreen extends StatefulWidget {
  const CustomerDealsScreen({
    super.key,
  });

  @override
  State<CustomerDealsScreen> createState() {
    return _CustomerDealsScreenState();
  }
}

class _CustomerDealsScreenState
    extends State<CustomerDealsScreen> {
  bool _isLoading = true;
  String? _errorMessage;
  List<Deal> _deals = const [];

  @override
  void initState() {
    super.initState();
    _loadDeals();
  }

  Future<void> _loadDeals() async {
    if (mounted) {
      setState(() {
        _isLoading = true;
        _errorMessage = null;
      });
    }

    try {
      final deals =
          await DealService.instance.fetchDeals();

      if (!mounted) {
        return;
      }

      setState(() {
        _deals = deals;
      });
    } catch (error) {
      if (!mounted) {
        return;
      }

      setState(() {
        _errorMessage = _cleanError(error);
      });
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  Future<void> _openConfirmation(
    Deal deal,
  ) async {
    final updatedDeal =
        await Navigator.of(context).push<Deal>(
      MaterialPageRoute<Deal>(
        builder: (_) =>
            CustomerDealConfirmationScreen(
          deal: deal,
        ),
      ),
    );

    if (!mounted || updatedDeal == null) {
      return;
    }

    setState(() {
      _deals = _deals.map((currentDeal) {
        if (currentDeal.id == updatedDeal.id) {
          return updatedDeal;
        }

        return currentDeal;
      }).toList();
    });
  }

  String _cleanError(Object error) {
    return error
        .toString()
        .replaceFirst(
          RegExp(r'^Exception:\s*'),
          '',
        )
        .trim();
  }

  String _statusLabel(String status) {
    switch (status.toLowerCase()) {
      case 'awaiting_customer':
        return 'Awaiting your confirmation';

      case 'awaiting_partner':
        return 'Awaiting partner confirmation';

      case 'awaiting_owner':
        return 'Awaiting owner confirmation';

      case 'awaiting_confirmations':
        return 'Awaiting confirmations';

      case 'negotiating':
        return 'Still being considered';

      case 'agreed':
        return 'Deal agreed';

      case 'completed':
        return 'Completed';

      case 'commission_paid':
        return 'Completed';

      case 'cancelled':
        return 'No deal';

      case 'disputed':
        return 'Needs review';

      default:
        if (status.trim().isEmpty) {
          return 'Deal';
        }

        return status
            .replaceAll('_', ' ')
            .split(' ')
            .where(
              (word) => word.isNotEmpty,
            )
            .map(
              (word) =>
                  '${word[0].toUpperCase()}'
                  '${word.substring(1)}',
            )
            .join(' ');
    }
  }

  IconData _statusIcon(Deal deal) {
    if (deal.status == 'agreed' ||
        deal.status == 'completed' ||
        deal.status == 'commission_paid') {
      return Icons.verified_outlined;
    }

    if (deal.status == 'cancelled') {
      return Icons.cancel_outlined;
    }

    if (deal.status == 'disputed') {
      return Icons.report_problem_outlined;
    }

    if (deal.customerConfirmed) {
      return Icons.schedule_outlined;
    }

    return Icons.task_alt_outlined;
  }

  Widget _buildDealCard(Deal deal) {
    final customerNeedsToConfirm =
        !deal.customerConfirmed;

    return Card(
      margin: const EdgeInsets.only(
        bottom: 14,
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment:
              CrossAxisAlignment.start,
          children: [
            Row(
              crossAxisAlignment:
                  CrossAxisAlignment.start,
              children: [
                Icon(
                  _statusIcon(deal),
                  size: 28,
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment:
                        CrossAxisAlignment.start,
                    children: [
                      Text(
                        deal.propertyTitle,
                        style: const TextStyle(
                          fontSize: 18,
                          fontWeight:
                              FontWeight.w700,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        deal.isSale
                            ? 'Property purchase'
                            : 'Property rental',
                      ),
                    ],
                  ),
                ),
              ],
            ),

            const SizedBox(height: 14),

            _DealInfoRow(
              label: 'Status',
              value: _statusLabel(
                deal.status,
              ),
            ),

            if (deal.partnerName
                .trim()
                .isNotEmpty)
              _DealInfoRow(
                label: 'Partner',
                value: deal.partnerName,
              ),

            if (deal.requestedDate
                .trim()
                .isNotEmpty)
              _DealInfoRow(
                label: 'Viewing',
                value: deal.requestedDate,
              ),

            const SizedBox(height: 12),

            _ConfirmationProgress(
              customerConfirmed:
                  deal.customerConfirmed,
              partnerConfirmed:
                  deal.partnerConfirmed,
              ownerConfirmed:
                  deal.ownerConfirmed,
            ),

            const SizedBox(height: 16),

            if (customerNeedsToConfirm)
              SizedBox(
                width: double.infinity,
                child: FilledButton.icon(
                  onPressed: () {
                    _openConfirmation(
                      deal,
                    );
                  },
                  icon: const Icon(
                    Icons.fact_check_outlined,
                  ),
                  label: const Text(
                    'Confirm Outcome',
                  ),
                ),
              )
            else
              Container(
                width: double.infinity,
                padding:
                    const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  borderRadius:
                      BorderRadius.circular(10),
                  color:
                      Colors.green.shade50,
                ),
                child: const Row(
                  children: [
                    Icon(
                      Icons.lock_outline,
                      size: 20,
                    ),
                    SizedBox(width: 10),
                    Expanded(
                      child: Text(
                        'Your confirmation '
                        'has been submitted.',
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

  Widget _buildBody() {
    if (_isLoading) {
      return const Center(
        child: CircularProgressIndicator(),
      );
    }

    if (_errorMessage != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize:
                MainAxisSize.min,
            children: [
              const Icon(
                Icons.error_outline,
                size: 52,
              ),
              const SizedBox(height: 14),
              Text(
                _errorMessage!,
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 18),
              FilledButton.icon(
                onPressed: _loadDeals,
                icon: const Icon(
                  Icons.refresh,
                ),
                label: const Text(
                  'Try Again',
                ),
              ),
            ],
          ),
        ),
      );
    }

    if (_deals.isEmpty) {
      return RefreshIndicator(
        onRefresh: _loadDeals,
        child: ListView(
          physics:
              const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(24),
          children: const [
            SizedBox(height: 120),
            Icon(
              Icons.handshake_outlined,
              size: 64,
            ),
            SizedBox(height: 18),
            Text(
              'No deals yet',
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: 21,
                fontWeight: FontWeight.bold,
              ),
            ),
            SizedBox(height: 8),
            Text(
              'When a property transaction '
              'reaches the confirmation stage, '
              'it will appear here.',
              textAlign: TextAlign.center,
            ),
          ],
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: _loadDeals,
      child: ListView(
        physics:
            const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(16),
        children: [
          const Text(
            'My Deals',
            style: TextStyle(
              fontSize: 24,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 6),
          const Text(
            'Confirm what happened after '
            'your property viewing.',
          ),
          const SizedBox(height: 18),

          ..._deals.map(
            _buildDealCard,
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text(
          'My Deals',
        ),
        actions: [
          IconButton(
            onPressed:
                _isLoading ? null : _loadDeals,
            tooltip: 'Refresh',
            icon: const Icon(
              Icons.refresh,
            ),
          ),
        ],
      ),
      body: _buildBody(),
    );
  }
}

class _DealInfoRow extends StatelessWidget {
  const _DealInfoRow({
    required this.label,
    required this.value,
  });

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding:
          const EdgeInsets.only(bottom: 5),
      child: Row(
        crossAxisAlignment:
            CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 76,
            child: Text(
              '$label:',
              style: const TextStyle(
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
          Expanded(
            child: Text(value),
          ),
        ],
      ),
    );
  }
}

class _ConfirmationProgress
    extends StatelessWidget {
  const _ConfirmationProgress({
    required this.customerConfirmed,
    required this.partnerConfirmed,
    required this.ownerConfirmed,
  });

  final bool customerConfirmed;
  final bool partnerConfirmed;
  final bool ownerConfirmed;

  Widget _item(
    String label,
    bool confirmed,
  ) {
    return Expanded(
      child: Column(
        children: [
          Icon(
            confirmed
                ? Icons.check_circle
                : Icons.radio_button_unchecked,
            size: 22,
            color: confirmed
                ? Colors.green
                : Colors.grey,
          ),
          const SizedBox(height: 5),
          Text(
            label,
            textAlign: TextAlign.center,
            style: const TextStyle(
              fontSize: 12,
            ),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        _item(
          'You',
          customerConfirmed,
        ),
        _item(
          'Partner',
          partnerConfirmed,
        ),
        _item(
          'Owner',
          ownerConfirmed,
        ),
      ],
    );
  }
}