import 'package:flutter/material.dart';

import 'package:mobile/models/property.dart';
import 'package:mobile/models/property_type_option.dart';
import 'package:mobile/services/partner_property_service.dart';
import 'package:mobile/services/property_service.dart';
import 'package:mobile/screens/partner_property_workspace_screen.dart';

class PartnerNewPropertyFormScreen extends StatefulWidget {
  const PartnerNewPropertyFormScreen({
    super.key,
    required this.latitude,
    required this.longitude,
  });

  final double latitude;
  final double longitude;

  @override
  State<PartnerNewPropertyFormScreen> createState() {
    return _PartnerNewPropertyFormScreenState();
  }
}

class _PartnerNewPropertyFormScreenState
    extends State<PartnerNewPropertyFormScreen> {
  final _formKey = GlobalKey<FormState>();

  final _titleController = TextEditingController();
  final _priceController = TextEditingController();
  final _countyController = TextEditingController();
  final _townController = TextEditingController();
  final _estateController = TextEditingController();
  final _addressController = TextEditingController();
  final _bedroomsController = TextEditingController();
  final _bathroomsController = TextEditingController();
  final _descriptionController = TextEditingController();

  late Future<List<PropertyTypeOption>> _propertyTypesFuture;

  String? _propertyType;
  String _listingType = 'rent';

  bool _isSubmitting = false;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();

    _propertyTypesFuture =
        PropertyService().fetchPropertyTypes();
  }

  @override
  void dispose() {
    _titleController.dispose();
    _priceController.dispose();
    _countyController.dispose();
    _townController.dispose();
    _estateController.dispose();
    _addressController.dispose();
    _bedroomsController.dispose();
    _bathroomsController.dispose();
    _descriptionController.dispose();

    super.dispose();
  }

  String? _requiredValidator(
    String? value,
    String label,
  ) {
    if (value == null || value.trim().isEmpty) {
      return '$label is required.';
    }

    return null;
  }

  String? _priceValidator(String? value) {
    final requiredError =
        _requiredValidator(value, 'Price');

    if (requiredError != null) {
      return requiredError;
    }

    final amount = double.tryParse(
      value!.replaceAll(',', '').trim(),
    );

    if (amount == null || amount <= 0) {
      return 'Enter a valid price.';
    }

    return null;
  }

  String? _wholeNumberValidator(
    String? value,
    String label,
  ) {
    final requiredError =
        _requiredValidator(value, label);

    if (requiredError != null) {
      return requiredError;
    }

    final number = int.tryParse(value!.trim());

    if (number == null || number < 0) {
      return 'Enter a valid $label.';
    }

    return null;
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

  bool _candidateIsMine(Map<String, dynamic> candidate) {
    final value = candidate['is_mine'];

    if (value == true) {
      return true;
    }

    final text = value?.toString().trim().toLowerCase();
    return text == 'true' || text == '1' || text == 'yes';
  }

  Future<Property?> _recoverRecentDraft() async {
    final expectedTitle = _titleController.text.trim().toLowerCase();

    for (var attempt = 0; attempt < 2; attempt++) {
      if (attempt > 0) {
        await Future<void>.delayed(const Duration(milliseconds: 800));
      }

      try {
        final result =
            await PartnerPropertyService.instance.findNearbyProperties(
          latitude: widget.latitude,
          longitude: widget.longitude,
        );

        final rawCandidates = result['candidates'];

        if (rawCandidates is! List) {
          continue;
        }

        final candidates = rawCandidates
            .whereType<Map>()
            .map((item) => Map<String, dynamic>.from(item))
            .where((candidate) {
              final title =
                  candidate['title']?.toString().trim().toLowerCase() ?? '';

              return _candidateIsMine(candidate) &&
                  candidate['status'] == 'draft' &&
                  title == expectedTitle;
            })
            .toList()
          ..sort((left, right) {
            final leftId = int.tryParse(left['id']?.toString() ?? '') ?? 0;
            final rightId = int.tryParse(right['id']?.toString() ?? '') ?? 0;
            return rightId.compareTo(leftId);
          });

        for (final candidate in candidates) {
          final createdAt = DateTime.tryParse(
            candidate['created_at']?.toString() ?? '',
          );

          if (createdAt == null) {
            continue;
          }

          final age = DateTime.now().toUtc().difference(createdAt.toUtc());

          if (age > const Duration(minutes: 15) ||
              age < const Duration(minutes: -1)) {
            continue;
          }

          final propertyId =
              int.tryParse(candidate['id']?.toString() ?? '');

          if (propertyId == null || propertyId <= 0) {
            continue;
          }

          return PartnerPropertyService.instance.fetchMyProperty(propertyId);
        }
      } catch (_) {
        // Recovery is best-effort; the original create error is shown below.
      }
    }

    return null;
  }
  Future<void> _submit() async {
    if (_isSubmitting) {
      return;
    }

    final form = _formKey.currentState;

    if (form == null || !form.validate()) {
      return;
    }

    final propertyType = _propertyType;

    if (propertyType == null || propertyType.trim().isEmpty) {
      setState(() {
        _errorMessage = 'Please choose a property type.';
      });
      return;
    }

    final price = double.tryParse(
      _priceController.text.replaceAll(',', '').trim(),
    );
    final bedrooms = int.tryParse(_bedroomsController.text.trim());
    final bathrooms = int.tryParse(_bathroomsController.text.trim());

    if (price == null || bedrooms == null || bathrooms == null) {
      return;
    }

    setState(() {
      _isSubmitting = true;
      _errorMessage = null;
    });

    Property? property;
    var workspaceFinished = false;

    try {
      var recovered = false;

      try {
        property = await PartnerPropertyService.instance.createProperty(
          title: _titleController.text,
          propertyType: propertyType,
          listingType: _listingType,
          price: price,
          county: _countyController.text,
          town: _townController.text,
          estate: _estateController.text,
          address: _addressController.text,
          latitude: widget.latitude,
          longitude: widget.longitude,
          bedrooms: bedrooms,
          bathrooms: bathrooms,
          description: _descriptionController.text,
        );
      } catch (createError) {
        property = await _recoverRecentDraft();

        if (property == null) {
          throw createError;
        }

        recovered = true;
      }

      if (!mounted) {
        return;
      }

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            recovered
                ? 'Your saved draft was recovered. Continue below.'
                : 'Property "${property.title}" created. '
                    'Continue setting it up below.',
          ),
        ),
      );

      await Navigator.of(context).push<bool>(
        MaterialPageRoute<bool>(
          builder: (_) => PartnerPropertyWorkspaceScreen(
            property: property!,
          ),
        ),
      );

      workspaceFinished = true;
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

    if (workspaceFinished && mounted && property != null) {
      Navigator.of(context).pop<Property>(property);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text(
          'Property Details',
        ),
      ),
      body: Form(
        key: _formKey,
        child: ListView(
          padding: const EdgeInsets.fromLTRB(
            16,
            16,
            16,
            32,
          ),
          children: [
            const Text(
              'Tell us about the property',
              style: TextStyle(
                fontSize: 22,
                fontWeight: FontWeight.bold,
              ),
            ),

            const SizedBox(height: 6),

            const Text(
              'The property location has already been '
              'captured from your device.',
            ),

            const SizedBox(height: 16),

            Card(
              child: Padding(
                padding: const EdgeInsets.all(14),
                child: Row(
                  children: [
                    const Icon(
                      Icons.location_on_outlined,
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Text(
                        '${widget.latitude.toStringAsFixed(7)}, '
                        '${widget.longitude.toStringAsFixed(7)}',
                      ),
                    ),
                  ],
                ),
              ),
            ),

            const SizedBox(height: 20),

            TextFormField(
              controller: _titleController,
              textInputAction:
                  TextInputAction.next,
              decoration: const InputDecoration(
                labelText: 'Property title',
                hintText: 'Example: Greenview Apartments',
                border: OutlineInputBorder(),
              ),
              validator: (value) =>
                  _requiredValidator(
                value,
                'Property title',
              ),
            ),

            const SizedBox(height: 16),

            FutureBuilder<List<PropertyTypeOption>>(
              future: _propertyTypesFuture,
              builder: (context, snapshot) {
                if (snapshot.connectionState ==
                    ConnectionState.waiting) {
                  return const LinearProgressIndicator();
                }

                if (snapshot.hasError) {
                  return Column(
                    crossAxisAlignment:
                        CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Property types could not be loaded.',
                      ),
                      const SizedBox(height: 8),
                      OutlinedButton.icon(
                        onPressed: () {
                          setState(() {
                            _propertyTypesFuture =
                                PropertyService()
                                    .fetchPropertyTypes();
                          });
                        },
                        icon: const Icon(
                          Icons.refresh,
                        ),
                        label: const Text(
                          'Try Again',
                        ),
                      ),
                    ],
                  );
                }

                final types =
                    snapshot.data ??
                        <PropertyTypeOption>[];

                return DropdownButtonFormField<String>(
                  initialValue: _propertyType,
                  decoration: const InputDecoration(
                    labelText: 'Property type',
                    border: OutlineInputBorder(),
                  ),
                  items: types
                      .map(
                        (type) =>
                            DropdownMenuItem<String>(
                          value: type.value,
                          child: Text(type.label),
                        ),
                      )
                      .toList(),
                  onChanged: (value) {
                    setState(() {
                      _propertyType = value;
                    });
                  },
                  validator: (value) {
                    if (value == null ||
                        value.trim().isEmpty) {
                      return 'Choose a property type.';
                    }

                    return null;
                  },
                );
              },
            ),

            const SizedBox(height: 20),

            const Text(
              'Listing type',
              style: TextStyle(
                fontWeight: FontWeight.bold,
              ),
            ),

            const SizedBox(height: 8),

            SegmentedButton<String>(
              segments: const [
                ButtonSegment<String>(
                  value: 'rent',
                  icon: Icon(
                    Icons.key_outlined,
                  ),
                  label: Text('Rent'),
                ),
                ButtonSegment<String>(
                  value: 'sale',
                  icon: Icon(
                    Icons.sell_outlined,
                  ),
                  label: Text('Sale'),
                ),
              ],
              selected: {
                _listingType,
              },
              onSelectionChanged: (selection) {
                setState(() {
                  _listingType = selection.first;
                });
              },
            ),

            const SizedBox(height: 20),

            TextFormField(
              controller: _priceController,
              keyboardType:
                  const TextInputType.numberWithOptions(
                decimal: true,
              ),
              textInputAction:
                  TextInputAction.next,
              decoration: InputDecoration(
                labelText: _listingType == 'rent'
                    ? 'Monthly rent (KES)'
                    : 'Sale price (KES)',
                border:
                    const OutlineInputBorder(),
              ),
              validator: _priceValidator,
            ),

            const SizedBox(height: 20),

            const Text(
              'Location',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
              ),
            ),

            const SizedBox(height: 12),

            TextFormField(
              controller: _countyController,
              textInputAction:
                  TextInputAction.next,
              decoration: const InputDecoration(
                labelText: 'County',
                border: OutlineInputBorder(),
              ),
              validator: (value) =>
                  _requiredValidator(
                value,
                'County',
              ),
            ),

            const SizedBox(height: 12),

            TextFormField(
              controller: _townController,
              textInputAction:
                  TextInputAction.next,
              decoration: const InputDecoration(
                labelText: 'Town',
                border: OutlineInputBorder(),
              ),
              validator: (value) =>
                  _requiredValidator(
                value,
                'Town',
              ),
            ),

            const SizedBox(height: 12),

            TextFormField(
              controller: _estateController,
              textInputAction:
                  TextInputAction.next,
              decoration: const InputDecoration(
                labelText: 'Estate / neighborhood',
                border: OutlineInputBorder(),
              ),
            ),

            const SizedBox(height: 12),

            TextFormField(
              controller: _addressController,
              textInputAction:
                  TextInputAction.next,
              decoration: const InputDecoration(
                labelText:
                    'Building / road / address',
                hintText:
                    'Example: Mirembe Court, Thika Road',
                border: OutlineInputBorder(),
              ),
            ),

            const SizedBox(height: 20),

            Row(
              children: [
                Expanded(
                  child: TextFormField(
                    controller:
                        _bedroomsController,
                    keyboardType:
                        TextInputType.number,
                    textInputAction:
                        TextInputAction.next,
                    decoration:
                        const InputDecoration(
                      labelText: 'Bedrooms',
                      border:
                          OutlineInputBorder(),
                    ),
                    validator: (value) =>
                        _wholeNumberValidator(
                      value,
                      'bedrooms',
                    ),
                  ),
                ),

                const SizedBox(width: 12),

                Expanded(
                  child: TextFormField(
                    controller:
                        _bathroomsController,
                    keyboardType:
                        TextInputType.number,
                    textInputAction:
                        TextInputAction.next,
                    decoration:
                        const InputDecoration(
                      labelText: 'Bathrooms',
                      border:
                          OutlineInputBorder(),
                    ),
                    validator: (value) =>
                        _wholeNumberValidator(
                      value,
                      'bathrooms',
                    ),
                  ),
                ),
              ],
            ),

            const SizedBox(height: 20),

            TextFormField(
              controller: _descriptionController,
              minLines: 4,
              maxLines: 8,
              decoration: const InputDecoration(
                labelText: 'Description',
                hintText:
                    'Describe the property, condition, '
                    'features, and anything a customer '
                    'should know.',
                alignLabelWithHint: true,
                border: OutlineInputBorder(),
              ),
              validator: (value) =>
                  _requiredValidator(
                value,
                'Description',
              ),
            ),

            if (_errorMessage != null) ...[
              const SizedBox(height: 16),
              Card(
                color: Colors.red.shade50,
                child: Padding(
                  padding:
                      const EdgeInsets.all(14),
                  child: Text(
                    _errorMessage!,
                    style: TextStyle(
                      color: Colors.red.shade800,
                    ),
                  ),
                ),
              ),
            ],

            const SizedBox(height: 24),

            FilledButton.icon(
              onPressed:
                  _isSubmitting ? null : _submit,
              icon: _isSubmitting
                  ? const SizedBox(
                      height: 18,
                      width: 18,
                      child:
                          CircularProgressIndicator(
                        strokeWidth: 2,
                      ),
                    )
                  : const Icon(
                      Icons.save_outlined,
                    ),
              label: Text(
                _isSubmitting
                    ? 'Creating property...'
                    : 'Create Property',
              ),
            ),
          ],
        ),
      ),
    );
  }
}