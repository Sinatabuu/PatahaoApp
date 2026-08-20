import 'package:flutter/material.dart';

import 'screens/app_entry_screen.dart';

void main() {
  runApp(const PataHaoApp());
}

class PataHaoApp extends StatelessWidget {
  const PataHaoApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Pata Hao',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF34AD2C)),
        useMaterial3: true,
      ),
      home: const AppEntryScreen(),
    );
  }
}
