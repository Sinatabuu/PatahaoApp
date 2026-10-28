# Pata Hao iOS release preparation

Existing App Store Connect record: Apple ID **1419532156**, Bundle ID **com.Patahao** (case preserved), previous version **1.8**. Update this existing record; do not create a second app or change its registered identifier. The Flutter Xcode app target now uses com.Patahao in Debug/Profile/Release; the test target uses com.Patahao.RunnerTests. Display name is Pata Hao. App Store ID is a store record identifier, not the bundle identifier or signing Team ID.

Branch feature/ios-release-preparation is based on feature/mobile-property-sharing, including the tested clipboard fix. The Android sharing work remains on its own branch. This preparation changes iOS configuration only, plus this document. It does not upload or publish a build, change server environments, add Apple credentials, upgrade Flutter or select a signing team.

## Mac preflight

In Terminal on the Mac, check:

```sh
sw_vers
uname -m
xcodebuild -version
xcode-select -p
flutter --version
flutter doctor -v
```

Use a Flutter version compatible with the tested Windows Flutter 3.44.5 / Dart 3.12.2 setup. First inspect these results; do not blindly upgrade the SDK or overwrite an existing checkout. Obtain the source branch in a separate checkout so the Windows release files and local signing material are untouched. Run flutter pub get to resolve share_plus and regenerate the local plugin/SPM integration; review and preserve pubspec.lock after dependency resolution. The Windows-generated lockfile is not yet committed on the remote sharing branch.

## Before the first signed build

Wait for Apple's Developer Program membership to become active. Sign in to Xcode with the recovered account, select the team that owns com.Patahao for Runner, and allow automatic signing. Never paste Apple passwords, private signing keys, API private keys or recovery codes in chat or commit them. Do not select a different team simply to make signing succeed. Confirm the app's latest App Store and TestFlight marketing/build versions before choosing new version numbers.

The project already uses Flutter's generated Swift Package Manager integration. Do not add a Podfile or edit generated packages by hand. The app uses foreground location only. geolocator's SPM instructions require BYPASS_PERMISSION_LOCATION_ALWAYS=1 in the build environment to exclude the unused Always permission path; use this environment variable for terminal iOS builds, and verify the resulting native configuration on the Mac. No background location permission or background mode is added by this preparation.

The Info.plist has user-facing camera, photo library, video microphone and when-in-use location descriptions matching existing Flutter features. Runner.entitlements is wired for every app build configuration with the secure storage plugin's documented empty keychain-access-groups array. This does not authorize sharing keychain data with another app. Verify token persistence with actual signing on the iPhone before release.

## Checks still required on the Mac/iPhone

- Resolve dependencies, flutter analyze, flutter test, and an iOS simulator build.
- Validate Xcode signing/provisioning for the exact existing app and membership team.
- Confirm final app icons and launch screen branding before App Store submission (template assets have not been replaced by this preparation).
- Test customer and partner sign-in, logout/restart token persistence, and registration/account recovery against the intended HTTPS API.
- Test camera/library selection (including HEIC on a physical device), photo/video upload, foreground location denial/grant, property browsing, favourites, share sheet and copy fallback on iPhone. Verify popover behavior if supporting iPad.
- Test upgrading an existing version 1.8 installation. Keeping the Bundle ID preserves the App Store update path but does not automatically migrate credentials or local data from the old implementation.
- M-Pesa remains sandbox and its complete app callback flow still needs verification; do not claim production payment readiness.
- Check account-deletion access, App Privacy declarations, privacy manifests/plugin disclosures, export compliance, review access, supported device layouts and current Apple submission requirements.
- Upload to TestFlight and verify the existing App Store record receives the build before requesting public review. TestFlight/App Store signing and upload have not been attempted here.

Local verification for this preparation: XML property lists parsed successfully; all three app identifiers, test identifiers and entitlement paths checked; git diff whitespace checks passed. No Xcode build was possible in the Linux workspace. The shared Flutter code previously passed analysis, all 96 tests on Windows, and native Android share testing; iOS behavior is still unverified.
