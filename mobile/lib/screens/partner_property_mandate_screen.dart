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
  bool _isSavingAuthorization = false;
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

  bool _authorizationAccepted = false;

  Property get property => widget.property;

  bool get _isSaleProperty => property.listingType.toLowerCase() == 'sale';

  bool get _hasAgreement => _agreement.isNotEmpty;

  bool get _agreementAccepted => _agreement['partner_accepted'] == true;

  bool get _hasMandate => _mandate.isNotEmpty;

  bool get _mandateDeclared => _mandate['partner_declared'] == true;

  int? get _mandateId => int.tryParse(_mandate['id']?.toString() ?? '');

  String get _mandateStatus => _mandate['status']?.toString() ?? '';

  bool get _mandateUnderReview => _mandateStatus == 'under_review';

  bool get _mandateApproved => _mandateStatus == 'approved';

  bool get _commercialTermsFrozen =>
      _agreementAccepted ||
      _agreement['is_verified'] == true ||
      _agreement['is_locked'] == true;

  bool get _authorizationComplete =>
      _agreementAccepted && _mandateDeclared;

  bool get _saleDocumentsAdded {
    if (!_isSaleProperty) {
      return true;
    }

    final steps = _salePackSteps();

    return steps.isNotEmpty &&
        steps.every((step) {
          final document = _documentForStep(step);

          return document != null &&
              document['status']?.toString() != 'rejected';
        });
  }

  @override
  void initState() {
    super.initState();

    if (_isSaleProperty) {
      _commissionBasis = 'sale_price';
    }

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

      _authorizationAccepted =
          _mandate['owner_authority_confirmed'] == true &&
          _mandate['no_cash_acknowledged'] == true &&
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

  Future<void> _saveAuthorization() async {
    if (_isSavingAuthorization || _authorizationComplete) {
      return;
    }

    final formState = _formKey.currentState;

    if (formState == null || !formState.validate()) {
      return;
    }

    if (!_authorizationAccepted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Confirm the authorization declaration to continue.'),
        ),
      );

      return;
    }

    setState(() {
      _isSavingAuthorization = true;
      _errorMessage = null;
    });

    try {
      Map<String, dynamic> agreement = _agreement;

      if (agreement['partner_accepted'] != true) {
        if (agreement.isEmpty) {
          agreement = await PartnerMandateService.instance
              .createCommissionAgreement(
                propertyId: property.id,
                ownerName: _ownerNameController.text,
                ownerPhoneNumber: _ownerPhoneController.text,
                commissionMethod: _commissionMethod,
                commissionBasis: _commissionBasis,
                transactionValue: property.price.trim(),
                commissionRate: _commissionMethod == 'percentage'
                    ? _commissionRateController.text
                    : null,
                fixedCommissionAmount: _commissionMethod == 'fixed'
                    ? _fixedCommissionController.text
                    : null,
              );
        } else {
          final agreementId = int.tryParse(
            agreement['id']?.toString() ?? '',
          );

          if (agreementId == null) {
            throw Exception('The commission agreement ID is invalid.');
          }

          agreement = await PartnerMandateService.instance
              .updateCommissionAgreement(
                agreementId: agreementId,
                ownerName: _ownerNameController.text,
                ownerPhoneNumber: _ownerPhoneController.text,
                commissionMethod: _commissionMethod,
                commissionBasis: _commissionBasis,
                transactionValue: property.price.trim(),
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
          _agreement = agreement;
        });

        final agreementId = int.tryParse(
          agreement['id']?.toString() ?? '',
        );

        if (agreementId == null) {
          throw Exception('The commission agreement ID is invalid.');
        }

        agreement = await PartnerMandateService.instance
            .acceptCommissionAgreement(agreementId);

        if (!mounted) {
          return;
        }

        setState(() {
          _agreement = agreement;
          _hydrateFormFromServer();
        });
      }

      final agreementId = int.tryParse(
        agreement['id']?.toString() ?? '',
      );

      if (agreementId == null) {
        throw Exception('The commission agreement ID is invalid.');
      }

      Map<String, dynamic> mandate = _mandate;

      if (mandate.isEmpty) {
        mandate = await PartnerMandateService.instance.createMandate(
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
          _mandate = mandate;
        });
      }

      if (mandate['partner_declared'] != true) {
        final mandateId = int.tryParse(
          mandate['id']?.toString() ?? '',
        );

        if (mandateId == null) {
          throw Exception('The property mandate ID is invalid.');
        }

        mandate = await PartnerMandateService.instance.declareMandate(
          mandateId: mandateId,
          authorizationMethod: _authorizationMethod,
          authorizationNotes: _authorizationNotesController.text,
        );
      }

      if (!mounted) {
        return;
      }

      setState(() {
        _agreement = agreement;
        _mandate = mandate;
        _authorizationAccepted = true;
        _hydrateFormFromServer();
      });

      await _refreshSalePackFrom(mandate);

      if (!mounted) {
        return;
      }

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            _isSaleProperty
                ? 'Authorization saved. Add the three sale documents next.'
                : 'Authorization saved. Submit it for Pata Hao review.',
          ),
        ),
      );
    } catch (error) {
      if (!mounted) {
        return;
      }

      final message = _cleanError(error);

      await _loadData();

      if (!mounted) {
        return;
      }

      if (_authorizationComplete) {
        setState(() {
          _errorMessage = null;
        });

        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Saved authorization recovered. You can continue.'),
          ),
        );
      } else {
        setState(() {
          _errorMessage = message;
        });

        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text(message)));
      }
    } finally {
      if (mounted) {
        setState(() {
          _isSavingAuthorization = false;
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
          content: Text('Authorization submitted to Pata Hao for review.'),
        ),
      );
    } catch (error) {
      if (!mounted) {
        return;
      }

      final message = _cleanError(error);

      await _loadData();

      if (!mounted) {
        return;
      }

      if (_mandateUnderReview || _mandateApproved) {
        setState(() {
          _errorMessage = null;
        });

        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Submission recovered. Pata Hao review has started.'),
          ),
        );
      } else {
        setState(() {
          _errorMessage = message;
        });

        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text(message)));
      }
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

  Widget _buildSalePackCard() {
    final steps = _salePackSteps();

    final documentsAdded = steps.where((step) {
      final document = _documentForStep(step);

      return document != null &&
          document['status']?.toString() != 'rejected';
    }).length;

    final totalDocuments = steps.length;
    final progress = totalDocuments > 0
        ? documentsAdded / totalDocuments
        : 0.0;

    return _SectionCard(
      title: 'Sale documents',
      icon: Icons.folder_copy_outlined,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            '$documentsAdded of $totalDocuments documents added',
            style: const TextStyle(fontWeight: FontWeight.w700),
          ),
          const SizedBox(height: 8),
          LinearProgressIndicator(
            value: progress,
            minHeight: 8,
            borderRadius: BorderRadius.circular(8),
          ),
          const SizedBox(height: 10),
          const Text(
            'Add owner ID, ownership proof, and signed sale authority. '
            'PDF, JPG, JPEG or PNG; maximum 10 MB each.',
            style: TextStyle(color: Colors.black54, height: 1.4),
          ),
          const SizedBox(height: 14),
          if (steps.isEmpty)
            const _InfoBanner(
              icon: Icons.sync,
              text: 'Document checklist is loading. Pull down to refresh.',
            )
          else
            ...steps.map(
              (step) => Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: _buildSalePackStep(step),
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildSalePackStep(Map<String, dynamic> step) {
    final document = _documentForStep(step);
    final documentType = _documentTypeForStep(step);
    final status = document?['status']?.toString() ?? '';
    final filename = document?['original_filename']?.toString() ?? '';
    final rejectionReason =
        document?['rejection_reason']?.toString().trim() ?? '';

    final rejected = status == 'rejected';
    final approved = status == 'approved';
    final missing = document == null;
    final uploadingThis =
        _isUploadingEvidence && _uploadingDocumentType == documentType;

    final icon = approved
        ? Icons.check_circle
        : rejected
        ? Icons.error_outline
        : missing
        ? Icons.upload_file_outlined
        : Icons.schedule;

    final iconColor = approved
        ? const Color(0xFF15803D)
        : rejected
        ? const Color(0xFFB91C1C)
        : missing
        ? const Color(0xFFD97706)
        : const Color(0xFF1D4ED8);

    final statusText = approved
        ? 'Approved'
        : rejected
        ? 'Needs replacement'
        : missing
        ? 'Required'
        : 'Added';

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: const Color(0xFFFFFFFF),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: iconColor.withAlpha(90)),
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
                      step['label']?.toString() ?? 'Sale document',
                      style: const TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: 3),
                    Text(
                      statusText,
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
            const SizedBox(height: 8),
            Text(
              filename,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(color: Colors.black54),
            ),
          ],
          if (rejectionReason.isNotEmpty) ...[
            const SizedBox(height: 10),
            _ErrorCard(message: rejectionReason),
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
                    : Icon(rejected ? Icons.refresh : Icons.upload_file),
                label: Text(
                  uploadingThis
                      ? 'Uploading...'
                      : rejected
                      ? 'Replace document'
                      : 'Add document',
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildReviewCard() {
    if (_mandateApproved) {
      return const _SectionCard(
        title: 'Pata Hao review',
        icon: Icons.verified_outlined,
        child: _SuccessBanner(
          text: 'Authorization approved. This protection step is complete.',
        ),
      );
    }

    if (_mandateUnderReview) {
      return const _SectionCard(
        title: 'Pata Hao review',
        icon: Icons.hourglass_top_rounded,
        child: _InfoBanner(
          icon: Icons.hourglass_top_rounded,
          text: 'Submitted. Pata Hao will review the authorization and documents.',
        ),
      );
    }

    final ready = _mandateDeclared && _saleDocumentsAdded;

    return _SectionCard(
      title: 'Final check',
      icon: Icons.fact_check_outlined,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            ready
                ? 'Everything required from you is ready.'
                : 'Add all required sale documents before submitting.',
            style: const TextStyle(height: 1.4),
          ),
          const SizedBox(height: 14),
          SizedBox(
            width: double.infinity,
            child: FilledButton.icon(
              onPressed: ready && !_isSubmittingForReview
                  ? _submitForReview
                  : null,
              icon: _isSubmittingForReview
                  ? const SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.send_outlined),
              label: Text(
                _isSubmittingForReview
                    ? 'Submitting...'
                    : 'Send Authorization for Review',
              ),
            ),
          ),
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
    final authorizationLocked =
        _mandateDeclared || _mandateUnderReview || _mandateApproved;

    return Scaffold(
      backgroundColor: const Color(0xFFF6F8F6),
      appBar: AppBar(
        title: Text(_isSaleProperty ? 'Sale setup' : 'Rental setup'),
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
                  const SizedBox(height: 14),
                  _InfoBanner(
                    icon: Icons.shield_outlined,
                    text: _isSaleProperty
                        ? 'Confirm the owner and commission once, add three '
                              'sale documents, then submit for verification.'
                        : 'Confirm the landlord and commission once, then '
                              'submit for verification.',
                  ),
                  if (_errorMessage != null) ...[
                    const SizedBox(height: 14),
                    _ErrorCard(message: _errorMessage!),
                  ],
                  const SizedBox(height: 16),
                  if (!_authorizationComplete)
                    Form(
                      key: _formKey,
                      child: _SectionCard(
                        title: _isSaleProperty
                            ? 'Sale authorization'
                            : 'Rental authorization',
                        icon: Icons.verified_user_outlined,
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            TextFormField(
                              controller: _ownerNameController,
                              enabled: !authorizationLocked,
                              textInputAction: TextInputAction.next,
                              decoration: InputDecoration(
                                labelText: _isSaleProperty
                                    ? 'Owner name'
                                    : 'Landlord name',
                                border: const OutlineInputBorder(),
                              ),
                              validator: (value) => _validateRequiredText(
                                value,
                                _isSaleProperty
                                    ? 'Enter the owner name.'
                                    : 'Enter the landlord name.',
                              ),
                            ),
                            const SizedBox(height: 12),
                            TextFormField(
                              controller: _ownerPhoneController,
                              enabled: !authorizationLocked,
                              keyboardType: TextInputType.phone,
                              textInputAction: TextInputAction.next,
                              decoration: InputDecoration(
                                labelText: _isSaleProperty
                                    ? 'Owner phone'
                                    : 'Landlord phone',
                                border: const OutlineInputBorder(),
                              ),
                              validator: (value) => _validateRequiredText(
                                value,
                                _isSaleProperty
                                    ? 'Enter the owner phone number.'
                                    : 'Enter the landlord phone number.',
                              ),
                            ),
                            const SizedBox(height: 12),
                            DropdownButtonFormField<String>(
                              initialValue: _authorizationMethod,
                              decoration: const InputDecoration(
                                labelText: 'How were you authorized?',
                                border: OutlineInputBorder(),
                              ),
                              items: const [
                                DropdownMenuItem(
                                  value: 'phone',
                                  child: Text('Phone'),
                                ),
                                DropdownMenuItem(
                                  value: 'whatsapp',
                                  child: Text('WhatsApp or message'),
                                ),
                                DropdownMenuItem(
                                  value: 'written',
                                  child: Text('Written authority'),
                                ),
                                DropdownMenuItem(
                                  value: 'verbal',
                                  child: Text('In person or verbal'),
                                ),
                                DropdownMenuItem(
                                  value: 'property_manager',
                                  child: Text('Property manager authority'),
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
                              onChanged: authorizationLocked
                                  ? null
                                  : (value) {
                                      if (value != null) {
                                        setState(() {
                                          _authorizationMethod = value;
                                        });
                                      }
                                    },
                            ),
                            const SizedBox(height: 12),
                            TextFormField(
                              controller: _authorizationNotesController,
                              enabled: !authorizationLocked,
                              maxLines: 2,
                              decoration: const InputDecoration(
                                labelText: 'Authorization note (optional)',
                                border: OutlineInputBorder(),
                              ),
                            ),
                            const SizedBox(height: 20),
                            const Text(
                              'Agreed Pata Hao commission',
                              style: TextStyle(
                                fontSize: 16,
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                            const SizedBox(height: 5),
                            Text(
                              'Based on ${property.formattedPrice}.',
                              style: const TextStyle(color: Colors.black54),
                            ),
                            const SizedBox(height: 12),
                            SegmentedButton<String>(
                              segments: const [
                                ButtonSegment<String>(
                                  value: 'percentage',
                                  label: Text('Percentage'),
                                  icon: Icon(Icons.percent),
                                ),
                                ButtonSegment<String>(
                                  value: 'fixed',
                                  label: Text('Fixed amount'),
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
                            const SizedBox(height: 12),
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
                                validator: (value) => _validatePositiveNumber(
                                  value,
                                  'Enter the agreed commission percentage.',
                                ),
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
                                  labelText: 'Commission amount (KES)',
                                  border: OutlineInputBorder(),
                                ),
                                validator: (value) => _validatePositiveNumber(
                                  value,
                                  'Enter the agreed commission amount.',
                                ),
                              ),
                            const SizedBox(height: 12),
                            _CommissionPreview(
                              propertyValue: _formatKes(_propertyValue()),
                              commissionMethod: _commissionMethod,
                              rate: _commissionRateController.text.trim(),
                              commission: _hasAgreement
                                  ? _serverCommissionLabel()
                                  : _formatKes(_previewCommission()),
                            ),
                            const SizedBox(height: 14),
                            CheckboxListTile(
                              contentPadding: EdgeInsets.zero,
                              controlAffinity: ListTileControlAffinity.leading,
                              value: _authorizationAccepted,
                              onChanged: authorizationLocked
                                  ? null
                                  : (value) {
                                      setState(() {
                                        _authorizationAccepted = value ?? false;
                                      });
                                    },
                              title: const Text(
                                'I confirm I am authorized to market this '
                                'property, will use Pata Hao\'s recorded '
                                'payment process, and will not bypass Pata Hao '
                                'for customers introduced by the platform.',
                                style: TextStyle(height: 1.35),
                              ),
                            ),
                            const SizedBox(height: 10),
                            SizedBox(
                              width: double.infinity,
                              child: FilledButton.icon(
                                onPressed: _isSavingAuthorization
                                    ? null
                                    : _saveAuthorization,
                                icon: _isSavingAuthorization
                                    ? const SizedBox(
                                        width: 18,
                                        height: 18,
                                        child: CircularProgressIndicator(
                                          strokeWidth: 2,
                                        ),
                                      )
                                    : const Icon(Icons.arrow_forward),
                                label: Text(
                                  _isSavingAuthorization
                                      ? 'Saving...'
                                      : 'Save Authorization & Continue',
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                    )
                  else
                    _SectionCard(
                      title: 'Authorization complete',
                      icon: Icons.check_circle_outline,
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const _SuccessBanner(
                            text:
                                'Owner authority and commission terms are securely recorded.',
                          ),
                          const SizedBox(height: 12),
                          Text(
                            'Owner: ${_ownerNameController.text.trim()}',
                          ),
                          const SizedBox(height: 4),
                          Text('Commission: ${_serverCommissionLabel()}'),
                        ],
                      ),
                    ),
                  if (_isSaleProperty && _hasMandate) ...[
                    const SizedBox(height: 16),
                    _buildSalePackCard(),
                  ],
                  if (_mandateDeclared) ...[
                    const SizedBox(height: 16),
                    _buildReviewCard(),
                  ],
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
