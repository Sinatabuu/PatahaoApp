import 'package:flutter/material.dart';

import '../services/auth_service.dart';

class AddPhoneNumberScreen extends StatefulWidget {
  const AddPhoneNumberScreen({super.key});

  @override
  State<AddPhoneNumberScreen> createState() => _AddPhoneNumberScreenState();
}

class _AddPhoneNumberScreenState extends State<AddPhoneNumberScreen> {
  final GlobalKey<FormState> _formKey = GlobalKey<FormState>();

  final TextEditingController _phoneController = TextEditingController();

  bool _isSaving = false;

  @override
  void dispose() {
    _phoneController.dispose();
    super.dispose();
  }

  Future<void> _savePhoneNumber() async {
    FocusScope.of(context).unfocus();

    if (!_formKey.currentState!.validate()) {
      return;
    }

    setState(() {
      _isSaving = true;
    });

    try {
      final user = await AuthService.instance.updatePhoneNumber(
        phoneNumber: _phoneController.text,
      );

      if (!mounted) {
        return;
      }

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Phone number saved successfully.')),
      );

      Navigator.of(context).pop(user);
    } catch (error) {
      if (!mounted) {
        return;
      }

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(error.toString().replaceFirst('Exception: ', '')),
        ),
      );
    } finally {
      if (mounted) {
        setState(() {
          _isSaving = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF6F8F6),
      appBar: AppBar(
        title: const Text('Add Phone Number'),
        backgroundColor: const Color(0xFFF6F8F6),
      ),
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 460),
              child: Card(
                elevation: 2,
                child: Padding(
                  padding: const EdgeInsets.all(24),
                  child: Form(
                    key: _formKey,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        const CircleAvatar(
                          radius: 38,
                          backgroundColor: Color(0xFFE8F5E9),
                          child: Icon(
                            Icons.phone_android_outlined,
                            size: 42,
                            color: Color(0xFF14532D),
                          ),
                        ),
                        const SizedBox(height: 18),
                        const Text(
                          'Add your phone number',
                          textAlign: TextAlign.center,
                          style: TextStyle(
                            fontSize: 24,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        const SizedBox(height: 10),
                        const Text(
                          'A phone number is required before '
                          'you can request a property viewing. '
                          'It will be used for viewing '
                          'coordination and payment.',
                          textAlign: TextAlign.center,
                          style: TextStyle(
                            fontSize: 15,
                            height: 1.4,
                            color: Colors.black54,
                          ),
                        ),
                        const SizedBox(height: 28),
                        TextFormField(
                          controller: _phoneController,
                          enabled: !_isSaving,
                          keyboardType: TextInputType.phone,
                          textInputAction: TextInputAction.done,
                          onFieldSubmitted: (_) {
                            if (!_isSaving) {
                              _savePhoneNumber();
                            }
                          },
                          decoration: const InputDecoration(
                            labelText: 'Phone Number',
                            hintText: '0712345678',
                            prefixIcon: Icon(Icons.phone_outlined),
                            border: OutlineInputBorder(),
                          ),
                          validator: (value) {
                            final phone = value?.trim() ?? '';

                            if (phone.isEmpty) {
                              return 'Enter your phone number.';
                            }

                            if (phone.length < 9) {
                              return 'Enter a valid phone number.';
                            }

                            return null;
                          },
                        ),
                        const SizedBox(height: 22),
                        SizedBox(
                          height: 54,
                          child: ElevatedButton(
                            onPressed: _isSaving ? null : _savePhoneNumber,
                            child: _isSaving
                                ? const SizedBox(
                                    width: 24,
                                    height: 24,
                                    child: CircularProgressIndicator(
                                      strokeWidth: 2,
                                    ),
                                  )
                                : const Text(
                                    'Save and Continue',
                                    style: TextStyle(fontSize: 17),
                                  ),
                          ),
                        ),
                        const SizedBox(height: 14),
                        const Text(
                          'Phone verification by OTP will be '
                          'added later. For now, Pata Hao stores '
                          'the number on your customer account.',
                          textAlign: TextAlign.center,
                          style: TextStyle(fontSize: 13, color: Colors.black54),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
