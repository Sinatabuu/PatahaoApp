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

  Future<void> _submit() async {
    if (_isSubmitting) {
      return;
    }

    final form = _formKey.currentState;

    if (form == null || !form.validate()) {
      return;
    }

    final propertyType = _propertyType;

    if (propertyType == null ||
        propertyType.trim().isEmpty) {
      setState(() {
        _errorMessage =
            'Please choose a property type.';
      });
      return;
    }

    final price = double.tryParse(
      _priceController.text
          .replaceAll(',', '')
          .trim(),
    );

    final bedrooms = int.tryParse(
      _bedroomsController.text.trim(),
    );

    final bathrooms = int.tryParse(
      _bathroomsController.text.trim(),
    );

    if (price == null ||
        bedrooms == null ||
        bathrooms == null) {
      return;
    }

    setState(() {
      _isSubmitting = true;
      _errorMessage = null;
    });

    try {
      final Property property =
          await PartnerPropertyService.instance
              .createProperty(
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

      if (!mounted) {
        return;
        }

        ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
            content: Text(
            'Property "${property.title}" created. '
            'Now add property photos.',
            ),
        ),
        );

        await Navigator.of(context).push(
        MaterialPageRoute(
            builder: (_) => PartnerPropertyWorkspaceScreen(
            property: property,
            ),
        ),
        );

        if (!mounted) {
        return;
        }

        Navigator.of(context).pop<Property>(
        property,
        );

      Navigator.of(context).pop<Property>(
        property,
      );
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