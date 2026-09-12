import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../services/auth_service.dart';

class ForgotPasswordScreen extends StatefulWidget {
  const ForgotPasswordScreen({super.key});

  @override
  State<ForgotPasswordScreen> createState() => _ForgotPasswordScreenState();
}

class _ForgotPasswordScreenState extends State<ForgotPasswordScreen> {
  final GlobalKey<FormState> _requestFormKey = GlobalKey<FormState>();
  final GlobalKey<FormState> _confirmFormKey = GlobalKey<FormState>();
  final TextEditingController _identifierController = TextEditingController();
  final TextEditingController _codeController = TextEditingController();
  final TextEditingController _passwordController = TextEditingController();
  final TextEditingController _passwordConfirmController =
      TextEditingController();

  bool _codeRequested = false;
  bool _isLoading = false;
  bool _obscurePassword = true;
  bool _obscurePasswordConfirm = true;

  @override
  void dispose() {
    _identifierController.dispose();
    _codeController.dispose();
    _passwordController.dispose();
    _passwordConfirmController.dispose();
    super.dispose();
  }

  Future<void> _requestCode() async {
    FocusScope.of(context).unfocus();
    final requestForm = _requestFormKey.currentState;
    if (!_codeRequested && (requestForm == null || !requestForm.validate())) {
      return;
    }

    setState(() {
      _isLoading = true;
    });

    try {
      await AuthService.instance.requestPasswordReset(
        identifier: _identifierController.text,
      );

      if (!mounted) {
        return;
      }

      setState(() {
        _codeRequested = true;
        _codeController.clear();
      });
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text(
            'If the account exists, a reset code was sent to its email.',
          ),
        ),
      );
    } catch (error) {
      _showError(error);
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  Future<void> _resetPassword() async {
    FocusScope.of(context).unfocus();
    if (!_confirmFormKey.currentState!.validate()) {
      return;
    }

    setState(() {
      _isLoading = true;
    });

    try {
      await AuthService.instance.confirmPasswordReset(
        identifier: _identifierController.text,
        code: _codeController.text,
        newPassword: _passwordController.text,
        newPasswordConfirm: _passwordConfirmController.text,
      );

      if (!mounted) {
        return;
      }

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Password changed. You can now sign in.'),
        ),
      );
      Navigator.of(context).pop();
    } catch (error) {
      _showError(error);
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  void _showError(Object error) {
    if (!mounted) {
      return;
    }

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(error.toString().replaceFirst('Exception: ', '')),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF6F8F6),
      appBar: AppBar(
        title: const Text('Reset Password'),
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
                  child: _codeRequested
                      ? _buildConfirmationForm()
                      : _buildRequestForm(),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildRequestForm() {
    return Form(
      key: _requestFormKey,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const Icon(
            Icons.lock_reset_outlined,
            size: 64,
            color: Color(0xFF14532D),
          ),
          const SizedBox(height: 18),
          const Text(
            'Forgot your password?',
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 10),
          const Text(
            'Enter your email or username. We will email a secure reset '
            'code to the address saved on your Pata HAO account.',
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 15, color: Colors.black54, height: 1.4),
          ),
          const SizedBox(height: 26),
          TextFormField(
            controller: _identifierController,
            enabled: !_isLoading,
            textInputAction: TextInputAction.done,
            keyboardType: TextInputType.emailAddress,
            autofillHints: const [AutofillHints.username, AutofillHints.email],
            onFieldSubmitted: (_) {
              if (!_isLoading) {
                _requestCode();
              }
            },
            decoration: const InputDecoration(
              labelText: 'Email or username',
              prefixIcon: Icon(Icons.alternate_email),
              border: OutlineInputBorder(),
            ),
            validator: (value) {
              if (value == null || value.trim().isEmpty) {
                return 'Enter your email or username.';
              }
              return null;
            },
          ),
          const SizedBox(height: 22),
          SizedBox(
            height: 54,
            child: ElevatedButton(
              onPressed: _isLoading ? null : _requestCode,
              child: _isLoading
                  ? const SizedBox(
                      width: 24,
                      height: 24,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Text(
                      'Send Reset Code',
                      style: TextStyle(fontSize: 17),
                    ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildConfirmationForm() {
    return Form(
      key: _confirmFormKey,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const Icon(
            Icons.mark_email_read_outlined,
            size: 64,
            color: Color(0xFF14532D),
          ),
          const SizedBox(height: 18),
          const Text(
            'Check your email',
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 10),
          const Text(
            'Enter the 8-digit code and choose a new password. The code '
            'expires after 15 minutes.',
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 15, color: Colors.black54, height: 1.4),
          ),
          const SizedBox(height: 24),
          TextFormField(
            controller: _codeController,
            enabled: !_isLoading,
            keyboardType: TextInputType.number,
            textInputAction: TextInputAction.next,
            inputFormatters: [
              FilteringTextInputFormatter.digitsOnly,
              LengthLimitingTextInputFormatter(8),
            ],
            decoration: const InputDecoration(
              labelText: '8-digit reset code',
              prefixIcon: Icon(Icons.pin_outlined),
              border: OutlineInputBorder(),
            ),
            validator: (value) {
              if ((value ?? '').trim().length != 8) {
                return 'Enter the 8-digit reset code.';
              }
              return null;
            },
          ),
          const SizedBox(height: 16),
          _buildPasswordField(
            controller: _passwordController,
            label: 'New Password',
            obscure: _obscurePassword,
            onToggle: () {
              setState(() {
                _obscurePassword = !_obscurePassword;
              });
            },
          ),
          const SizedBox(height: 16),
          _buildPasswordField(
            controller: _passwordConfirmController,
            label: 'Confirm New Password',
            obscure: _obscurePasswordConfirm,
            onToggle: () {
              setState(() {
                _obscurePasswordConfirm = !_obscurePasswordConfirm;
              });
            },
            confirm: true,
          ),
          const SizedBox(height: 22),
          SizedBox(
            height: 54,
            child: ElevatedButton(
              onPressed: _isLoading ? null : _resetPassword,
              child: _isLoading
                  ? const SizedBox(
                      width: 24,
                      height: 24,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Text(
                      'Change Password',
                      style: TextStyle(fontSize: 17),
                    ),
            ),
          ),
          TextButton(
            onPressed: _isLoading ? null : _requestCode,
            child: const Text('Send a new code'),
          ),
          TextButton(
            onPressed: _isLoading
                ? null
                : () {
                    setState(() {
                      _codeRequested = false;
                      _codeController.clear();
                      _passwordController.clear();
                      _passwordConfirmController.clear();
                    });
                  },
            child: const Text('Use a different email or username'),
          ),
        ],
      ),
    );
  }

  Widget _buildPasswordField({
    required TextEditingController controller,
    required String label,
    required bool obscure,
    required VoidCallback onToggle,
    bool confirm = false,
  }) {
    return TextFormField(
      controller: controller,
      enabled: !_isLoading,
      obscureText: obscure,
      textInputAction: confirm ? TextInputAction.done : TextInputAction.next,
      onFieldSubmitted: confirm
          ? (_) {
              if (!_isLoading) {
                _resetPassword();
              }
            }
          : null,
      decoration: InputDecoration(
        labelText: label,
        prefixIcon: const Icon(Icons.lock_outline),
        border: const OutlineInputBorder(),
        suffixIcon: IconButton(
          onPressed: _isLoading ? null : onToggle,
          icon: Icon(
            obscure ? Icons.visibility_outlined : Icons.visibility_off_outlined,
          ),
        ),
      ),
      validator: (value) {
        if (value == null || value.isEmpty) {
          return confirm ? 'Confirm your new password.' : 'Enter a password.';
        }
        if (value.length < 8) {
          return 'Password must be at least 8 characters.';
        }
        if (confirm && value != _passwordController.text) {
          return 'The passwords do not match.';
        }
        return null;
      },
    );
  }
}
