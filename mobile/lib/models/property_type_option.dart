class PropertyTypeOption {
  const PropertyTypeOption({
    required this.value,
    required this.label,
  });

  final String value;
  final String label;

  factory PropertyTypeOption.fromJson(Map<String, dynamic> json) {
    final value = json['value']?.toString().trim() ?? '';
    final label = json['label']?.toString().trim() ?? '';

    if (value.isEmpty || label.isEmpty) {
      throw const FormatException(
        'Property type must contain value and label.',
      );
    }

    return PropertyTypeOption(
      value: value,
      label: label,
    );
  }
}