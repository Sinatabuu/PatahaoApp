import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';

import 'package:mobile/models/property.dart';
import 'package:mobile/services/partner_mandate_service.dart';

class PartnerPropertyMandateScreen extends StatefulWidget {
  const PartnerPropertyMandateScreen({super.key, required this.property});

  final Property property;

  @override
  State<PartnerPropertyMandateScreen> createState() {
    return _PartnerPropertyMandateScreenState();
  }
}

class _PartnerPropertyMandateScreenState
    extends State<PartnerPropertyMandateScreen> {
  final _formKey = GlobalKey<FormState>();

  final TextEditingController _ownerNameController = TextEditingController();

  final TextEditingController _ownerPhoneController = TextEditingController();

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
  bool _isUploadingEvidence = false;
  String? _uploadingDocumentType;

  String? _errorMessage;

  Map<String, dynamic> _agreement = <String, dynamic>{};
  Map<String, dynamic> _mandate = <String, dynamic>{};
  Map<String, dynamic> _salePack = <String, dynamic>{};

  String _commissionMethod = 'percentage';
  String _commissionBasis = 'first_month_rent';
  String _authorizationMethod = 'phone';

  bool _authorityConfirmed = false;
  bool _paymentPolicyAccepted = false;
  bool _antiCircumventionAccepted = false;

  Property get property => widget.property;

  bool get _isSaleProperty => property.listingType.toLowerCase() == 'sale';

  bool get _hasAgreement => _agreement.isNotEmpty;

  bool get _agreementAccepted => _agreement['partner_accepted'] == true;

  bool get _agreementVerified => _agreement['is_verified'] == true;

  bool get _agreementLocked => _agreement['is_locked'] == true;

  int? get _agreementId => int.tryParse(_agreement['id']?.toString() ?? '');

  bool get _hasMandate => _mandate.isNotEmpty;

  bool get _mandateDeclared => _mandate['partner_declared'] == true;

  int? get _mandateId => int.tryParse(_mandate['id']?.toString() ?? '');

  String get _mandateStatus => _mandate['status']?.toString() ?? '';

  bool get _mandateUnderReview => _mandateStatus == 'under_review';

  bool get _mandateApproved => _mandateStatus == 'approved';

  bool get _commercialTermsFrozen =>
      _agreementAccepted || _agreementVerified || _agreementLocked;

  @override
  void initState() {
    super.initState();

    _commissionRateController.addListener(_rebuildCommissionPreview);

    _fixedCommissionController.addListener(_rebuildCommissionPreview);

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
      final agreement = await PartnerMandateService.instance
          .fetchCommissionAgreementForProperty(property.id);

      final mandate = await PartnerMandateService.instance
          .fetchMandateForProperty(property.id);

      final salePack = await _fetchSalePackForMandate(mandate);

      if (!mounted) {
        return;
      }

      setState(() {
        _agreement = agreement;
        _mandate = mandate;
        _salePack = salePack;

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

  Future<Map<String, dynamic>> _fetchSalePackForMandate(
    Map<String, dynamic> mandateData,
  ) async {
    if (!_isSaleProperty || mandateData.isEmpty) {
      return <String, dynamic>{};
    }

    final mandateId = int.tryParse(mandateData['id']?.toString() ?? '');

    if (mandateId == null || mandateId <= 0) {
      return <String, dynamic>{};
    }

    return PartnerMandateService.instance.fetchSaleMandatePack(mandateId);
  }

  void _hydrateFormFromServer() {
    if (_agreement.isNotEmpty) {
      _ownerNameController.text = _agreement['owner_name']?.toString() ?? '';

      _ownerPhoneController.text =
          _agreement['owner_phone_number']?.toString() ?? '';

      final method = _agreement['commission_method']?.toString() ?? '';

      if (method == 'fixed' || method == 'percentage') {
        _commissionMethod = method;
      }

      final basis = _agreement['commission_basis']?.toString() ?? '';

      if (basis.isNotEmpty) {
        _commissionBasis = basis;
      }

      _commissionRateController.text =
          _agreement['commission_rate']?.toString() ?? '';

      _fixedCommissionController.text =
          _agreement['fixed_commission_amount']?.toString() ?? '';
    }

    if (_mandate.isNotEmpty) {
      final authorizationMethod =
          _mandate['authorization_method']?.toString() ?? '';

      if (authorizationMethod.isNotEmpty) {
        _authorizationMethod = authorizationMethod;
      }

      _authorizationNotesController.text =
          _mandate['authorization_notes']?.toString() ?? '';

      _authorityConfirmed = _mandate['owner_authority_confirmed'] == true;

      _paymentPolicyAccepted = _mandate['no_cash_acknowledged'] == true;

      _antiCircumventionAccepted =
          _mandate['anti_circumvention_acknowledged'] == true;

      final ownerDetail = _mandate['owner_detail'];

      if (ownerDetail is Map) {
        final ownerMap = Map<String, dynamic>.from(ownerDetail);

        if (_ownerNameController.text.trim().isEmpty) {
          _ownerNameController.text = ownerMap['legal_name']?.toString() ?? '';
        }

        if (_ownerPhoneController.text.trim().isEmpty) {
          _ownerPhoneController.text =
              ownerMap['phone_number']?.toString() ?? '';
        }
      }
    }
  }

  Future<void> _saveCommission() async {
    if (_isSavingCommission || _commercialTermsFrozen) {
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
          throw Exception('The commission agreement ID is invalid.');
        }

        result = await PartnerMandateService.instance.updateCommissionAgreement(
          agreementId: agreementId,
          ownerName: _ownerNameController.text,
          ownerPhoneNumber: _ownerPhoneController.text,
          commissionMethod: _commissionMethod,
          commissionBasis: _commissionBasis,
          transactionValue: transactionValue,
          commissionRate: _commissionMethod == 'percentage'
              ? _commissionRateController.text
              : null,
          fixedCommissionAmount: _commissionMethod == 'fixed'
              ? _fixedCommissionController.text
              : null,
        );
      } else {
        result = await PartnerMandateService.instance.createCommissionAgreement(
          propertyId: property.id,
          ownerName: _ownerNameController.text,
          ownerPhoneNumber: _ownerPhoneController.text,
          commissionMethod: _commissionMethod,
          commissionBasis: _commissionBasis,
          transactionValue: transactionValue,
          commissionRate: _commissionMethod == 'percentage'
              ? _commissionRateController.text
              : null,
          fixedCommissionAmount: _commissionMethod == 'fixed'
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

      ScaffoldMessenger.of(
        context,
      ).showSnackBar(const SnackBar(content: Text('Commission terms saved.')));
    } catch (error) {
      if (!mounted) {
        return;
      }

      setState(() {
        _errorMessage = _cleanError(error);
      });

      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(_cleanError(error))));
    } finally {
      if (mounted) {
        setState(() {
          _isSavingCommission = false;
        });
      }
    }
  }

  Future<void> _acceptCommission() async {
    if (_isAcceptingCommission || _agreementAccepted) {
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
          title: const Text('Accept Commission Terms?'),
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
      final result = await PartnerMandateService.instance
          .acceptCommissionAgreement(agreementId);

      if (!mounted) {
        return;
      }

      setState(() {
        _agreement = result;
        _hydrateFormFromServer();
      });

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Commission terms accepted.')),
      );
    } catch (error) {
      if (!mounted) {
        return;
      }

      setState(() {
        _errorMessage = _cleanError(error);
      });

      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(_cleanError(error))));
    } finally {
      if (mounted) {
        setState(() {
          _isAcceptingCommission = false;
        });
      }
    }
  }

  Future<void> _createMandate() async {
    if (_isCreatingMandate || _hasMandate || !_agreementAccepted) {
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
      final result = await PartnerMandateService.instance.createMandate(
        propertyId: property.id,
        ownerName: _ownerNameController.text,
        ownerPhoneNumber: _ownerPhoneController.text,
        commissionAgreementId: agreementId,
        authorizationMethod: _authorizationMethod,
        authorizationNotes: _authorizationNotesController.text,
      );

      if (!mounted) {
        return;
      }

      setState(() {
        _mandate = result;
        _hydrateFormFromServer();
      });

      ScaffoldMessenger.of(
        context,
      ).showSnackBar(const SnackBar(content: Text('Digital mandate created.')));
    } catch (error) {
      if (!mounted) {
        return;
      }

      setState(() {
        _errorMessage = _cleanError(error);
      });

      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(_cleanError(error))));
    } finally {
      if (mounted) {
        setState(() {
          _isCreatingMandate = false;
        });
      }
    }
  }

  Future<void> _declareMandate() async {
    if (_isDeclaringMandate || !_hasMandate || _mandateDeclared) {
      return;
    }

    if (!_authorityConfirmed ||
        !_paymentPolicyAccepted ||
        !_antiCircumventionAccepted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Please accept all three declarations first.'),
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
          title: const Text('Accept Digital Mandate?'),
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
      final result = await PartnerMandateService.instance.declareMandate(
        mandateId: mandateId,
        authorizationMethod: _authorizationMethod,
        authorizationNotes: _authorizationNotesController.text,
      );

      if (!mounted) {
        return;
      }

      setState(() {
        _mandate = result;
        _hydrateFormFromServer();
      });

      await _refreshSalePackFrom(result);

      if (!mounted) {
        return;
      }

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Digital mandate accepted.')),
      );
    } catch (error) {
      if (!mounted) {
        return;
      }

      setState(() {
        _errorMessage = _cleanError(error);
      });

      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(_cleanError(error))));
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
      final result = await PartnerMandateService.instance
          .submitMandateForReview(mandateId);

      if (!mounted) {
        return;
      }

      setState(() {
        _mandate = result;
        _hydrateFormFromServer();
      });

      await _refreshSalePackFrom(result);

      if (!mounted) {
        return;
      }

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Mandate submitted to Pata Hao for review.'),
        ),
      );
    } catch (error) {
      if (!mounted) {
        return;
      }

      setState(() {
        _errorMessage = _cleanError(error);
      });

      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(_cleanError(error))));
    } finally {
      if (mounted) {
        setState(() {
          _isSubmittingForReview = false;
        });
      }
    }
  }

  Future<void> _refreshSalePackFrom(Map<String, dynamic> mandateData) async {
    if (!_isSaleProperty) {
      return;
    }

    try {
      final salePack = await _fetchSalePackForMandate(mandateData);

      if (!mounted) {
        return;
      }

      setState(() {
        _salePack = salePack;
      });
    } catch (error) {
      if (!mounted) {
        return;
      }

      setState(() {
        _errorMessage = _cleanError(error);
      });
    }
  }

  List<Map<String, dynamic>> _salePackSteps() {
    final rawSteps = _salePack['steps'];

    if (rawSteps is! List) {
      return <Map<String, dynamic>>[];
    }

    return rawSteps
        .whereType<Map>()
        .map((step) => Map<String, dynamic>.from(step))
        .toList();
  }

  Map<String, dynamic>? _documentForStep(Map<String, dynamic> step) {
    final rawDocument = step['document'];

    if (rawDocument is! Map) {
      return null;
    }

    return Map<String, dynamic>.from(rawDocument);
  }

  String? _documentTypeForStep(Map<String, dynamic> step) {
    final document = _documentForStep(step);

    final storedType = document?['document_type']?.toString().trim();

    if (storedType != null && storedType.isNotEmpty) {
      return storedType;
    }

    switch (step['key']?.toString()) {
      case 'owner_identity':
        return 'owner_id';
      case 'ownership_proof':
        return 'ownership_proof';
      case 'sale_authority':
        return 'signed_mandate';
      default:
        return null;
    }
  }

  Future<void> _selectAndUploadSalePackEvidence(
    Map<String, dynamic> step,
  ) async {
    if (_isUploadingEvidence) {
      return;
    }

    final documentType = _documentTypeForStep(step);

    if (documentType == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Invalid Sale Pack document type.')),
      );

      return;
    }

    final document = _documentForStep(step);

    final status = document?['status']?.toString() ?? '';

    final replacing = status == 'rejected';

    if (document != null && !replacing) {
      return;
    }

    final documentId = int.tryParse(document?['id']?.toString() ?? '');

    if (replacing && documentId == null) {
      return;
    }

    PlatformFile? selectedFile;

    try {
      selectedFile = await FilePicker.pickFile(
        type: FileType.custom,
        allowedExtensions: const ['pdf', 'jpg', 'jpeg', 'png'],
      );
    } catch (error) {
      if (!mounted) {
        return;
      }

      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(_cleanError(error))));

      return;
    }

    if (selectedFile == null || !mounted) {
      return;
    }

    final fileSize = await selectedFile.length();

    if (!mounted) {
      return;
    }

    if (fileSize > 10 * 1024 * 1024) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Evidence files cannot exceed 10 MB.')),
      );

      return;
    }

    final fileBytes = await selectedFile.readAsBytes();

    if (!mounted) {
      return;
    }

    if (fileBytes.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('The selected file could not be read.')),
      );

      return;
    }

    final label = step['label']?.toString() ?? 'Sale Pack evidence';

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) {
        return AlertDialog(
          title: Text(
            replacing ? 'Replace rejected evidence?' : 'Upload evidence?',
          ),
          content: Text(
            'Step: $label\n'
            'File: ${selectedFile!.name}\n\n'
            '${replacing ? 'The rejected version will remain preserved. ' : ''}'
            'The uploaded file will require fresh Pata Hao approval.',
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
              child: Text(replacing ? 'Replace Evidence' : 'Upload Evidence'),
            ),
          ],
        );
      },
    );

    if (confirmed != true || !mounted) {
      return;
    }

    final mandateId = _mandateId;

    if (mandateId == null) {
      return;
    }

    setState(() {
      _isUploadingEvidence = true;
      _uploadingDocumentType = documentType;
      _errorMessage = null;
    });

    try {
      late final Map<String, dynamic> updatedSalePack;

      if (replacing) {
        updatedSalePack = await PartnerMandateService.instance
            .replaceRejectedSalePackDocument(
              mandateId: mandateId,
              documentId: documentId!,
              filename: selectedFile.name,
              fileBytes: fileBytes,
            );
      } else {
        updatedSalePack = await PartnerMandateService.instance
            .uploadSalePackDocument(
              mandateId: mandateId,
              documentType: documentType,
              filename: selectedFile.name,
              fileBytes: fileBytes,
            );
      }

      if (!mounted) {
        return;
      }

      setState(() {
        _salePack = updatedSalePack;
      });

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            replacing
                ? 'Replacement uploaded. Fresh approval is required.'
                : 'Evidence uploaded for Pata Hao review.',
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

      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(_cleanError(error))));
    } finally {
      if (mounted) {
        setState(() {
          _isUploadingEvidence = false;
          _uploadingDocumentType = null;
        });
      }
    }
  }

  String _salePackCheckLabel(String key) {
    switch (key) {
      case 'document_approved':
        return 'Evidence approved by Pata Hao';
      case 'owner_verified':
        return 'Property owner verified';
      case 'partner_declared':
        return 'Partner accepted digital mandate';
      case 'commission_agreement_ready':
        return 'Commission agreement approved and locked';
      default:
        return key.replaceAll('_', ' ');
    }
  }

  Widget _buildSalePackCard() {
    final steps = _salePackSteps();

    final completedSteps =
        int.tryParse(_salePack['completed_steps']?.toString() ?? '') ?? 0;

    final totalSteps =
        int.tryParse(_salePack['total_steps']?.toString() ?? '') ??
        steps.length;

    final progress = totalSteps > 0
        ? (completedSteps / totalSteps).clamp(0.0, 1.0).toDouble()
        : 0.0;

    final packComplete = _salePack['pack_complete'] == true;

    final publicationAllowed = _salePack['publication_allowed'] == true;

    final reasons = <String>[];
    final rawReasons = _salePack['blocking_reasons'];

    if (rawReasons is List) {
      for (final reason in rawReasons) {
        final text = reason.toString().trim();

        if (text.isNotEmpty) {
          reasons.add(text);
        }
      }
    }

    return _SectionCard(
      title: 'Sale Mandate Pack',
      icon: Icons.folder_copy_outlined,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            '$completedSteps of $totalSteps steps complete',
            style: const TextStyle(fontWeight: FontWeight.w700),
          ),
          const SizedBox(height: 8),
          LinearProgressIndicator(
            value: progress,
            minHeight: 8,
            borderRadius: BorderRadius.circular(8),
          ),
          const SizedBox(height: 9),
          const Text(
            'PDF, JPG, JPEG or PNG • Maximum 10 MB',
            style: TextStyle(color: Colors.black54),
          ),
          const SizedBox(height: 14),
          if (packComplete && publicationAllowed)
            const _SuccessBanner(
              text:
                  'The Sale Mandate Pack is complete and the publication gate is satisfied.',
            )
          else if (packComplete)
            const _InfoBanner(
              icon: Icons.admin_panel_settings_outlined,
              text:
                  'All three evidence steps are complete. Other administrative checks are still pending.',
            )
          else
            const _InfoBanner(
              icon: Icons.fact_check_outlined,
              text:
                  'Upload missing evidence. Every uploaded file requires Pata Hao approval.',
            ),
          const SizedBox(height: 14),
          if (steps.isEmpty)
            const _InfoBanner(
              icon: Icons.sync,
              text: 'Sale Pack status is loading. Pull down to refresh.',
            )
          else
            ...steps.map(
              (step) => Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: _buildSalePackStep(step),
              ),
            ),
          if (reasons.isNotEmpty)
            _InfoBanner(
              icon: Icons.lock_outline,
              text:
                  'Still blocking publication:\n'
                  '${reasons.map((reason) => '• $reason').join('\n')}',
            ),
        ],
      ),
    );
  }

  Widget _buildSalePackStep(Map<String, dynamic> step) {
    final document = _documentForStep(step);

    final documentType = _documentTypeForStep(step);

    final status = document?['status']?.toString() ?? '';

    final statusDisplay = document?['status_display']?.toString() ?? '';

    final filename = document?['original_filename']?.toString() ?? '';

    final rejectionReason =
        document?['rejection_reason']?.toString().trim() ?? '';

    final completed = step['completed'] == true;

    final rejected = status == 'rejected';

    final missing = document == null;

    final uploadingThis =
        _isUploadingEvidence && _uploadingDocumentType == documentType;

    final rawChecks = step['checks'];

    final checks = rawChecks is Map
        ? Map<String, dynamic>.from(rawChecks)
        : <String, dynamic>{};

    final icon = completed
        ? Icons.check_circle
        : rejected
        ? Icons.cancel
        : missing
        ? Icons.upload_file
        : Icons.hourglass_top;

    final iconColor = completed
        ? const Color(0xFF15803D)
        : rejected
        ? const Color(0xFFB91C1C)
        : const Color(0xFFD97706);

    final borderColor = completed
        ? const Color(0xFFBBF7D0)
        : rejected
        ? const Color(0xFFFECACA)
        : const Color(0xFFFDE68A);

    final backgroundColor = completed
        ? const Color(0xFFF0FDF4)
        : rejected
        ? const Color(0xFFFEF2F2)
        : const Color(0xFFFFFBEB);

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: backgroundColor,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: borderColor),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(icon, color: iconColor),
              const SizedBox(width: 9),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      step['label']?.toString() ?? 'Sale Pack step',
                      style: const TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: 3),
                    Text(
                      missing
                          ? 'Evidence not uploaded'
                          : statusDisplay.isNotEmpty
                          ? statusDisplay
                          : status,
                      style: TextStyle(
                        color: iconColor,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          if (filename.isNotEmpty) ...[
            const SizedBox(height: 10),
            Text('File: $filename'),
          ],
          if (checks.isNotEmpty) ...[
            const SizedBox(height: 8),
            ...checks.entries.map(
              (entry) => _StatusRow(
                label: _salePackCheckLabel(entry.key),
                complete: entry.value == true,
              ),
            ),
          ],
          if (rejectionReason.isNotEmpty) ...[
            const SizedBox(height: 10),
            _ErrorCard(message: 'Rejection reason: $rejectionReason'),
          ],
          if (missing || rejected) ...[
            const SizedBox(height: 12),
            SizedBox(
              width: double.infinity,
              child: OutlinedButton.icon(
                onPressed: _isUploadingEvidence || documentType == null
                    ? null
                    : () {
                        _selectAndUploadSalePackEvidence(step);
                      },
                icon: uploadingThis
                    ? const SizedBox(
                        width: 18,
                        height: 18,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : Icon(
                        rejected ? Icons.refresh : Icons.upload_file_outlined,
                      ),
                label: Text(
                  uploadingThis
                      ? 'Uploading...'
                      : rejected
                      ? 'Replace Rejected Evidence'
                      : 'Upload Evidence',
                ),
              ),
            ),
          ] else if (status == 'uploaded' || status == 'under_review') ...[
            const SizedBox(height: 10),
            const _InfoBanner(
              icon: Icons.hourglass_top_rounded,
              text: 'Waiting for Pata Hao administrator review.',
            ),
          ],
        ],
      ),
    );
  }

  double _propertyValue() {
    return double.tryParse(property.price.trim()) ?? 0;
  }

  double _previewCommission() {
    final propertyValue = _propertyValue();

    if (_commissionMethod == 'percentage') {
      final rate = double.tryParse(_commissionRateController.text.trim()) ?? 0;

      return propertyValue * rate / 100;
    }

    return double.tryParse(_fixedCommissionController.text.trim()) ?? 0;
  }

  String _formatKes(num value) {
    final whole = value.round();

    final text = whole.toString();

    final formatted = text.replaceAllMapped(
      RegExp(r'\B(?=(\d{3})+(?!\d))'),
      (match) => ',',
    );

    return 'KES $formatted';
  }

  String _serverCommissionLabel() {
    final raw = _agreement['expected_total_commission']?.toString();

    final amount = double.tryParse(raw ?? '');

    if (amount == null) {
      return _formatKes(_previewCommission());
    }

    return _formatKes(amount);
  }

  String _cleanError(Object error) {
    return error.toString().replaceFirst(RegExp(r'^Exception:\s*'), '').trim();
  }

  String? _validateRequiredText(String? value, String message) {
    if (value == null || value.trim().isEmpty) {
      return message;
    }

    return null;
  }

  String? _validatePositiveNumber(String? value, String message) {
    final number = double.tryParse(value?.trim() ?? '');

    if (number == null || number <= 0) {
      return message;
    }

    return null;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF6F8F6),
      appBar: AppBar(
        title: const Text('Property Mandate'),
        backgroundColor: const Color(0xFF14532D),
        foregroundColor: Colors.white,
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _loadData,
              child: ListView(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: const EdgeInsets.fromLTRB(16, 18, 16, 36),
                children: [
                  _PropertySummaryCard(property: property),
                  const SizedBox(height: 16),

                  if (_errorMessage != null)
                    _ErrorCard(message: _errorMessage!),

                  if (_errorMessage != null) const SizedBox(height: 16),

                  _WorkflowStatusCard(
                    hasAgreement: _hasAgreement,
                    agreementAccepted: _agreementAccepted,
                    agreementVerified: _agreementVerified,
                    agreementLocked: _agreementLocked,
                    hasMandate: _hasMandate,
                    mandateDeclared: _mandateDeclared,
                    mandateStatus: _mandateStatus,
                  ),

                  const SizedBox(height: 18),

                  if (_isSaleProperty && _hasMandate) ...[
                    _buildSalePackCard(),
                    const SizedBox(height: 18),
                  ],

                  Form(
                    key: _formKey,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        _SectionCard(
                          title: 'Owner / Landlord',
                          icon: Icons.person_outline,
                          child: Column(
                            children: [
                              TextFormField(
                                controller: _ownerNameController,
                                enabled: !_commercialTermsFrozen,
                                textInputAction: TextInputAction.next,
                                decoration: const InputDecoration(
                                  labelText: 'Owner / landlord name',
                                  border: OutlineInputBorder(),
                                ),
                                validator: (value) => _validateRequiredText(
                                  value,
                                  'Enter the owner or landlord name.',
                                ),
                              ),
                              const SizedBox(height: 12),
                              TextFormField(
                                controller: _ownerPhoneController,
                                enabled: !_commercialTermsFrozen,
                                keyboardType: TextInputType.phone,
                                decoration: const InputDecoration(
                                  labelText: 'Owner / landlord phone',
                                  border: OutlineInputBorder(),
                                ),
                                validator: (value) => _validateRequiredText(
                                  value,
                                  'Enter the owner or landlord phone number.',
                                ),
                              ),
                            ],
                          ),
                        ),

                        const SizedBox(height: 16),

                        _SectionCard(
                          title: 'Commission Agreement',
                          icon: Icons.handshake_outlined,
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                property.formattedPrice,
                                style: Theme.of(context).textTheme.titleLarge
                                    ?.copyWith(fontWeight: FontWeight.w700),
                              ),
                              const SizedBox(height: 4),
                              Text(
                                property.listingType.toLowerCase() == 'rent'
                                    ? 'Property rent used for commission calculation.'
                                    : 'Property value used for commission calculation.',
                                style: const TextStyle(color: Colors.black54),
                              ),
                              const SizedBox(height: 18),

                              SegmentedButton<String>(
                                segments: const [
                                  ButtonSegment<String>(
                                    value: 'percentage',
                                    label: Text('Percentage'),
                                    icon: Icon(Icons.percent),
                                  ),
                                  ButtonSegment<String>(
                                    value: 'fixed',
                                    label: Text('Fixed'),
                                    icon: Icon(Icons.payments_outlined),
                                  ),
                                ],
                                selected: {_commissionMethod},
                                onSelectionChanged: _commercialTermsFrozen
                                    ? null
                                    : (selection) {
                                        setState(() {
                                          _commissionMethod = selection.first;
                                        });
                                      },
                              ),

                              const SizedBox(height: 16),

                              if (_commissionMethod == 'percentage')
                                TextFormField(
                                  controller: _commissionRateController,
                                  enabled: !_commercialTermsFrozen,
                                  keyboardType:
                                      const TextInputType.numberWithOptions(
                                        decimal: true,
                                      ),
                                  decoration: const InputDecoration(
                                    labelText: 'Commission rate (%)',
                                    border: OutlineInputBorder(),
                                  ),
                                  validator: (value) =>
                                      _commissionMethod == 'percentage'
                                      ? _validatePositiveNumber(
                                          value,
                                          'Enter a commission percentage greater than zero.',
                                        )
                                      : null,
                                )
                              else
                                TextFormField(
                                  controller: _fixedCommissionController,
                                  enabled: !_commercialTermsFrozen,
                                  keyboardType:
                                      const TextInputType.numberWithOptions(
                                        decimal: true,
                                      ),
                                  decoration: const InputDecoration(
                                    labelText: 'Fixed commission (KES)',
                                    border: OutlineInputBorder(),
                                  ),
                                  validator: (value) =>
                                      _commissionMethod == 'fixed'
                                      ? _validatePositiveNumber(
                                          value,
                                          'Enter a fixed commission greater than zero.',
                                        )
                                      : null,
                                ),

                              const SizedBox(height: 16),

                              _CommissionPreview(
                                propertyValue: _formatKes(_propertyValue()),
                                commissionMethod: _commissionMethod,
                                rate: _commissionRateController.text.trim(),
                                commission: _hasAgreement
                                    ? _serverCommissionLabel()
                                    : _formatKes(_previewCommission()),
                              ),

                              if (!_commercialTermsFrozen) ...[
                                const SizedBox(height: 16),
                                SizedBox(
                                  width: double.infinity,
                                  child: FilledButton.icon(
                                    onPressed: _isSavingCommission
                                        ? null
                                        : _saveCommission,
                                    icon: _isSavingCommission
                                        ? const SizedBox(
                                            width: 18,
                                            height: 18,
                                            child: CircularProgressIndicator(
                                              strokeWidth: 2,
                                            ),
                                          )
                                        : const Icon(Icons.save_outlined),
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

                              if (_hasAgreement && !_agreementAccepted) ...[
                                const SizedBox(height: 12),
                                SizedBox(
                                  width: double.infinity,
                                  child: FilledButton.icon(
                                    onPressed: _isAcceptingCommission
                                        ? null
                                        : _acceptCommission,
                                    icon: _isAcceptingCommission
                                        ? const SizedBox(
                                            width: 18,
                                            height: 18,
                                            child: CircularProgressIndicator(
                                              strokeWidth: 2,
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
                                  padding: EdgeInsets.only(top: 14),
                                  child: _SuccessBanner(
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
                            title: 'Digital Property Mandate',
                            icon: Icons.assignment_turned_in_outlined,
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                DropdownButtonFormField<String>(
                                  initialValue: _authorizationMethod,
                                  decoration: const InputDecoration(
                                    labelText:
                                        'How did the owner authorize you?',
                                    border: OutlineInputBorder(),
                                  ),
                                  items: const [
                                    DropdownMenuItem(
                                      value: 'verbal',
                                      child: Text('Verbal authorization'),
                                    ),
                                    DropdownMenuItem(
                                      value: 'phone',
                                      child: Text('Phone authorization'),
                                    ),
                                    DropdownMenuItem(
                                      value: 'whatsapp',
                                      child: Text('WhatsApp / message'),
                                    ),
                                    DropdownMenuItem(
                                      value: 'written',
                                      child: Text('Written authorization'),
                                    ),
                                    DropdownMenuItem(
                                      value: 'property_manager',
                                      child: Text(
                                        'Property management authority',
                                      ),
                                    ),
                                    DropdownMenuItem(
                                      value: 'owner_self',
                                      child: Text('I am the owner'),
                                    ),
                                    DropdownMenuItem(
                                      value: 'other',
                                      child: Text('Other'),
                                    ),
                                  ],
                                  onChanged:
                                      _mandateDeclared ||
                                          _mandateUnderReview ||
                                          _mandateApproved
                                      ? null
                                      : (value) {
                                          if (value == null) {
                                            return;
                                          }

                                          setState(() {
                                            _authorizationMethod = value;
                                          });
                                        },
                                ),

                                const SizedBox(height: 12),

                                TextFormField(
                                  controller: _authorizationNotesController,
                                  enabled:
                                      !_mandateDeclared &&
                                      !_mandateUnderReview &&
                                      !_mandateApproved,
                                  maxLines: 3,
                                  decoration: const InputDecoration(
                                    labelText: 'Authorization notes (optional)',
                                    hintText:
                                        'Example: Owner authorized me by phone.',
                                    border: OutlineInputBorder(),
                                  ),
                                ),

                                if (!_hasMandate) ...[
                                  const SizedBox(height: 16),
                                  SizedBox(
                                    width: double.infinity,
                                    child: FilledButton.icon(
                                      onPressed: _isCreatingMandate
                                          ? null
                                          : _createMandate,
                                      icon: _isCreatingMandate
                                          ? const SizedBox(
                                              width: 18,
                                              height: 18,
                                              child: CircularProgressIndicator(
                                                strokeWidth: 2,
                                              ),
                                            )
                                          : const Icon(Icons.note_add_outlined),
                                      label: Text(
                                        _isCreatingMandate
                                            ? 'Creating...'
                                            : 'Create Digital Mandate',
                                      ),
                                    ),
                                  ),
                                ],

                                if (_hasMandate && !_mandateDeclared) ...[
                                  const SizedBox(height: 18),

                                  CheckboxListTile(
                                    contentPadding: EdgeInsets.zero,
                                    value: _authorityConfirmed,
                                    onChanged: (value) {
                                      setState(() {
                                        _authorityConfirmed = value ?? false;
                                      });
                                    },
                                    title: const Text(
                                      'I confirm that I have authority to market this property.',
                                    ),
                                  ),

                                  CheckboxListTile(
                                    contentPadding: EdgeInsets.zero,
                                    value: _paymentPolicyAccepted,
                                    onChanged: (value) {
                                      setState(() {
                                        _paymentPolicyAccepted = value ?? false;
                                      });
                                    },
                                    title: const Text(
                                      'I agree to use Pata Hao\'s recorded payment and transaction workflow.',
                                    ),
                                  ),

                                  CheckboxListTile(
                                    contentPadding: EdgeInsets.zero,
                                    value: _antiCircumventionAccepted,
                                    onChanged: (value) {
                                      setState(() {
                                        _antiCircumventionAccepted =
                                            value ?? false;
                                      });
                                    },
                                    title: const Text(
                                      'I will not knowingly bypass Pata Hao for customers introduced through the platform.',
                                    ),
                                  ),

                                  const SizedBox(height: 10),

                                  SizedBox(
                                    width: double.infinity,
                                    child: FilledButton.icon(
                                      onPressed: _isDeclaringMandate
                                          ? null
                                          : _declareMandate,
                                      icon: _isDeclaringMandate
                                          ? const SizedBox(
                                              width: 18,
                                              height: 18,
                                              child: CircularProgressIndicator(
                                                strokeWidth: 2,
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
                                    width: double.infinity,
                                    child: FilledButton.icon(
                                      onPressed: _isSubmittingForReview
                                          ? null
                                          : _submitForReview,
                                      icon: _isSubmittingForReview
                                          ? const SizedBox(
                                              width: 18,
                                              height: 18,
                                              child: CircularProgressIndicator(
                                                strokeWidth: 2,
                                              ),
                                            )
                                          : const Icon(Icons.send_outlined),
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
                                    padding: EdgeInsets.only(top: 16),
                                    child: _InfoBanner(
                                      icon: Icons.hourglass_top_rounded,
                                      text:
                                          'Your digital mandate is under Pata Hao review.',
                                    ),
                                  ),

                                if (_mandateApproved)
                                  const Padding(
                                    padding: EdgeInsets.only(top: 16),
                                    child: _SuccessBanner(
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
  const _PropertySummaryCard({required this.property});

  final Property property;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              property.title,
              style: Theme.of(
                context,
              ).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: 5),
            Text(property.locationLabel),
            const SizedBox(height: 8),
            Row(
              children: [
                Chip(label: Text(property.formattedListingType)),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    property.formattedPrice,
                    textAlign: TextAlign.end,
                    style: const TextStyle(fontWeight: FontWeight.w700),
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
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Commercial authorization',
              style: TextStyle(fontSize: 17, fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: 14),
            _StatusRow(label: 'Commission terms', complete: hasAgreement),
            _StatusRow(
              label: 'Partner accepted commission',
              complete: agreementAccepted,
            ),
            _StatusRow(
              label: 'Pata Hao commission review',
              complete: agreementVerified,
            ),
            _StatusRow(label: 'Commission locked', complete: agreementLocked),
            _StatusRow(label: 'Digital mandate created', complete: hasMandate),
            _StatusRow(
              label: 'Partner accepted mandate',
              complete: mandateDeclared,
            ),
            _StatusRow(
              label: 'Mandate submitted / approved',
              complete:
                  mandateStatus == 'under_review' ||
                  mandateStatus == 'approved',
            ),
          ],
        ),
      ),
    );
  }
}

class _StatusRow extends StatelessWidget {
  const _StatusRow({required this.label, required this.complete});

  final String label;
  final bool complete;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          Icon(
            complete ? Icons.check_circle : Icons.radio_button_unchecked,
            size: 20,
            color: complete ? const Color(0xFF15803D) : Colors.black38,
          ),
          const SizedBox(width: 9),
          Expanded(child: Text(label)),
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
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFFF0FDF4),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: const Color(0xFFBBF7D0)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Commission preview',
            style: TextStyle(fontWeight: FontWeight.w700),
          ),
          const SizedBox(height: 8),
          Text('Property value: $propertyValue'),
          if (commissionMethod == 'percentage')
            Text('Rate: ${rate.isEmpty ? '—' : '$rate%'}'),
          const SizedBox(height: 8),
          Text(
            commission,
            style: const TextStyle(
              fontSize: 22,
              fontWeight: FontWeight.bold,
              color: Color(0xFF14532D),
            ),
          ),
          const SizedBox(height: 4),
          const Text(
            'Commission payable to Pata Hao on a successful transaction.',
            style: TextStyle(color: Colors.black54),
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
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(icon),
                const SizedBox(width: 8),
                Text(
                  title,
                  style: const TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.w700,
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
  const _SuccessBanner({required this.text});

  final String text;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: const Color(0xFFF0FDF4),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFFBBF7D0)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Icon(Icons.check_circle_outline, color: Color(0xFF15803D)),
          const SizedBox(width: 9),
          Expanded(child: Text(text)),
        ],
      ),
    );
  }
}

class _InfoBanner extends StatelessWidget {
  const _InfoBanner({required this.icon, required this.text});

  final IconData icon;
  final String text;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: const Color(0xFFEFF6FF),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFFBFDBFE)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: const Color(0xFF1D4ED8)),
          const SizedBox(width: 9),
          Expanded(child: Text(text)),
        ],
      ),
    );
  }
}

class _ErrorCard extends StatelessWidget {
  const _ErrorCard({required this.message});

  final String message;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: const Color(0xFFFEF2F2),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFFFECACA)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Icon(Icons.error_outline, color: Color(0xFFB91C1C)),
          const SizedBox(width: 9),
          Expanded(child: Text(message)),
        ],
      ),
    );
  }
}
