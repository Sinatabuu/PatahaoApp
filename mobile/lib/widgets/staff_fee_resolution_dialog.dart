import 'package:flutter/material.dart';

class StaffFeeResolutionDecision {
  const StaffFeeResolutionDecision({
    required this.providerReference,
    required this.notes,
  });

  final String providerReference;
  final String notes;
}

Future<StaffFeeResolutionDecision?> showStaffFeeResolutionDialog(
  BuildContext context, {
  required bool isRefund,
}) {
  final formKey = GlobalKey<FormState>();
  var providerReference = '';
  var notes = '';

  return showDialog<StaffFeeResolutionDecision>(
    context: context,
    builder: (dialogContext) {
      return AlertDialog(
        title: Text(isRefund ? 'Confirm full refund' : 'Issue viewing credit'),
        content: Form(
          key: formKey,
          child: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  isRefund
                      ? 'First complete the refund with the payment provider. '
                            'Then enter its refund reference so Pata HAO records '
                            'evidence of the returned money.'
                      : 'This will create transferable viewing credit for the '
                            'customer using the paid fee.',
                ),
                if (isRefund) ...[
                  const SizedBox(height: 16),
                  TextFormField(
                    onChanged: (value) => providerReference = value,
                    decoration: const InputDecoration(
                      labelText: 'Provider refund reference',
                      border: OutlineInputBorder(),
                    ),
                    validator: (value) {
                      if ((value ?? '').trim().isEmpty) {
                        return 'Enter the completed refund reference.';
                      }
                      return null;
                    },
                  ),
                ],
                const SizedBox(height: 16),
                TextFormField(
                  onChanged: (value) => notes = value,
                  maxLines: 3,
                  decoration: const InputDecoration(
                    labelText: 'Internal notes (optional)',
                    border: OutlineInputBorder(),
                  ),
                ),
              ],
            ),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () {
              if (formKey.currentState?.validate() != true) {
                return;
              }

              Navigator.pop(
                dialogContext,
                StaffFeeResolutionDecision(
                  providerReference: providerReference.trim(),
                  notes: notes.trim(),
                ),
              );
            },
            child: Text(isRefund ? 'Record Refund' : 'Issue Credit'),
          ),
        ],
      );
    },
  );
}
