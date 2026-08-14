import 'package:flutter/material.dart';

import 'package:mobile/models/deal.dart';
import 'package:mobile/services/deal_service.dart';

class CustomerDealConfirmationScreen extends StatefulWidget {
  const CustomerDealConfirmationScreen({
    super.key,
    required this.deal,
  });

  final Deal deal;

  @override
  State<CustomerDealConfirmationScreen> createState() {
    return _CustomerDealConfirmationScreenState();
  }
}

class _CustomerDealConfirmationScreenState
    extends State<CustomerDealConfirmationScreen> {
  final TextEditingController _notesController =
      TextEditingController();

  String? _selectedOutcome;
  bool _isSubmitting = false;
  String? _errorMessage;

  Deal get deal => widget.deal;

  @override
  void dispose() {
    _notesController.dispose();
    super.dispose();
  }

  String get _successOutcome {
    return deal.isSale
        ? 'purchased'
        : 'rented';
  }

  String get _successTitle {
    return deal.isSale
        ? 'Yes, I bought this property'
        : 'Yes, I rented this property';
  }

  String get _question {
    return deal.isSale
        ? 'Did you buy this property?'
        : 'Did you rent this property?';
  }

  Future<void> _submit() async {
    if (_isSubmitting) {
      return;
    }

    final outcome = _selectedOutcome;

    if (outcome == null) {
      setState(() {
        _errorMessage =
            'Please choose what happened.';
      });

      return;
    }

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) {
        return AlertDialog(
          title: const Text(
            'Submit confirmation?',
          ),
          content: const Text(
            'Your confirmation becomes part of '
            'the permanent deal record and cannot '
            'be changed after submission.',
          ),
          actions: [
            TextButton(
              onPressed: () {
                Navigator.of(context).pop(false);
              },
              child: const Text(
                'Cancel',
              ),
            ),
            FilledButton(
              onPressed: () {
                Navigator.of(context).pop(true);
              },
              child: const Text(
                'Submit Confirmation',
              ),
            ),
          ],
        );
      },
    );

    if (confirmed != true || !mounted) {
      return;
    }

    setState(() {
      _isSubmitting = true;
      _errorMessage = null;
    });

    try {
      final updatedDeal =
          await DealService.instance
              .submitCustomerOutcome(
        dealId: deal.id,
        outcome: outcome,
        notes: _notesController.text,
      );

      if (!mounted) {
        return;
      }

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text(
            'Your confirmation was submitted.',
          ),
        ),
      );

      Navigator.of(context).pop(updatedDeal);
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
          _isSubmitting = false;
        });
      }
    }
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

  Widget _buildChoice({
    required String value,
    required String title,
    required String subtitle,
    required IconData icon,
  }) {
    return Card(
      margin: const EdgeInsets.only(
        bottom: 10,
      ),
      child: RadioListTile<String>(
        value: value,
        secondary: Icon(
          icon,
        ),
        title: Text(
          title,
          style: const TextStyle(
            fontWeight: FontWeight.w600,
          ),
        ),
        subtitle: Text(
          subtitle,
        ),
      ),
    );
  }

  Widget _buildAlreadyConfirmed() {
    return Scaffold(
      appBar: AppBar(
        title: const Text(
          'Deal Confirmation',
        ),
      ),
      body: const Center(
        child: Padding(
          padding: EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                Icons.verified_outlined,
                size: 64,
              ),
              SizedBox(height: 16),
              Text(
                'Your confirmation has already '
                'been submitted.',
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.w600,
                ),
              ),
              SizedBox(height: 8),
              Text(
                'Confirmations are permanent and '
                'cannot be changed.',
                textAlign: TextAlign.center,
              ),
            ],
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (deal.customerConfirmed) {
      return _buildAlreadyConfirmed();
    }

    return Scaffold(
      appBar: AppBar(
        title: const Text(
          'Deal Confirmation',
        ),
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text(
            deal.propertyTitle,
            style: const TextStyle(
              fontSize: 24,
              fontWeight: FontWeight.bold,
            ),
          ),

          const SizedBox(height: 6),

          Text(
            deal.isSale
                ? 'Property purchase'
                : 'Property rental',
          ),

          const SizedBox(height: 24),

          Text(
            _question,
            style: const TextStyle(
              fontSize: 20,
              fontWeight: FontWeight.w700,
            ),
          ),

          const SizedBox(height: 8),

          const Text(
            'Choose the answer that best '
            'describes what happened.',
          ),

          const SizedBox(height: 16),

          RadioGroup<String>(
            groupValue: _selectedOutcome,
            onChanged: (value) {
                if (_isSubmitting) {
                return;
                }

                setState(() {
                _selectedOutcome = value;
                _errorMessage = null;
                });
            },
            child: Column(
              children: [
                _buildChoice(
                  value: _successOutcome,
                  title: _successTitle,
                  subtitle: deal.isSale
                      ? 'I completed the purchase.'
                      : 'I moved forward with the rental.',
                  icon: Icons.check_circle_outline,
                ),

                _buildChoice(
                  value: 'still_deciding',
                  title: 'I am still deciding',
                  subtitle:
                      'The transaction is not complete yet.',
                  icon: Icons.schedule_outlined,
                ),

                _buildChoice(
                  value: 'declined',
                  title: 'No, I did not proceed',
                  subtitle: deal.isSale
                      ? 'I decided not to buy this property.'
                      : 'I decided not to rent this property.',
                  icon: Icons.cancel_outlined,
                ),
              ],
            ),
          ),

          const SizedBox(height: 20),

          TextField(
            controller: _notesController,
            enabled: !_isSubmitting,
            maxLines: 4,
            maxLength: 2000,
            decoration: const InputDecoration(
              labelText: 'Optional note',
              hintText:
                  'Add any helpful details...',
              border: OutlineInputBorder(),
            ),
          ),

          if (_errorMessage != null) ...[
            const SizedBox(height: 12),
            Text(
              _errorMessage!,
              style: TextStyle(
                color: Colors.red.shade700,
                fontWeight: FontWeight.w500,
              ),
            ),
          ],

          const SizedBox(height: 20),

          Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              borderRadius:
                  BorderRadius.circular(12),
              color: Colors.amber.shade50,
            ),
            child: const Row(
              crossAxisAlignment:
                  CrossAxisAlignment.start,
              children: [
                Icon(
                  Icons.lock_outline,
                  size: 20,
                ),
                SizedBox(width: 10),
                Expanded(
                  child: Text(
                    'Your answer becomes part of '
                    'the permanent deal record and '
                    'cannot be changed later.',
                  ),
                ),
              ],
            ),
          ),

          const SizedBox(height: 20),

          FilledButton.icon(
            onPressed:
                _isSubmitting ? null : _submit,
            icon: _isSubmitting
                ? const SizedBox(
                    width: 18,
                    height: 18,
                    child:
                        CircularProgressIndicator(
                      strokeWidth: 2,
                    ),
                  )
                : const Icon(
                    Icons.verified_outlined,
                  ),
            label: Text(
              _isSubmitting
                  ? 'Submitting...'
                  : 'Submit Confirmation',
            ),
          ),

          const SizedBox(height: 24),
        ],
      ),
    );
  }
}