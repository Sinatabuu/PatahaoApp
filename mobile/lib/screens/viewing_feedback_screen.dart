import 'package:flutter/material.dart';

import '../models/viewing.dart';
import '../models/viewing_feedback.dart';
import '../services/viewing_service.dart';

class ViewingFeedbackScreen extends StatefulWidget {
  const ViewingFeedbackScreen({super.key, required this.viewing});

  final Viewing viewing;

  @override
  State<ViewingFeedbackScreen> createState() => _ViewingFeedbackScreenState();
}

class _ViewingFeedbackScreenState extends State<ViewingFeedbackScreen> {
  final TextEditingController _commentsController = TextEditingController();

  bool _attended = true;
  String? _propertyAccuracy;

  int _partnerRating = 0;
  int _propertyRating = 0;

  bool _isSubmitting = false;
  String? _errorMessage;

  @override
  void dispose() {
    _commentsController.dispose();
    super.dispose();
  }

  Future<void> _submitFeedback() async {
    if (_propertyAccuracy == null) {
      setState(() {
        _errorMessage = 'Select whether the property matched the listing.';
      });
      return;
    }

    if (_partnerRating == 0) {
      setState(() {
        _errorMessage = 'Please rate the partner.';
      });
      return;
    }

    if (_propertyRating == 0) {
      setState(() {
        _errorMessage = 'Please rate the property.';
      });
      return;
    }

    setState(() {
      _isSubmitting = true;
      _errorMessage = null;
    });

    try {
      final ViewingFeedback feedback = await ViewingService()
          .submitViewingFeedback(
            viewingId: widget.viewing.id,
            attended: _attended,
            propertyAccuracy: _propertyAccuracy!,
            partnerRating: _partnerRating,
            propertyRating: _propertyRating,
            comments: _commentsController.text,
          );

      if (!mounted) {
        return;
      }

      await showDialog<void>(
        context: context,
        barrierDismissible: false,
        builder: (dialogContext) {
          return AlertDialog(
            icon: const Icon(
              Icons.check_circle_rounded,
              size: 54,
              color: Color(0xFF15803D),
            ),
            title: const Text('Thank you', textAlign: TextAlign.center),
            content: Text(
              'Your feedback for '
              '${widget.viewing.propertyTitle} '
              'has been submitted successfully.',
              textAlign: TextAlign.center,
            ),
            actions: [
              SizedBox(
                width: double.infinity,
                child: ElevatedButton(
                  onPressed: () {
                    Navigator.of(dialogContext).pop();
                  },
                  child: const Text('Done'),
                ),
              ),
            ],
          );
        },
      );

      if (!mounted) {
        return;
      }

      Navigator.of(context).pop<ViewingFeedback>(feedback);
    } catch (error) {
      if (!mounted) {
        return;
      }

      setState(() {
        _errorMessage = error.toString().replaceFirst('Exception: ', '');
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
      backgroundColor: const Color(0xFFF6F8F6),
      appBar: AppBar(
        title: const Text('Viewing Feedback'),
        backgroundColor: const Color(0xFF14532D),
        foregroundColor: Colors.white,
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(16, 18, 16, 32),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _HeaderCard(viewing: widget.viewing),
              const SizedBox(height: 18),
              _SectionCard(
                title: 'Did you attend?',
                child: SegmentedButton<bool>(
                  segments: const [
                    ButtonSegment<bool>(
                      value: true,
                      icon: Icon(Icons.check_circle_outline),
                      label: Text('Yes'),
                    ),
                    ButtonSegment<bool>(
                      value: false,
                      icon: Icon(Icons.cancel_outlined),
                      label: Text('No'),
                    ),
                  ],
                  selected: <bool>{_attended},
                  onSelectionChanged: _isSubmitting
                      ? null
                      : (selection) {
                          setState(() {
                            _attended = selection.first;
                          });
                        },
                ),
              ),
              const SizedBox(height: 16),
              _SectionCard(
                title: 'Did the property match the listing?',
                child: RadioGroup<String>(
                  groupValue: _propertyAccuracy,
                  onChanged: (value) {
                    if (_isSubmitting) {
                      return;
                    }

                    setState(() {
                      _propertyAccuracy = value;
                    });
                  },
                  child: const Column(
                    children: [
                      _AccuracyOption(
                        value: 'yes',
                        title: 'Yes',
                        subtitle:
                            'The property matched the photos and description.',
                      ),
                      _AccuracyOption(
                        value: 'partially',
                        title: 'Partially',
                        subtitle:
                            'Some details were accurate, but others differed.',
                      ),
                      _AccuracyOption(
                        value: 'no',
                        title: 'No',
                        subtitle: 'The property was significantly different.',
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 16),
              _SectionCard(
                title: 'Rate the partner',
                child: _StarRating(
                  value: _partnerRating,
                  onChanged: _isSubmitting
                      ? null
                      : (value) {
                          setState(() {
                            _partnerRating = value;
                          });
                        },
                ),
              ),
              const SizedBox(height: 16),
              _SectionCard(
                title: 'Rate the property',
                child: _StarRating(
                  value: _propertyRating,
                  onChanged: _isSubmitting
                      ? null
                      : (value) {
                          setState(() {
                            _propertyRating = value;
                          });
                        },
                ),
              ),
              const SizedBox(height: 16),
              _SectionCard(
                title: 'Comments',
                child: TextField(
                  controller: _commentsController,
                  enabled: !_isSubmitting,
                  minLines: 4,
                  maxLines: 7,
                  maxLength: 1000,
                  decoration: const InputDecoration(
                    hintText: 'Tell us what went well or what should improve.',
                    border: OutlineInputBorder(),
                  ),
                ),
              ),
              if (_errorMessage != null) ...[
                const SizedBox(height: 16),
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: const Color(0xFFFFE4E6),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: const Color(0xFFFDA4AF)),
                  ),
                  child: Text(
                    _errorMessage!,
                    style: const TextStyle(
                      color: Color(0xFF9F1239),
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
              ],
              const SizedBox(height: 22),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton.icon(
                  onPressed: _isSubmitting ? null : _submitFeedback,
                  icon: _isSubmitting
                      ? const SizedBox(
                          width: 18,
                          height: 18,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Icon(Icons.send_rounded),
                  label: Text(
                    _isSubmitting ? 'Submitting...' : 'Submit Feedback',
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

class _HeaderCard extends StatelessWidget {
  const _HeaderCard({required this.viewing});

  final Viewing viewing;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: const Color(0xFFE8F5EC),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: const Color(0xFF86EFAC)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Icon(
            Icons.rate_review_outlined,
            color: Color(0xFF15803D),
            size: 34,
          ),
          const SizedBox(height: 12),
          Text(
            viewing.propertyTitle,
            style: const TextStyle(
              fontSize: 21,
              fontWeight: FontWeight.bold,
              color: Color(0xFF14532D),
            ),
          ),
          const SizedBox(height: 6),
          const Text(
            'Your feedback helps Pata Hao improve property '
            'accuracy and partner service.',
            style: TextStyle(color: Color(0xFF166534), height: 1.4),
          ),
        ],
      ),
    );
  }
}

class _SectionCard extends StatelessWidget {
  const _SectionCard({required this.title, required this.child});

  final String title;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(17),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: const Color(0xFFE5E7EB)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: const TextStyle(
              fontSize: 17,
              fontWeight: FontWeight.bold,
              color: Color(0xFF111827),
            ),
          ),
          const SizedBox(height: 14),
          child,
        ],
      ),
    );
  }
}

class _AccuracyOption extends StatelessWidget {
  const _AccuracyOption({
    required this.value,
    required this.title,
    required this.subtitle,
  });

  final String value;
  final String title;
  final String subtitle;

  @override
  Widget build(BuildContext context) {
    return RadioListTile<String>(
      value: value,
      contentPadding: EdgeInsets.zero,
      title: Text(title, style: const TextStyle(fontWeight: FontWeight.w700)),
      subtitle: Text(subtitle),
    );
  }
}

class _StarRating extends StatelessWidget {
  const _StarRating({required this.value, required this.onChanged});

  final int value;
  final ValueChanged<int>? onChanged;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: List.generate(5, (index) {
        final rating = index + 1;
        final isSelected = rating <= value;

        return IconButton(
          tooltip: '$rating star${rating == 1 ? '' : 's'}',
          onPressed: onChanged == null
              ? null
              : () {
                  onChanged!(rating);
                },
          iconSize: 36,
          icon: Icon(
            isSelected ? Icons.star_rounded : Icons.star_border_rounded,
            color: isSelected
                ? const Color(0xFFF59E0B)
                : const Color(0xFF9CA3AF),
          ),
        );
      }),
    );
  }
}
