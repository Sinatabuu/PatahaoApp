# Pata HAO mobile release configuration

## API environment

The app defaults to the current HTTPS API origin. Override it for a staging or
production build without editing Dart source:

```powershell
flutter run --dart-define=PATAHAO_API_BASE_URL=https://staging-api.example.com
flutter build appbundle --release --dart-define=PATAHAO_API_BASE_URL=https://api.example.com
```

The value must be an origin only: scheme, hostname, and optional port. Do not
include `/api/`, credentials, query parameters, or a fragment. Release builds
reject non-HTTPS origins. Android permits cleartext traffic only in debug
builds so local development remains possible without weakening a release.

## Android signing

Release builds are no longer signed with Flutter's public debug key. Generate
and protect the Play upload key, copy `android/key.properties.example` to
`android/key.properties`, and replace every placeholder. Both
`key.properties` and keystore files are ignored by Git.

Use Google Play App Signing and keep two encrypted backups of the upload key in
locations controlled by Pata HAO. Never put the keystore or its passwords in
GitHub, chat, email, screenshots, or build logs.

The permanent Android application ID is still `com.example.mobile`. Change it
before the first Play Console release, after Pata HAO confirms the permanent
brand/domain identifier. Google Play treats that identifier as permanent.
