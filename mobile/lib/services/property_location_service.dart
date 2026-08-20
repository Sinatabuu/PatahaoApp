import 'package:geolocator/geolocator.dart';

class PropertyLocationResult {
  const PropertyLocationResult({
    required this.latitude,
    required this.longitude,
    required this.accuracyMeters,
  });

  final double latitude;
  final double longitude;
  final double accuracyMeters;
}

class PropertyLocationService {
  PropertyLocationService._();

  static final PropertyLocationService instance =
      PropertyLocationService._();

  Future<PropertyLocationResult> captureCurrentLocation() async {
    final serviceEnabled =
        await Geolocator.isLocationServiceEnabled();

    if (!serviceEnabled) {
      throw Exception(
        'Location services are turned off. '
        'Please enable GPS and try again.',
      );
    }

    var permission = await Geolocator.checkPermission();

    if (permission == LocationPermission.denied) {
      permission = await Geolocator.requestPermission();
    }

    if (permission == LocationPermission.denied) {
      throw Exception(
        'Location permission is required to post a property.',
      );
    }

    if (permission == LocationPermission.deniedForever) {
      throw Exception(
        'Location permission has been permanently denied. '
        'Enable it in your phone settings to post a property.',
      );
    }

    final position = await Geolocator.getCurrentPosition(
      locationSettings: const LocationSettings(
        accuracy: LocationAccuracy.high,
        timeLimit: Duration(seconds: 20),
      ),
    );

    return PropertyLocationResult(
      latitude: position.latitude,
      longitude: position.longitude,
      accuracyMeters: position.accuracy,
    );
  }
}