import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

import '../foundation/app_error_message.dart';
import '../models/payment.dart';
import '../models/viewing.dart';
import '../models/viewing_credit.dart';
import '../services/payment_service.dart';
import 'payment_success_screen.dart';

class PaymentScreen extends StatefulWidget {
  const PaymentScreen({super.key, required this.viewing, this.paymentService});

  final Viewing viewing;
  final PaymentService? paymentService;

  @override
  State<PaymentScreen> createState() {
    return _PaymentScreenState();
  }
}

class _PaymentScreenState extends State<PaymentScreen> {
  final GlobalKey<FormState> _formKey = GlobalKey<FormState>();

  final TextEditingController _phoneController = TextEditingController();

  late final PaymentService _paymentService;

  bool _isProcessing = false;
  bool _isLoadingCredit = true;
  bool _useViewingCredit = false;
  String _paymentMessage = '';
  String _creditError = '';
  ViewingCreditBalance? _creditBalance;
  Payment? _existingPayment;

  double get _availableCredit => _creditBalance?.availableAmount ?? 0;

  double get _creditToApply {
    if (_existingPayment != null) {
      return _existingPayment!.creditAppliedAmount;
    }

    if (!_useViewingCredit || _availableCredit <= 0) {
      return 0;
    }

    return _availableCredit < widget.viewing.feeAmount
        ? _availableCredit
        : widget.viewing.feeAmount;
  }

  double get _cashDue =>
      _existingPayment?.cashAmount ?? widget.viewing.feeAmount - _creditToApply;

  bool get _requiresMpesa => _cashDue > 0.001;

  @override
  void initState() {
    super.initState();
    _paymentService = widget.paymentService ?? PaymentService();
    _loadViewingCredit();
  }

  @override
  void dispose() {
    _phoneController.dispose();
    super.dispose();
  }

  Future<void> _pay() async {
    FocusScope.of(context).unfocus();

    if (_isProcessing) {
      return;
    }

    if (!_formKey.currentState!.validate()) {
      return;
    }

    setState(() {
      _isProcessing = true;
      _paymentMessage = _existingPayment != null
          ? 'Resuming your protected viewing payment...'
          : _useViewingCredit
          ? 'Applying your protected viewing credit...'
          : 'Creating your secure M-Pesa payment...';
    });

    try {
      final Payment createdPayment =
          _existingPayment ??
          await _paymentService.createPayment(
            viewingId: widget.viewing.id,
            phoneNumber: _phoneController.text.trim(),
            useViewingCredit: _useViewingCredit,
          );

      if (mounted && _existingPayment == null) {
        setState(() {
          _existingPayment = createdPayment;
          _useViewingCredit = createdPayment.usedViewingCredit;
        });
      }

      final createdStatus = createdPayment.status.trim().toLowerCase();

      /*
       * A newly created payment must be pending or processing.
       *
       * If Django returns successful here, this viewing already has
       * an old completed payment. We do not pretend that a new STK
       * Push occurred.
       */
      if ((createdStatus == 'successful' || createdStatus == 'paid') &&
          createdPayment.fullyCoveredByCredit) {
        await _openPaymentSuccess(createdPayment);
        return;
      }

      if (createdStatus == 'successful' || createdStatus == 'paid') {
        throw Exception(
          'This viewing already has a completed payment. '
          'Create a new viewing request before testing M-Pesa again.',
        );
      }

      if (createdStatus == 'cancelled' || createdStatus == 'expired') {
        throw Exception('The payment record could not be prepared for M-Pesa.');
      }

      if (!mounted) {
        return;
      }

      setState(() {
        _paymentMessage = createdPayment.usedViewingCredit
            ? 'Credit applied. Sending KES '
                  '${createdPayment.cashAmount.toStringAsFixed(0)} '
                  'M-Pesa request to your phone...'
            : 'Sending the M-Pesa request to your phone...';
      });

      final Payment initiatedPayment = await _paymentService
          .initiateMpesaPayment(paymentId: createdPayment.id);

      final initiatedStatus = initiatedPayment.status.trim().toLowerCase();

      /*
       * The initiation endpoint should normally return processing.
       *
       * Even if it returns successful, we do not open the success
       * screen from this response. We independently fetch the latest
       * backend status during polling.
       */
      if (initiatedStatus == 'failed' ||
          initiatedStatus == 'cancelled' ||
          initiatedStatus == 'expired') {
        throw Exception(_paymentFailureMessage(initiatedPayment));
      }

      if (!mounted) {
        return;
      }

      setState(() {
        _paymentMessage = 'Check your phone and enter your M-Pesa PIN.';
      });

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text(
            'M-Pesa request sent. '
            'Check your phone and enter your PIN.',
          ),
          duration: Duration(seconds: 6),
        ),
      );

      /*
       * Wait briefly before the first status request.
       * Safaricom needs time to deliver the STK prompt.
       */
      await Future<void>.delayed(const Duration(seconds: 4));

      /*
       * Poll for up to approximately two minutes:
       * 30 attempts × 4 seconds.
       */
      for (int attempt = 1; attempt <= 30; attempt++) {
        if (!mounted) {
          return;
        }

        setState(() {
          _paymentMessage =
              'Waiting for M-Pesa confirmation '
              '($attempt of 30)...';
        });

        final Payment currentPayment = await _paymentService.getPayment(
          paymentId: createdPayment.id,
        );

        final status = currentPayment.status.trim().toLowerCase();

        if (status == 'successful' || status == 'paid') {
          /*
           * Fetch the official viewing receipt after the backend
           * has received and processed the Safaricom callback.
           */
          await _openPaymentSuccess(currentPayment);

          return;
        }

        if (status == 'failed' ||
            status == 'cancelled' ||
            status == 'expired') {
          throw Exception(_paymentFailureMessage(currentPayment));
        }

        if (attempt < 30) {
          await Future<void>.delayed(const Duration(seconds: 4));
        }
      }

      if (!mounted) {
        return;
      }

      setState(() {
        _paymentMessage = 'Payment confirmation is still pending.';
      });

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text(
            'M-Pesa confirmation is taking longer than expected. '
            'Do not pay again. Check your M-Pesa messages.',
          ),
          duration: Duration(seconds: 10),
        ),
      );
    } catch (error) {
      if (!mounted) {
        return;
      }

      setState(() {
        _paymentMessage = '';
      });

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(_cleanError(error)),
          duration: const Duration(seconds: 8),
        ),
      );
    } finally {
      if (mounted) {
        setState(() {
          _isProcessing = false;
        });
      }
    }
  }

  Future<void> _completeDevelopmentPayment() async {
    FocusScope.of(context).unfocus();

    if (_isProcessing) {
      return;
    }

    if (!_formKey.currentState!.validate()) {
      return;
    }

    setState(() {
      _isProcessing = true;
      _paymentMessage = 'Preparing a safe development payment...';
    });

    try {
      final createdPayment =
          _existingPayment ??
          await _paymentService.createPayment(
            viewingId: widget.viewing.id,
            phoneNumber: _phoneController.text.trim(),
            useViewingCredit: _useViewingCredit,
          );

      if (mounted && _existingPayment == null) {
        setState(() {
          _existingPayment = createdPayment;
          _useViewingCredit = createdPayment.usedViewingCredit;
        });
      }

      if (createdPayment.isSuccessful && createdPayment.fullyCoveredByCredit) {
        await _openPaymentSuccess(createdPayment);
        return;
      }

      if (!mounted) {
        return;
      }

      setState(() {
        _paymentMessage = 'Completing the development payment...';
      });

      final completedPayment = await _paymentService.completeDevelopmentPayment(
        paymentId: createdPayment.id,
      );

      await _openPaymentSuccess(completedPayment);
    } catch (error) {
      if (!mounted) {
        return;
      }

      setState(() {
        _paymentMessage = '';
      });

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(_cleanError(error)),
          duration: const Duration(seconds: 8),
        ),
      );
    } finally {
      if (mounted) {
        setState(() {
          _isProcessing = false;
        });
      }
    }
  }

  Future<void> _loadViewingCredit() async {
    try {
      Payment? existingPayment;
      final viewingStatus = widget.viewing.status.trim().toLowerCase();

      if (viewingStatus == 'payment_processing' ||
          viewingStatus == 'payment_failed') {
        existingPayment = await _paymentService.fetchViewingPayment(
          viewingId: widget.viewing.id,
        );
      }

      final balance = await _paymentService.fetchViewingCreditBalance();

      if (!mounted) {
        return;
      }

      if (existingPayment != null &&
          existingPayment.phoneNumber.trim().isNotEmpty) {
        _phoneController.text = existingPayment.phoneNumber;
      }

      setState(() {
        _existingPayment = existingPayment;
        _creditBalance = balance;
        _useViewingCredit = existingPayment?.usedViewingCredit ?? false;
        _creditError = '';
        _isLoadingCredit = false;
      });
    } catch (error) {
      if (!mounted) {
        return;
      }

      setState(() {
        _creditError = _cleanError(error);
        _isLoadingCredit = false;
      });
    }
  }

  Future<void> _openPaymentSuccess(Payment payment) async {
    Payment confirmedPayment = payment;

    try {
      confirmedPayment = await _paymentService.getViewingReceipt(
        viewingId: widget.viewing.id,
      );
    } catch (_) {
      // A successful payment response is itself a valid receipt fallback.
    }

    if (!mounted) {
      return;
    }

    await Navigator.of(context).pushReplacement(
      MaterialPageRoute<void>(
        builder: (_) => PaymentSuccessScreen(
          viewing: widget.viewing,
          payment: confirmedPayment,
        ),
      ),
    );
  }

  String _paymentFailureMessage(Payment payment) {
    final failureReason = payment.failureReason.trim();

    if (failureReason.isNotEmpty) {
      return failureReason;
    }

    final status = payment.status.trim().toLowerCase();

    if (status == 'cancelled') {
      return 'The M-Pesa request was cancelled.';
    }

    if (status == 'expired') {
      return 'The M-Pesa request expired. Please try again.';
    }

    return 'The M-Pesa payment was not completed.';
  }

  String _cleanError(Object error) {
    return AppErrorMessage.forError(error);
  }

  String? _validatePhoneNumber(String? value) {
    if (!_requiresMpesa) {
      return null;
    }

    if (value == null || value.trim().isEmpty) {
      return 'Enter your M-Pesa phone number.';
    }

    final normalized = value.replaceAll(RegExp(r'[^0-9]'), '');

    final validLocalSafaricom =
        normalized.startsWith('07') && normalized.length == 10;

    final validLocalNew =
        normalized.startsWith('01') && normalized.length == 10;

    final validInternational = RegExp(r'^254(7|1)\d{8}$').hasMatch(normalized);

    if (!validLocalSafaricom && !validLocalNew && !validInternational) {
      return 'Use 07XXXXXXXX, 01XXXXXXXX, '
          'or 254XXXXXXXXX.';
    }

    return null;
  }

  @override
  Widget build(BuildContext context) {
    final creditToApply = _creditToApply;
    final cashDue = _cashDue;
    final paymentButtonText = _isProcessing
        ? (_requiresMpesa ? 'Waiting for M-Pesa...' : 'Applying Credit...')
        : _existingPayment != null && _requiresMpesa
        ? 'Resume M-Pesa · KES ${cashDue.toStringAsFixed(0)}'
        : _useViewingCredit && !_requiresMpesa
        ? 'Use KES ${creditToApply.toStringAsFixed(0)} Credit'
        : _useViewingCredit
        ? 'Use KES ${creditToApply.toStringAsFixed(0)} + '
              'Pay KES ${cashDue.toStringAsFixed(0)}'
        : 'Pay KES ${widget.viewing.feeAmount.toStringAsFixed(0)}';

    return Scaffold(
      appBar: AppBar(title: const Text('Viewing Payment')),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(20),
          child: Form(
            key: _formKey,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text(
                  widget.viewing.propertyTitle,
                  style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 8),
                const Text('Your viewing reservation is pending payment.'),
                const SizedBox(height: 24),
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(18),
                    child: Column(
                      children: [
                        _DetailRow(
                          label: 'Reservation ID',
                          value: widget.viewing.id.toString(),
                        ),
                        _DetailRow(
                          label: 'Status',
                          value: widget.viewing.status
                              .replaceAll('_', ' ')
                              .toUpperCase(),
                        ),
                        _DetailRow(
                          label: 'Viewing date',
                          value: widget.viewing.requestedDate,
                        ),
                        _DetailRow(
                          label: 'Viewing time',
                          value: widget.viewing.requestedTime,
                        ),
                        _DetailRow(
                          label: 'Viewing fee',
                          value:
                              'KES '
                              '${widget.viewing.feeAmount.toStringAsFixed(0)}',
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 24),
                if (_isLoadingCredit)
                  const Card(
                    child: Padding(
                      padding: EdgeInsets.all(18),
                      child: Row(
                        children: [
                          SizedBox(
                            width: 20,
                            height: 20,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          ),
                          SizedBox(width: 12),
                          Expanded(
                            child: Text('Checking your viewing credit...'),
                          ),
                        ],
                      ),
                    ),
                  )
                else if (_creditBalance?.hasCredit == true ||
                    _existingPayment?.usedViewingCredit == true)
                  Card(
                    color: const Color(0xFFF0FDF4),
                    child: SwitchListTile.adaptive(
                      value: _useViewingCredit,
                      onChanged: _isProcessing || _existingPayment != null
                          ? null
                          : (value) {
                              setState(() {
                                _useViewingCredit = value;
                              });
                            },
                      secondary: const Icon(
                        Icons.account_balance_wallet_outlined,
                        color: Color(0xFF166534),
                      ),
                      title: Text(
                        _existingPayment?.usedViewingCredit == true
                            ? 'Viewing credit already applied '
                                  '(KES ${creditToApply.toStringAsFixed(0)})'
                            : 'Use viewing credit '
                                  '(KES ${_availableCredit.toStringAsFixed(0)} '
                                  'available)',
                        style: const TextStyle(fontWeight: FontWeight.bold),
                      ),
                      subtitle: Padding(
                        padding: const EdgeInsets.only(top: 6),
                        child: Text(
                          _existingPayment?.usedViewingCredit == true
                              ? 'This credit is protected in this payment. '
                                    'KES ${_availableCredit.toStringAsFixed(0)} '
                                    'remains available.'
                              : _useViewingCredit
                              ? 'KES ${creditToApply.toStringAsFixed(0)} will '
                                    'be used. KES '
                                    '${(_availableCredit - creditToApply).toStringAsFixed(0)} '
                                    'will remain.'
                              : 'Your credit will stay available for a future '
                                    'viewing.',
                        ),
                      ),
                    ),
                  )
                else if (_creditError.isNotEmpty)
                  Card(
                    color: const Color(0xFFFFFBEB),
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text(
                            'We could not check your viewing credit.',
                            style: TextStyle(fontWeight: FontWeight.bold),
                          ),
                          const SizedBox(height: 6),
                          const Text(
                            'You can continue with M-Pesa or try checking '
                            'again.',
                          ),
                          const SizedBox(height: 8),
                          TextButton.icon(
                            onPressed: _isProcessing
                                ? null
                                : () {
                                    setState(() {
                                      _isLoadingCredit = true;
                                      _creditError = '';
                                    });
                                    _loadViewingCredit();
                                  },
                            icon: const Icon(Icons.refresh),
                            label: const Text('Check Again'),
                          ),
                        ],
                      ),
                    ),
                  ),
                if (_requiresMpesa) ...[
                  const SizedBox(height: 24),
                  const Text(
                    'M-Pesa phone number',
                    style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 10),
                  TextFormField(
                    controller: _phoneController,
                    enabled: !_isProcessing,
                    keyboardType: TextInputType.phone,
                    decoration: const InputDecoration(
                      hintText: '0712345678',
                      prefixIcon: Icon(Icons.phone_android),
                      border: OutlineInputBorder(),
                    ),
                    validator: _validatePhoneNumber,
                  ),
                  const SizedBox(height: 14),
                  Text(
                    _useViewingCredit
                        ? 'After applying your credit, an M-Pesa request for '
                              'KES ${cashDue.toStringAsFixed(0)} will be sent '
                              'to this phone.'
                        : 'An M-Pesa payment request will be sent to this '
                              'phone. Enter your M-Pesa PIN on the phone to '
                              'complete payment.',
                    style: const TextStyle(color: Colors.black54, height: 1.4),
                  ),
                ],
                if (_paymentMessage.isNotEmpty) ...[
                  const SizedBox(height: 20),
                  Container(
                    padding: const EdgeInsets.all(14),
                    decoration: BoxDecoration(
                      color: Colors.orange.shade50,
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(color: Colors.orange.shade200),
                    ),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        if (_isProcessing)
                          const Padding(
                            padding: EdgeInsets.only(top: 2),
                            child: SizedBox(
                              width: 19,
                              height: 19,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            ),
                          ),
                        if (_isProcessing) const SizedBox(width: 12),
                        Expanded(
                          child: Text(
                            _paymentMessage,
                            style: const TextStyle(fontWeight: FontWeight.w600),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
                const SizedBox(height: 28),
                SizedBox(
                  height: 56,
                  child: FilledButton.icon(
                    onPressed: _isProcessing || _isLoadingCredit ? null : _pay,
                    icon: _isProcessing
                        ? const SizedBox(
                            width: 22,
                            height: 22,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : Icon(
                            _useViewingCredit
                                ? Icons.account_balance_wallet_outlined
                                : Icons.lock_outline,
                          ),
                    label: Text(
                      paymentButtonText,
                      style: const TextStyle(fontSize: 18),
                    ),
                  ),
                ),
                if (kDebugMode && _requiresMpesa) ...[
                  const SizedBox(height: 12),
                  OutlinedButton.icon(
                    onPressed: _isProcessing
                        ? null
                        : _completeDevelopmentPayment,
                    icon: const Icon(Icons.science_outlined),
                    label: const Text('Complete Test Payment'),
                  ),
                  const SizedBox(height: 8),
                  const Text(
                    'Development only — no M-Pesa request is sent.',
                    textAlign: TextAlign.center,
                    style: TextStyle(color: Colors.black54, fontSize: 12),
                  ),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _DetailRow extends StatelessWidget {
  const _DetailRow({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 9),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            child: Text(label, style: const TextStyle(color: Colors.black54)),
          ),
          Flexible(
            child: Text(
              value,
              textAlign: TextAlign.end,
              style: const TextStyle(fontWeight: FontWeight.bold),
            ),
          ),
        ],
      ),
    );
  }
}
