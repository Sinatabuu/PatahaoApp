import 'package:flutter/material.dart';

import 'package:mobile/models/property.dart';
import 'package:mobile/services/partner_mandate_service.dart';


class PartnerPropertyMandateScreen extends StatefulWidget {
  const PartnerPropertyMandateScreen({
    super.key,
    required this.property,
  });

  final Property property;

  @override
  State<PartnerPropertyMandateScreen> createState() {
    return _PartnerPropertyMandateScreenState();
  }
}


class _PartnerPropertyMandateScreenState
    extends State<PartnerPropertyMandateScreen> {
  final _formKey = GlobalKey<FormState>();

  final TextEditingController _ownerNameController =
      TextEditingController();

  final TextEditingController _ownerPhoneController =
      TextEditingController();

  final TextEditingController _commissionRateController =
      TextEditingController();

  final TextEditingController _fixedCommissionController =
      TextEditingController();

  final TextEditingController _authorizationNotesController =
      TextEditingController();

  bool _isLoading = true;
  bool _isSavingCommission = false;
  bool _isAcceptingCommission = false;
  bool _isCreatingMandate = false;
  bool _isDeclaringMandate = false;
  bool _isSubmittingForReview = false;

  String? _errorMessage;

  Map<String, dynamic> _agreement = <String, dynamic>{};
  Map<String, dynamic> _mandate = <String, dynamic>{};

  String _commissionMethod = 'percentage';
  String _commissionBasis = 'first_month_rent';
  String _authorizationMethod = 'phone';

  bool _authorityConfirmed = false;
  bool _paymentPolicyAccepted = false;
  bool _antiCircumventionAccepted = false;

  Property get property => widget.property;

  bool get _hasAgreement => _agreement.isNotEmpty;

  bool get _agreementAccepted =>
      _agreement['partner_accepted'] == true;

  bool get _agreementVerified =>
      _agreement['is_verified'] == true;

  bool get _agreementLocked =>
      _agreement['is_locked'] == true;

  int? get _agreementId => int.tryParse(
        _agreement['id']?.toString() ?? '',
      );

  bool get _hasMandate => _mandate.isNotEmpty;

  bool get _mandateDeclared =>
      _mandate['partner_declared'] == true;

  int? get _mandateId => int.tryParse(
        _mandate['id']?.toString() ?? '',
      );

  String get _mandateStatus =>
      _mandate['status']?.toString() ?? '';

  bool get _mandateUnderReview =>
      _mandateStatus == 'under_review';

  bool get _mandateApproved =>
      _mandateStatus == 'approved';

  bool get _commercialTermsFrozen =>
      _agreementAccepted ||
      _agreementVerified ||
      _agreementLocked;

  @override
  void initState() {
    super.initState();

    _commissionRateController.addListener(
      _rebuildCommissionPreview,
    );

    _fixedCommissionController.addListener(
      _rebuildCommissionPreview,
    );

    _loadData();
  }

  @override
  void dispose() {
    _ownerNameController.dispose();
    _ownerPhoneController.dispose();
    _commissionRateController.dispose();
    _fixedCommissionController.dispose();
    _authorizationNotesController.dispose();

    super.dispose();
  }

  void _rebuildCommissionPreview() {
    if (mounted) {
      setState(() {});
    }
  }

  Future<void> _loadData() async {
    if (!mounted) {
      return;
    }

    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final agreement =
          await PartnerMandateService.instance
              .fetchCommissionAgreementForProperty(
        property.id,
      );

      final mandate =
          await PartnerMandateService.instance
              .fetchMandateForProperty(
        property.id,
      );

      if (!mounted) {
        return;
      }

      setState(() {
        _agreement = agreement;
        _mandate = mandate;

        _hydrateFormFromServer();

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

  void _hydrateFormFromServer() {
    if (_agreement.isNotEmpty) {
      _ownerNameController.text =
          _agreement['owner_name']?.toString() ?? '';

      _ownerPhoneController.text =
          _agreement['owner_phone_number']?.toString() ?? '';

      final method =
          _agreement['commission_method']?.toString() ?? '';

      if (method == 'fixed' || method == 'percentage') {
        _commissionMethod = method;
      }

      final basis =
          _agreement['commission_basis']?.toString() ?? '';

      if (basis.isNotEmpty) {
        _commissionBasis = basis;
      }

      _commissionRateController.text =
          _agreement['commission_rate']?.toString() ?? '';

      _fixedCommissionController.text =
          _agreement['fixed_commission_amount']
                  ?.toString() ??
              '';
    }

    if (_mandate.isNotEmpty) {
      final authorizationMethod =
          _mandate['authorization_method']?.toString() ?? '';

      if (authorizationMethod.isNotEmpty) {
        _authorizationMethod = authorizationMethod;
      }

      _authorizationNotesController.text =
          _mandate['authorization_notes']?.toString() ?? '';

      _authorityConfirmed =
          _mandate['owner_authority_confirmed'] == true;

      _paymentPolicyAccepted =
          _mandate['no_cash_acknowledged'] == true;

      _antiCircumventionAccepted =
          _mandate['anti_circumvention_acknowledged'] == true;

      final ownerDetail = _mandate['owner_detail'];

      if (ownerDetail is Map) {
        final ownerMap =
            Map<String, dynamic>.from(ownerDetail);

        if (_ownerNameController.text.trim().isEmpty) {
          _ownerNameController.text =
              ownerMap['legal_name']?.toString() ?? '';
        }

        if (_ownerPhoneController.text.trim().isEmpty) {
          _ownerPhoneController.text =
              ownerMap['phone_number']?.toString() ?? '';
        }
      }
    }
  }

  Future<void> _saveCommission() async {
    if (_isSavingCommission ||
        _commercialTermsFrozen) {
      return;
    }

    if (!_formKey.currentState!.validate()) {
      return;
    }

    setState(() {
      _isSavingCommission = true;
      _errorMessage = null;
    });

    try {
      final transactionValue = property.price.trim();

      Map<String, dynamic> result;

      if (_hasAgreement) {
        final agreementId = _agreementId;

        if (agreementId == null) {
          throw Exception(
            'The commission agreement ID is invalid.',
          );
        }

        result =
            await PartnerMandateService.instance
                .updateCommissionAgreement(
          agreementId: agreementId,
          ownerName: _ownerNameController.text,
          ownerPhoneNumber:
              _ownerPhoneController.text,
          commissionMethod: _commissionMethod,
          commissionBasis: _commissionBasis,
          transactionValue: transactionValue,
          commissionRate:
              _commissionMethod == 'percentage'
                  ? _commissionRateController.text
                  : null,
          fixedCommissionAmount:
              _commissionMethod == 'fixed'
                  ? _fixedCommissionController.text
                  : null,
        );
      } else {
        result =
            await PartnerMandateService.instance
                .createCommissionAgreement(
          propertyId: property.id,
          ownerName: _ownerNameController.text,
          ownerPhoneNumber:
              _ownerPhoneController.text,
          commissionMethod: _commissionMethod,
          commissionBasis: _commissionBasis,
          transactionValue: transactionValue,
          commissionRate:
              _commissionMethod == 'percentage'
                  ? _commissionRateController.text
                  : null,
          fixedCommissionAmount:
              _commissionMethod == 'fixed'
                  ? _fixedCommissionController.text
                  : null,
        );
      }

      if (!mounted) {
        return;
      }

      setState(() {
        _agreement = result;
        _hydrateFormFromServer();
      });

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text(
            'Commission terms saved.',
          ),
        ),
      );
    } catch (error) {
      if (!mounted) {
        return;
      }

      setState(() {
        _errorMessage = _cleanError(error);
      });

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            _cleanError(error),
          ),
        ),
      );
    } finally {
      if (mounted) {
        setState(() {
          _isSavingCommission = false;
        });
      }
    }
  }

  Future<void> _acceptCommission() async {
    if (_isAcceptingCommission ||
        _agreementAccepted) {
      return;
    }

    final agreementId = _agreementId;

    if (agreementId == null) {
      return;
    }

    final shouldAccept = await showDialog<bool>(
      context: context,
      builder: (dialogContext) {
        return AlertDialog(
          title: const Text(
            'Accept Commission Terms?',
          ),
          content: Text(
            'You are confirming that the commission shown '
            'for "${property.title}" is the commission agreed '
            'for a successful Pata Hao transaction.\n\n'
            'Commission: ${_serverCommissionLabel()}',
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
              child: const Text('Accept'),
            ),
          ],
        );
      },
    );

    if (shouldAccept != true || !mounted) {
      return;
    }

    setState(() {
      _isAcceptingCommission = true;
      _errorMessage = null;
    });

    try {
      final result =
          await PartnerMandateService.instance
              .acceptCommissionAgreement(
        agreementId,
      );

      if (!mounted) {
        return;
      }

      setState(() {
        _agreement = result;
        _hydrateFormFromServer();
      });

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text(
            'Commission terms accepted.',
          ),
        ),
      );
    } catch (error) {
      if (!mounted) {
        return;
      }

      setState(() {
        _errorMessage = _cleanError(error);
      });

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            _cleanError(error),
          ),
        ),
      );
    } finally {
      if (mounted) {
        setState(() {
          _isAcceptingCommission = false;
        });
      }
    }
  }

  Future<void> _createMandate() async {
    if (_isCreatingMandate ||
        _hasMandate ||
        !_agreementAccepted) {
      return;
    }

    final agreementId = _agreementId;

    if (agreementId == null) {
      return;
    }

    setState(() {
      _isCreatingMandate = true;
      _errorMessage = null;
    });

    try {
      final result =
          await PartnerMandateService.instance
              .createMandate(
        propertyId: property.id,
        ownerName: _ownerNameController.text,
        ownerPhoneNumber:
            _ownerPhoneController.text,
        commissionAgreementId: agreementId,
        authorizationMethod:
            _authorizationMethod,
        authorizationNotes:
            _authorizationNotesController.text,
      );

      if (!mounted) {
        return;
      }

      setState(() {
        _mandate = result;
        _hydrateFormFromServer();
      });

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text(
            'Digital mandate created.',
          ),
        ),
      );
    } catch (error) {
      if (!mounted) {
        return;
      }

      setState(() {
        _errorMessage = _cleanError(error);
      });

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            _cleanError(error),
          ),
        ),
      );
    } finally {
      if (mounted) {
        setState(() {
          _isCreatingMandate = false;
        });
      }
    }
  }

  Future<void> _declareMandate() async {
    if (_isDeclaringMandate ||
        !_hasMandate ||
        _mandateDeclared) {
      return;
    }

    if (!_authorityConfirmed ||
        !_paymentPolicyAccepted ||
        !_antiCircumventionAccepted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text(
            'Please accept all three declarations first.',
          ),
        ),
      );

      return;
    }

    final mandateId = _mandateId;

    if (mandateId == null) {
      return;
    }

    final shouldAccept = await showDialog<bool>(
      context: context,
      builder: (dialogContext) {
        return AlertDialog(
          title: const Text(
            'Accept Digital Mandate?',
          ),
          content: const Text(
            'By continuing, you confirm that the information '
            'you provided is accurate and that you have authority '
            'to market this property under the terms shown.',
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
              child: const Text('Accept Mandate'),
            ),
          ],
        );
      },
    );

    if (shouldAccept != true || !mounted) {
      return;
    }

    setState(() {
      _isDeclaringMandate = true;
      _errorMessage = null;
    });

    try {
      final result =
          await PartnerMandateService.instance
              .declareMandate(
        mandateId: mandateId,
        authorizationMethod:
            _authorizationMethod,
        authorizationNotes:
            _authorizationNotesController.text,
      );

      if (!mounted) {
        return;
      }

      setState(() {
        _mandate = result;
        _hydrateFormFromServer();
      });

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text(
            'Digital mandate accepted.',
          ),
        ),
      );
    } catch (error) {
      if (!mounted) {
        return;
      }

      setState(() {
        _errorMessage = _cleanError(error);
      });

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            _cleanError(error),
          ),
        ),
      );
    } finally {
      if (mounted) {
        setState(() {
          _isDeclaringMandate = false;
        });
      }
    }
  }

  Future<void> _submitForReview() async {
    if (_isSubmittingForReview ||
        !_mandateDeclared ||
        _mandateUnderReview ||
        _mandateApproved) {
      return;
    }

    final mandateId = _mandateId;

    if (mandateId == null) {
      return;
    }

    setState(() {
      _isSubmittingForReview = true;
      _errorMessage = null;
    });

    try {
      final result =
          await PartnerMandateService.instance
              .submitMandateForReview(
        mandateId,
      );

      if (!mounted) {
        return;
      }

      setState(() {
        _mandate = result;
        _hydrateFormFromServer();
      });

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text(
            'Mandate submitted to Pata Hao for review.',
          ),
        ),
      );
    } catch (error) {
      if (!mounted) {
        return;
      }

      setState(() {
        _errorMessage = _cleanError(error);
      });

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            _cleanError(error),
          ),
        ),
      );
    } finally {
      if (mounted) {
        setState(() {
          _isSubmittingForReview = false;
        });
      }
    }
  }

  double _propertyValue() {
    return double.tryParse(
          property.price.trim(),
        ) ??
        0;
  }

  double _previewCommission() {
    final propertyValue = _propertyValue();

    if (_commissionMethod == 'percentage') {
      final rate = double.tryParse(
            _commissionRateController.text.trim(),
          ) ??
          0;

      return propertyValue * rate / 100;
    }

    return double.tryParse(
          _fixedCommissionController.text.trim(),
        ) ??
        0;
  }

  String _formatKes(
    num value,
  ) {
    final whole = value.round();

    final text = whole.toString();

    final formatted = text.replaceAllMapped(
      RegExp(r'\B(?=(\d{3})+(?!\d))'),
      (match) => ',',
    );

    return 'KES $formatted';
  }

  String _serverCommissionLabel() {
    final raw =
        _agreement['expected_total_commission']
            ?.toString();

    final amount = double.tryParse(
      raw ?? '',
    );

    if (amount == null) {
      return _formatKes(
        _previewCommission(),
      );
    }

    return _formatKes(amount);
  }

  String _cleanError(
    Object error,
  ) {
    return error
        .toString()
        .replaceFirst(
          RegExp(r'^Exception:\s*'),
          '',
        )
        .trim();
  }

  String? _validateRequiredText(
    String? value,
    String message,
  ) {
    if (value == null ||
        value.trim().isEmpty) {
      return message;
    }

    return null;
  }

  String? _validatePositiveNumber(
    String? value,
    String message,
  ) {
    final number = double.tryParse(
      value?.trim() ?? '',
    );

    if (number == null ||
        number <= 0) {
      return message;
    }

    return null;
  }

  @override
  Widget build(
    BuildContext context,
  ) {
    return Scaffold(
      backgroundColor:
          const Color(0xFFF6F8F6),
      appBar: AppBar(
        title: const Text(
          'Property Mandate',
        ),
        backgroundColor:
            const Color(0xFF14532D),
        foregroundColor: Colors.white,
      ),
      body: _isLoading
          ? const Center(
              child:
                  CircularProgressIndicator(),
            )
          : RefreshIndicator(
              onRefresh: _loadData,
              child: ListView(
                physics:
                    const AlwaysScrollableScrollPhysics(),
                padding:
                    const EdgeInsets.fromLTRB(
                  16,
                  18,
                  16,
                  36,
                ),
                children: [
                  _PropertySummaryCard(
                    property: property,
                  ),
                  const SizedBox(height: 16),

                  if (_errorMessage != null)
                    _ErrorCard(
                      message:
                          _errorMessage!,
                    ),

                  if (_errorMessage != null)
                    const SizedBox(height: 16),

                  _WorkflowStatusCard(
                    hasAgreement:
                        _hasAgreement,
                    agreementAccepted:
                        _agreementAccepted,
                    agreementVerified:
                        _agreementVerified,
                    agreementLocked:
                        _agreementLocked,
                    hasMandate:
                        _hasMandate,
                    mandateDeclared:
                        _mandateDeclared,
                    mandateStatus:
                        _mandateStatus,
                  ),

                  const SizedBox(height: 18),

                  Form(
                    key: _formKey,
                    child: Column(
                      crossAxisAlignment:
                          CrossAxisAlignment.start,
                      children: [
                        _SectionCard(
                          title:
                              'Owner / Landlord',
                          icon:
                              Icons.person_outline,
                          child: Column(
                            children: [
                              TextFormField(
                                controller:
                                    _ownerNameController,
                                enabled:
                                    !_commercialTermsFrozen,
                                textInputAction:
                                    TextInputAction.next,
                                decoration:
                                    const InputDecoration(
                                  labelText:
                                      'Owner / landlord name',
                                  border:
                                      OutlineInputBorder(),
                                ),
                                validator: (value) =>
                                    _validateRequiredText(
                                  value,
                                  'Enter the owner or landlord name.',
                                ),
                              ),
                              const SizedBox(height: 12),
                              TextFormField(
                                controller:
                                    _ownerPhoneController,
                                enabled:
                                    !_commercialTermsFrozen,
                                keyboardType:
                                    TextInputType.phone,
                                decoration:
                                    const InputDecoration(
                                  labelText:
                                      'Owner / landlord phone',
                                  border:
                                      OutlineInputBorder(),
                                ),
                                validator: (value) =>
                                    _validateRequiredText(
                                  value,
                                  'Enter the owner or landlord phone number.',
                                ),
                              ),
                            ],
                          ),
                        ),

                        const SizedBox(height: 16),

                        _SectionCard(
                          title:
                              'Commission Agreement',
                          icon:
                              Icons.handshake_outlined,
                          child: Column(
                            crossAxisAlignment:
                                CrossAxisAlignment.start,
                            children: [
                              Text(
                                property.formattedPrice,
                                style:
                                    Theme.of(context)
                                        .textTheme
                                        .titleLarge
                                        ?.copyWith(
                                          fontWeight:
                                              FontWeight.w700,
                                        ),
                              ),
                              const SizedBox(height: 4),
                              Text(
                                property.listingType
                                            .toLowerCase() ==
                                        'rent'
                                    ? 'Property rent used for commission calculation.'
                                    : 'Property value used for commission calculation.',
                                style:
                                    const TextStyle(
                                  color:
                                      Colors.black54,
                                ),
                              ),
                              const SizedBox(height: 18),

                              SegmentedButton<String>(
                                segments:
                                    const [
                                  ButtonSegment<String>(
                                    value:
                                        'percentage',
                                    label:
                                        Text(
                                      'Percentage',
                                    ),
                                    icon: Icon(
                                      Icons.percent,
                                    ),
                                  ),
                                  ButtonSegment<String>(
                                    value:
                                        'fixed',
                                    label:
                                        Text(
                                      'Fixed',
                                    ),
                                    icon: Icon(
                                      Icons.payments_outlined,
                                    ),
                                  ),
                                ],
                                selected: {
                                  _commissionMethod,
                                },
                                onSelectionChanged:
                                    _commercialTermsFrozen
                                        ? null
                                        : (selection) {
                                            setState(() {
                                              _commissionMethod =
                                                  selection.first;
                                            });
                                          },
                              ),

                              const SizedBox(height: 16),

                              if (_commissionMethod ==
                                  'percentage')
                                TextFormField(
                                  controller:
                                      _commissionRateController,
                                  enabled:
                                      !_commercialTermsFrozen,
                                  keyboardType:
                                      const TextInputType.numberWithOptions(
                                    decimal: true,
                                  ),
                                  decoration:
                                      const InputDecoration(
                                    labelText:
                                        'Commission rate (%)',
                                    border:
                                        OutlineInputBorder(),
                                  ),
                                  validator: (value) =>
                                      _commissionMethod ==
                                              'percentage'
                                          ? _validatePositiveNumber(
                                              value,
                                              'Enter a commission percentage greater than zero.',
                                            )
                                          : null,
                                )
                              else
                                TextFormField(
                                  controller:
                                      _fixedCommissionController,
                                  enabled:
                                      !_commercialTermsFrozen,
                                  keyboardType:
                                      const TextInputType.numberWithOptions(
                                    decimal: true,
                                  ),
                                  decoration:
                                      const InputDecoration(
                                    labelText:
                                        'Fixed commission (KES)',
                                    border:
                                        OutlineInputBorder(),
                                  ),
                                  validator: (value) =>
                                      _commissionMethod ==
                                              'fixed'
                                          ? _validatePositiveNumber(
                                              value,
                                              'Enter a fixed commission greater than zero.',
                                            )
                                          : null,
                                ),

                              const SizedBox(height: 16),

                              _CommissionPreview(
                                propertyValue:
                                    _formatKes(
                                  _propertyValue(),
                                ),
                                commissionMethod:
                                    _commissionMethod,
                                rate:
                                    _commissionRateController.text
                                        .trim(),
                                commission:
                                    _hasAgreement
                                        ? _serverCommissionLabel()
                                        : _formatKes(
                                            _previewCommission(),
                                          ),
                              ),

                              if (!_commercialTermsFrozen) ...[
                                const SizedBox(height: 16),
                                SizedBox(
                                  width:
                                      double.infinity,
                                  child:
                                      FilledButton.icon(
                                    onPressed:
                                        _isSavingCommission
                                            ? null
                                            : _saveCommission,
                                    icon:
                                        _isSavingCommission
                                            ? const SizedBox(
                                                width:
                                                    18,
                                                height:
                                                    18,
                                                child:
                                                    CircularProgressIndicator(
                                                  strokeWidth:
                                                      2,
                                                ),
                                              )
                                            : const Icon(
                                                Icons.save_outlined,
                                              ),
                                    label: Text(
                                      _isSavingCommission
                                          ? 'Saving...'
                                          : _hasAgreement
                                              ? 'Update Commission Terms'
                                              : 'Save Commission Terms',
                                    ),
                                  ),
                                ),
                              ],

                              if (_hasAgreement &&
                                  !_agreementAccepted) ...[
                                const SizedBox(height: 12),
                                SizedBox(
                                  width:
                                      double.infinity,
                                  child:
                                      FilledButton.icon(
                                    onPressed:
                                        _isAcceptingCommission
                                            ? null
                                            : _acceptCommission,
                                    icon:
                                        _isAcceptingCommission
                                            ? const SizedBox(
                                                width:
                                                    18,
                                                height:
                                                    18,
                                                child:
                                                    CircularProgressIndicator(
                                                  strokeWidth:
                                                      2,
                                                ),
                                              )
                                            : const Icon(
                                                Icons.check_circle_outline,
                                              ),
                                    label: Text(
                                      _isAcceptingCommission
                                          ? 'Accepting...'
                                          : 'Accept Commission',
                                    ),
                                  ),
                                ),
                              ],

                              if (_agreementAccepted)
                                const Padding(
                                  padding:
                                      EdgeInsets.only(
                                    top: 14,
                                  ),
                                  child:
                                      _SuccessBanner(
                                    text:
                                        'Commission terms accepted. These commercial terms can no longer be edited.',
                                  ),
                                ),
                            ],
                          ),
                        ),

                        if (_agreementAccepted) ...[
                          const SizedBox(height: 16),

                          _SectionCard(
                            title:
                                'Digital Property Mandate',
                            icon:
                                Icons.assignment_turned_in_outlined,
                            child: Column(
                              crossAxisAlignment:
                                  CrossAxisAlignment.start,
                              children: [
                                DropdownButtonFormField<String>(
                                  initialValue:
                                      _authorizationMethod,
                                  decoration:
                                      const InputDecoration(
                                    labelText:
                                        'How did the owner authorize you?',
                                    border:
                                        OutlineInputBorder(),
                                  ),
                                  items:
                                      const [
                                    DropdownMenuItem(
                                      value:
                                          'verbal',
                                      child:
                                          Text(
                                        'Verbal authorization',
                                      ),
                                    ),
                                    DropdownMenuItem(
                                      value:
                                          'phone',
                                      child:
                                          Text(
                                        'Phone authorization',
                                      ),
                                    ),
                                    DropdownMenuItem(
                                      value:
                                          'whatsapp',
                                      child:
                                          Text(
                                        'WhatsApp / message',
                                      ),
                                    ),
                                    DropdownMenuItem(
                                      value:
                                          'written',
                                      child:
                                          Text(
                                        'Written authorization',
                                      ),
                                    ),
                                    DropdownMenuItem(
                                      value:
                                          'property_manager',
                                      child:
                                          Text(
                                        'Property management authority',
                                      ),
                                    ),
                                    DropdownMenuItem(
                                      value:
                                          'owner_self',
                                      child:
                                          Text(
                                        'I am the owner',
                                      ),
                                    ),
                                    DropdownMenuItem(
                                      value:
                                          'other',
                                      child:
                                          Text(
                                        'Other',
                                      ),
                                    ),
                                  ],
                                  onChanged:
                                      _mandateDeclared ||
                                              _mandateUnderReview ||
                                              _mandateApproved
                                          ? null
                                          : (value) {
                                              if (value ==
                                                  null) {
                                                return;
                                              }

                                              setState(() {
                                                _authorizationMethod =
                                                    value;
                                              });
                                            },
                                ),

                                const SizedBox(height: 12),

                                TextFormField(
                                  controller:
                                      _authorizationNotesController,
                                  enabled:
                                      !_mandateDeclared &&
                                          !_mandateUnderReview &&
                                          !_mandateApproved,
                                  maxLines: 3,
                                  decoration:
                                      const InputDecoration(
                                    labelText:
                                        'Authorization notes (optional)',
                                    hintText:
                                        'Example: Owner authorized me by phone.',
                                    border:
                                        OutlineInputBorder(),
                                  ),
                                ),

                                if (!_hasMandate) ...[
                                  const SizedBox(height: 16),
                                  SizedBox(
                                    width:
                                        double.infinity,
                                    child:
                                        FilledButton.icon(
                                      onPressed:
                                          _isCreatingMandate
                                              ? null
                                              : _createMandate,
                                      icon:
                                          _isCreatingMandate
                                              ? const SizedBox(
                                                  width:
                                                      18,
                                                  height:
                                                      18,
                                                  child:
                                                      CircularProgressIndicator(
                                                    strokeWidth:
                                                        2,
                                                  ),
                                                )
                                              : const Icon(
                                                  Icons.note_add_outlined,
                                                ),
                                      label: Text(
                                        _isCreatingMandate
                                            ? 'Creating...'
                                            : 'Create Digital Mandate',
                                      ),
                                    ),
                                  ),
                                ],

                                if (_hasMandate &&
                                    !_mandateDeclared) ...[
                                  const SizedBox(height: 18),

                                  CheckboxListTile(
                                    contentPadding:
                                        EdgeInsets.zero,
                                    value:
                                        _authorityConfirmed,
                                    onChanged:
                                        (value) {
                                      setState(() {
                                        _authorityConfirmed =
                                            value ??
                                                false;
                                      });
                                    },
                                    title:
                                        const Text(
                                      'I confirm that I have authority to market this property.',
                                    ),
                                  ),

                                  CheckboxListTile(
                                    contentPadding:
                                        EdgeInsets.zero,
                                    value:
                                        _paymentPolicyAccepted,
                                    onChanged:
                                        (value) {
                                      setState(() {
                                        _paymentPolicyAccepted =
                                            value ??
                                                false;
                                      });
                                    },
                                    title:
                                        const Text(
                                      'I agree to use Pata Hao\'s recorded payment and transaction workflow.',
                                    ),
                                  ),

                                  CheckboxListTile(
                                    contentPadding:
                                        EdgeInsets.zero,
                                    value:
                                        _antiCircumventionAccepted,
                                    onChanged:
                                        (value) {
                                      setState(() {
                                        _antiCircumventionAccepted =
                                            value ??
                                                false;
                                      });
                                    },
                                    title:
                                        const Text(
                                      'I will not knowingly bypass Pata Hao for customers introduced through the platform.',
                                    ),
                                  ),

                                  const SizedBox(height: 10),

                                  SizedBox(
                                    width:
                                        double.infinity,
                                    child:
                                        FilledButton.icon(
                                      onPressed:
                                          _isDeclaringMandate
                                              ? null
                                              : _declareMandate,
                                      icon:
                                          _isDeclaringMandate
                                              ? const SizedBox(
                                                  width:
                                                      18,
                                                  height:
                                                      18,
                                                  child:
                                                      CircularProgressIndicator(
                                                    strokeWidth:
                                                        2,
                                                  ),
                                                )
                                              : const Icon(
                                                  Icons.verified_user_outlined,
                                                ),
                                      label: Text(
                                        _isDeclaringMandate
                                            ? 'Accepting...'
                                            : 'Accept Digital Mandate',
                                      ),
                                    ),
                                  ),
                                ],

                                if (_mandateDeclared &&
                                    !_mandateUnderReview &&
                                    !_mandateApproved) ...[
                                  const SizedBox(height: 16),
                                  const _SuccessBanner(
                                    text:
                                        'Digital mandate accepted. Submit it to Pata Hao for review.',
                                  ),
                                  const SizedBox(height: 12),
                                  SizedBox(
                                    width:
                                        double.infinity,
                                    child:
                                        FilledButton.icon(
                                      onPressed:
                                          _isSubmittingForReview
                                              ? null
                                              : _submitForReview,
                                      icon:
                                          _isSubmittingForReview
                                              ? const SizedBox(
                                                  width:
                                                      18,
                                                  height:
                                                      18,
                                                  child:
                                                      CircularProgressIndicator(
                                                    strokeWidth:
                                                        2,
                                                  ),
                                                )
                                              : const Icon(
                                                  Icons.send_outlined,
                                                ),
                                      label: Text(
                                        _isSubmittingForReview
                                            ? 'Submitting...'
                                            : 'Submit for Pata Hao Review',
                                      ),
                                    ),
                                  ),
                                ],

                                if (_mandateUnderReview)
                                  const Padding(
                                    padding:
                                        EdgeInsets.only(
                                      top: 16,
                                    ),
                                    child:
                                        _InfoBanner(
                                      icon:
                                          Icons.hourglass_top_rounded,
                                      text:
                                          'Your digital mandate is under Pata Hao review.',
                                    ),
                                  ),

                                if (_mandateApproved)
                                  const Padding(
                                    padding:
                                        EdgeInsets.only(
                                      top: 16,
                                    ),
                                    child:
                                        _SuccessBanner(
                                      text:
                                          'Digital mandate approved. Commercial authorization is complete.',
                                    ),
                                  ),
                              ],
                            ),
                          ),
                        ],
                      ],
                    ),
                  ),
                ],
              ),
            ),
    );
  }
}


class _PropertySummaryCard extends StatelessWidget {
  const _PropertySummaryCard({
    required this.property,
  });

  final Property property;

  @override
  Widget build(
    BuildContext context,
  ) {
    return Card(
      child: Padding(
        padding:
            const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment:
              CrossAxisAlignment.start,
          children: [
            Text(
              property.title,
              style:
                  Theme.of(context)
                      .textTheme
                      .titleLarge
                      ?.copyWith(
                        fontWeight:
                            FontWeight.w700,
                      ),
            ),
            const SizedBox(height: 5),
            Text(
              property.locationLabel,
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                Chip(
                  label: Text(
                    property.formattedListingType,
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    property.formattedPrice,
                    textAlign:
                        TextAlign.end,
                    style:
                        const TextStyle(
                      fontWeight:
                          FontWeight.w700,
                    ),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}


class _WorkflowStatusCard extends StatelessWidget {
  const _WorkflowStatusCard({
    required this.hasAgreement,
    required this.agreementAccepted,
    required this.agreementVerified,
    required this.agreementLocked,
    required this.hasMandate,
    required this.mandateDeclared,
    required this.mandateStatus,
  });

  final bool hasAgreement;
  final bool agreementAccepted;
  final bool agreementVerified;
  final bool agreementLocked;
  final bool hasMandate;
  final bool mandateDeclared;
  final String mandateStatus;

  @override
  Widget build(
    BuildContext context,
  ) {
    return Card(
      child: Padding(
        padding:
            const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment:
              CrossAxisAlignment.start,
          children: [
            const Text(
              'Commercial authorization',
              style: TextStyle(
                fontSize: 17,
                fontWeight:
                    FontWeight.w700,
              ),
            ),
            const SizedBox(height: 14),
            _StatusRow(
              label:
                  'Commission terms',
              complete: hasAgreement,
            ),
            _StatusRow(
              label:
                  'Partner accepted commission',
              complete:
                  agreementAccepted,
            ),
            _StatusRow(
              label:
                  'Pata Hao commission review',
              complete:
                  agreementVerified,
            ),
            _StatusRow(
              label:
                  'Commission locked',
              complete:
                  agreementLocked,
            ),
            _StatusRow(
              label:
                  'Digital mandate created',
              complete: hasMandate,
            ),
            _StatusRow(
              label:
                  'Partner accepted mandate',
              complete:
                  mandateDeclared,
            ),
            _StatusRow(
              label:
                  'Mandate submitted / approved',
              complete:
                  mandateStatus ==
                          'under_review' ||
                      mandateStatus ==
                          'approved',
            ),
          ],
        ),
      ),
    );
  }
}


class _StatusRow extends StatelessWidget {
  const _StatusRow({
    required this.label,
    required this.complete,
  });

  final String label;
  final bool complete;

  @override
  Widget build(
    BuildContext context,
  ) {
    return Padding(
      padding:
          const EdgeInsets.symmetric(
        vertical: 4,
      ),
      child: Row(
        children: [
          Icon(
            complete
                ? Icons.check_circle
                : Icons.radio_button_unchecked,
            size: 20,
            color: complete
                ? const Color(0xFF15803D)
                : Colors.black38,
          ),
          const SizedBox(width: 9),
          Expanded(
            child: Text(label),
          ),
        ],
      ),
    );
  }
}


class _CommissionPreview extends StatelessWidget {
  const _CommissionPreview({
    required this.propertyValue,
    required this.commissionMethod,
    required this.rate,
    required this.commission,
  });

  final String propertyValue;
  final String commissionMethod;
  final String rate;
  final String commission;

  @override
  Widget build(
    BuildContext context,
  ) {
    return Container(
      width: double.infinity,
      padding:
          const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color:
            const Color(0xFFF0FDF4),
        borderRadius:
            BorderRadius.circular(14),
        border: Border.all(
          color:
              const Color(0xFFBBF7D0),
        ),
      ),
      child: Column(
        crossAxisAlignment:
            CrossAxisAlignment.start,
        children: [
          const Text(
            'Commission preview',
            style: TextStyle(
              fontWeight:
                  FontWeight.w700,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            'Property value: $propertyValue',
          ),
          if (commissionMethod ==
              'percentage')
            Text(
              'Rate: ${rate.isEmpty ? '—' : '$rate%'}',
            ),
          const SizedBox(height: 8),
          Text(
            commission,
            style:
                const TextStyle(
              fontSize: 22,
              fontWeight:
                  FontWeight.bold,
              color:
                  Color(0xFF14532D),
            ),
          ),
          const SizedBox(height: 4),
          const Text(
            'Commission payable to Pata Hao on a successful transaction.',
            style: TextStyle(
              color:
                  Colors.black54,
            ),
          ),
        ],
      ),
    );
  }
}


class _SectionCard extends StatelessWidget {
  const _SectionCard({
    required this.title,
    required this.icon,
    required this.child,
  });

  final String title;
  final IconData icon;
  final Widget child;

  @override
  Widget build(
    BuildContext context,
  ) {
    return Card(
      child: Padding(
        padding:
            const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment:
              CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(icon),
                const SizedBox(width: 8),
                Text(
                  title,
                  style:
                      const TextStyle(
                    fontSize: 18,
                    fontWeight:
                        FontWeight.w700,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            child,
          ],
        ),
      ),
    );
  }
}


class _SuccessBanner extends StatelessWidget {
  const _SuccessBanner({
    required this.text,
  });

  final String text;

  @override
  Widget build(
    BuildContext context,
  ) {
    return Container(
      width: double.infinity,
      padding:
          const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color:
            const Color(0xFFF0FDF4),
        borderRadius:
            BorderRadius.circular(12),
        border: Border.all(
          color:
              const Color(0xFFBBF7D0),
        ),
      ),
      child: Row(
        crossAxisAlignment:
            CrossAxisAlignment.start,
        children: [
          const Icon(
            Icons.check_circle_outline,
            color:
                Color(0xFF15803D),
          ),
          const SizedBox(width: 9),
          Expanded(
            child: Text(text),
          ),
        ],
      ),
    );
  }
}


class _InfoBanner extends StatelessWidget {
  const _InfoBanner({
    required this.icon,
    required this.text,
  });

  final IconData icon;
  final String text;

  @override
  Widget build(
    BuildContext context,
  ) {
    return Container(
      width: double.infinity,
      padding:
          const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color:
            const Color(0xFFEFF6FF),
        borderRadius:
            BorderRadius.circular(12),
        border: Border.all(
          color:
              const Color(0xFFBFDBFE),
        ),
      ),
      child: Row(
        crossAxisAlignment:
            CrossAxisAlignment.start,
        children: [
          Icon(
            icon,
            color:
                const Color(0xFF1D4ED8),
          ),
          const SizedBox(width: 9),
          Expanded(
            child: Text(text),
          ),
        ],
      ),
    );
  }
}


class _ErrorCard extends StatelessWidget {
  const _ErrorCard({
    required this.message,
  });

  final String message;

  @override
  Widget build(
    BuildContext context,
  ) {
    return Container(
      width: double.infinity,
      padding:
          const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color:
            const Color(0xFFFEF2F2),
        borderRadius:
            BorderRadius.circular(12),
        border: Border.all(
          color:
              const Color(0xFFFECACA),
        ),
      ),
      child: Row(
        crossAxisAlignment:
            CrossAxisAlignment.start,
        children: [
          const Icon(
            Icons.error_outline,
            color:
                Color(0xFFB91C1C),
          ),
          const SizedBox(width: 9),
          Expanded(
            child: Text(message),
          ),
        ],
      ),
    );
  }
}
