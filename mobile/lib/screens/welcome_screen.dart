import 'package:flutter/material.dart';

import 'package:mobile/screens/login_screen.dart';
import 'package:mobile/screens/property_list_screen.dart';

class WelcomeScreen extends StatelessWidget {
  const WelcomeScreen({super.key, required this.onLoginSuccess});

  final VoidCallback onLoginSuccess;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF6F8F6),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Spacer(),

              Center(
                child: Image.asset(
                  'assets/images/pata_hao_logo.jpg',
                  width: 240,
                  fit: BoxFit.contain,
                ),
              ),

              const Center(
                child: Text(
                  'Find your next home',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    fontSize: 20,
                    fontWeight: FontWeight.w600,
                    color: Color(0xFF34AD2C),
                  ),
                ),
              ),

              const SizedBox(height: 40),

              // Sign in
              SizedBox(
                width: double.infinity,
                height: 54,
                child: ElevatedButton(
                  onPressed: () {
                    Navigator.push(
                      context,
                      MaterialPageRoute<void>(
                        builder: (_) => LoginScreen(
                          onLoginSuccess: () {
                            Navigator.pop(context);
                            onLoginSuccess();
                          },
                        ),
                      ),
                    );
                  },
                  child: const Text(
                    'Sign In',
                    style: TextStyle(fontSize: 18),
                  ),
                ),
              ),

              const SizedBox(height: 16),

              // Create account
              SizedBox(
                width: double.infinity,
                height: 54,
                child: OutlinedButton(
                  onPressed: () {
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(
                        content: Text(
                          'Account registration is coming next.',
                        ),
                      ),
                    );
                  },
                  child: const Text(
                    'Create Account',
                    style: TextStyle(fontSize: 18),
                  ),
                ),
              ),

              const SizedBox(height: 16),

              // Browse without signing in
              SizedBox(
                width: double.infinity,
                height: 54,
                child: TextButton(
                  onPressed: () {
                    Navigator.push(
                      context,
                      MaterialPageRoute<void>(
                        builder: (_) => const PropertyListScreen(),
                      ),
                    );
                  },
                  child: const Text(
                    'Browse Properties',
                    style: TextStyle(fontSize: 18),
                  ),
                ),
              ),

              const Spacer(),

              const Center(
                child: Text(
                  'Built for trust. Built for Kenya.',
                  style: TextStyle(color: Colors.black54),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}