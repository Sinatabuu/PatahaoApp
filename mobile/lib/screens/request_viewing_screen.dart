import 'package:flutter/material.dart';

import '../models/property.dart';
import '../models/viewing.dart';
import '../services/viewing_service.dart';
import 'payment_screen.dart';

class RequestViewingScreen extends StatefulWidget {
  final Property property;

  const RequestViewingScreen({super.key, required this.property});

  @override
  State<RequestViewingScreen> createState() => _RequestViewingScreenState();
}

class _RequestViewingScreenState extends State<RequestViewingScreen> {
  DateTime? _selectedDate;
  String? _selectedTime;

  final TextEditingController _messageController = TextEditingController();

  final List<String> _timeOptions = ['Morning', 'Afternoon', 'Evening'];

  final ViewingService _viewingService = ViewingService();

  bool _isSubmitting = false;

  int get viewingFee {
    return widget.property.listingType.trim().toLowerCase() == 'sale'
        ? 2000
        : 400;
  }

  String get formattedViewingFee {
    return viewingFee.toString().replaceAllMapped(
      RegExp(r'\B(?=(\d{3})+(?!\d))'),
      (match) => ',',
    );
  }

  @override
  void dispose() {
    _messageController.dispose();
    super.dispose();
  }

  Future<void> _chooseDate() async {
    final now = DateTime.now();

    final selectedDate = await showDatePicker(
      context: context,
      initialDate: now.add(const Duration(days: 1)),
      firstDate: now,
      lastDate: now.add(const Duration(days: 90)),
    );

    if (selectedDate != null) {
      setState(() {
        _selectedDate = selectedDate;
      });
    }
  }

  String get _formattedDate {
    if (_selectedDate == null) {
      return 'Choose a preferred date';
    }

    final day = _selectedDate!.day.toString().padLeft(2, '0');
    final month = _selectedDate!.month.toString().padLeft(2, '0');
    final year = _selectedDate!.year;

    return '$day/$month/$year';
  }

  Future<void> _submitRequest() async {
    if (_selectedDate == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please choose a viewing date.')),
      );
      return;
    }

    if (_selectedTime == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please choose a preferred time.')),
      );
      return;
    }

    final requestedTime = switch (_selectedTime) {
      'Morning' => '10:00:00',
      'Afternoon' => '14:00:00',
      'Evening' => '17:00:00',
      _ => '10:00:00',
    };

    setState(() {
      _isSubmitting = true;
    });

    try {
      final Viewing viewing = await _viewingService.createViewing(
        propertyId: widget.property.id,
        requestedDate: _selectedDate!,
        requestedTime: requestedTime,
        customerMessage: _messageController.text,
      );

      if (!mounted) {
        return;
      }

      await Navigator.pushReplacement(
        context,
        MaterialPageRoute<void>(
          builder: (_) => PaymentScreen(viewing: viewing),
        ),
      );
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
          _isSubmitting = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Request Viewing')),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Card(
                child: ListTile(
                  leading: const CircleAvatar(
                    backgroundColor: Color(0xFFE8F5E9),
                    child: Icon(Icons.home_outlined, color: Color(0xFF34AD2C)),
                  ),
                  title: Text(
                    widget.property.title,
                    style: const TextStyle(fontWeight: FontWeight.bold),
                  ),
                  subtitle: Text(
                    [
                      widget.property.estate,
                      widget.property.town,
                    ].where((value) => value.trim().isNotEmpty).join(', '),
                  ),
                ),
              ),
              const SizedBox(height: 28),
              const Text(
                'Preferred date',
                style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 12),
              InkWell(
                onTap: _chooseDate,
                borderRadius: BorderRadius.circular(14),
                child: Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(18),
                  decoration: BoxDecoration(
                    border: Border.all(color: Colors.black26),
                    borderRadius: BorderRadius.circular(14),
                  ),
                  child: Row(
                    children: [
                      const Icon(
                        Icons.calendar_month_outlined,
                        color: Color(0xFF34AD2C),
                      ),
                      const SizedBox(width: 12),
                      Text(
                        _formattedDate,
                        style: const TextStyle(fontSize: 16),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 28),
              const Text(
                'Preferred time',
                style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 12),
              Wrap(
                spacing: 10,
                runSpacing: 10,
                children: _timeOptions.map((time) {
                  return ChoiceChip(
                    label: Text(time),
                    selected: _selectedTime == time,
                    onSelected: (selected) {
                      setState(() {
                        _selectedTime = selected ? time : null;
                      });
                    },
                  );
                }).toList(),
              ),
              const SizedBox(height: 28),
              const Text(
                'Message to partner',
                style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _messageController,
                minLines: 4,
                maxLines: 6,
                decoration: InputDecoration(
                  hintText:
                      'Example: I would like to view the property after work.',
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(14),
                  ),
                ),
              ),
              const SizedBox(
                height: 24,
              ), // Added separation space before button
              SizedBox(
                width: double.infinity,
                height: 56,
                child: ElevatedButton.icon(
                  onPressed: _isSubmitting ? null : _submitRequest,
                  icon: const Icon(Icons.calendar_month_outlined),

                  label: _isSubmitting
                      ? const SizedBox(
                          width: 22,
                          height: 22,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : Text(
                          'Continue to payment — KES $formattedViewingFee',
                          style: const TextStyle(fontSize: 18),
                        ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
